#!/usr/bin/env python3
"""CPU-only check that flat critic reset preserves frozen actor/HIM inference.

Run with the existing container's Python, CUDA masked. No simulator is imported.
Compare checkpoint tensors and both actual evaluation exports on the same
history inputs; this audits transfer, not the locomotion or sensor convention.
"""
import contextlib
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import torch


def main():
    repo = Path(__file__).resolve().parent.parent
    sys.path.insert(0,str(repo/"isaaclab/vendor"))
    sys.path.insert(0,str(repo/"isaaclab"))
    from him_rsl_rl.modules.him_actor_critic import HIMActorCritic
    from checkpoint_transfer import warm_start
    if torch.cuda.is_available():
        raise ValueError("Audit requires CUDA unavailable; mask CUDA_VISIBLE_DEVICES")
    torch.set_num_threads(2)
    torch.manual_seed(1701)
    checkpoint = repo/"artifacts/go2-stairs-control660/model_660.pt"
    stair_export = repo/"artifacts/go2-stairs-control660/policy.pt"
    flat_run = repo/"isaaclab/logs/2026-10-11_06-09-35_frozen-stair-policy-flat-regression"
    config = json.loads((flat_run/"config.json").read_text())
    train_policy = config["train"]["policy"]
    options = {key:train_policy[key] for key in
               ("actor_hidden_dims","critic_hidden_dims","activation","init_noise_std")}
    with contextlib.redirect_stdout(io.StringIO()):
        model = HIMActorCritic(270,48,45,12,**options).cpu().eval()
    critic_before = {name:value.clone() for name,value in model.state_dict().items() if name.startswith("critic.")}
    optimizer = torch.optim.Adam(model.parameters(),lr=1e-4)
    runner = SimpleNamespace(device="cpu",alg=SimpleNamespace(actor_critic=model,optimizer=optimizer),
                             current_learning_iteration=0,tot_timesteps=0,tot_time=0)
    transfer = warm_start(runner,str(checkpoint),"reset")
    source = torch.load(checkpoint,map_location="cpu",weights_only=True)["model_state_dict"]
    same = [name for name,value in model.state_dict().items() if not name.startswith("critic.") and torch.equal(value,source[name])]
    expected = [name for name in source if not name.startswith("critic.")]
    if set(same) != set(expected) or len(same) != 22:
        raise ValueError("Actor/HIM/std changed during critic reset")
    if not all(torch.equal(value,model.state_dict()[name]) for name,value in critic_before.items()):
        raise ValueError("Reset critic did not retain its fresh initialization")
    if transfer != config["transfer"]:
        raise ValueError("Reproduced transfer record differs from flat evaluation")
    histories = [torch.zeros(1,270)]
    generator = torch.Generator().manual_seed(1709)
    for scale in (0.01,0.1,1.0,3.0):
        histories.append(torch.randn(32,270,generator=generator)*scale)
    commands = torch.zeros(6,6,45)
    for row,command in enumerate(((.3,0,0),(.5,0,0),(-.5,0,0),(0,.3,0),(0,0,.5),(0,0,-.5))):
        commands[row,:,6:9] = torch.tensor(command)*torch.tensor((2.0,2.0,.25))
    histories.append(commands.reshape(6,270))
    sample = torch.cat(histories)
    with torch.inference_mode():
        reconstructed = model.act_inference(sample)
        flat = torch.jit.load(str(flat_run/"policy.pt"),map_location="cpu").eval()(sample)
        stairs = torch.jit.load(str(stair_export),map_location="cpu").eval()(sample)
    differences = {"warm_start_vs_actual_flat_export":float((reconstructed-flat).abs().max()),
                   "warm_start_vs_stair_export":float((reconstructed-stairs).abs().max()),
                   "actual_flat_export_vs_stair_export":float((flat-stairs).abs().max())}
    if any(value > 1e-6 for value in differences.values()):
        raise ValueError(f"Inference mismatch: {differences}")
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    document = {"recorded_local":datetime.now().astimezone().isoformat(),"torch":torch.__version__,
                "cuda_available":False,"simulator_started":False,"gradient_updates":0,
                "checkpoint_sha256":sha(checkpoint),"flat_config_sha256":sha(flat_run/"config.json"),
                "flat_export_sha256":sha(flat_run/"policy.pt"),"stair_export_sha256":sha(stair_export),
                "critic_transfer_helper_sha256":sha(repo/"isaaclab/checkpoint_transfer.py"),
                "input_shape":list(sample.shape),"seed":1709,"matching_actor_him_std_tensors":same,
                "critic_dim_reset_to":48,"critic_fresh_initialization_retained":True,
                "transfer_record_exactly_matches_actual_flat_evaluation":True,
                "maximum_absolute_action_differences":differences,
                "limits":"Synthetic CPU inputs verify transfer/export synchronization, not actual sensor observations, locomotion quality, real-robot interface or unique cause of flat command failures."}
    (repo/"reproduction/frozen-flat-transfer-independent-audit.json").write_text(json.dumps(document,indent=2)+"\n")
    print(json.dumps({"actor_him_std_tensors":len(same),"inputs":list(sample.shape),"action_max_differences":differences}))


if __name__ == "__main__":
    main()
