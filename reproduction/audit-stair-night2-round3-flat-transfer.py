#!/usr/bin/env python3
"""Audit an independently frozen round3 policy actor/HIM transfer on CPU only.

Run with the existing container Python and CUDA_VISIBLE_DEVICES empty. Imports
Torch and the vendored networks, never AppLauncher or the simulation entry point.
The optional explicit --flat-run checks its real export/config after evaluation.
Outputs are exclusive: use a new output file for the post-evaluation audit.
"""

import argparse
import contextlib
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import torch


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [[.3, 0., 0.], [.5, 0., 0.], [-.5, 0., 0.],
            [0., .3, 0.], [0., -.3, 0.], [0., 0., .5], [0., 0., -.5]]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def tensor_digest(value):
    return hashlib.sha256(value.detach().contiguous().numpy().tobytes()).hexdigest()


def local_path(value):
    text = str(value)
    if text.startswith("/workspace/himloco/"):
        return ROOT / text[len("/workspace/himloco/"):]
    if text.startswith("/home/cone/Research/HIMLoco/"):
        return ROOT / text[len("/home/cone/Research/HIMLoco/"):]
    path = Path(text).expanduser()
    return path.resolve() if path.is_absolute() else ROOT / path


def fixed_histories():
    generator = torch.Generator().manual_seed(1709)
    samples = [torch.zeros(1, 270)]
    for scale in (.01, .1, 1., 3.):
        samples.append(torch.randn(32, 270, generator=generator) * scale)
    command_histories = torch.zeros(7, 6, 45)
    command_histories[:, :, :3] = torch.tensor(COMMANDS)[:, None, :] * torch.tensor([2., 2., .25])
    samples.append(command_histories.reshape(7, 270))
    impulse = torch.zeros(4, 6, 45)
    for index, (frame, column) in enumerate(((0, 0), (5, 0), (0, 9), (5, 44))):
        impulse[index, frame, column] = .25
    samples.append(impulse.reshape(4, 270))
    return torch.cat(samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--selection-file", type=Path, required=True)
    parser.add_argument("--flat-run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or torch.cuda.is_initialized():
        raise ValueError("CPU audit requires CUDA_VISIBLE_DEVICES empty and CUDA uninitialized")
    if torch.cuda.is_available():
        raise ValueError("CPU audit requires no visible CUDA devices")
    torch.set_num_threads(2)
    checkpoint, selection_path, output = map(local_path, (args.checkpoint, args.selection_file, args.output))
    if output.exists():
        raise ValueError("Refusing to overwrite existing audit: " + str(output))
    selection = json.loads(selection_path.read_text())
    selected = selection["selected"]
    if checkpoint.resolve() != local_path(selected["checkpoint"]).resolve() or digest(checkpoint) != selected["checkpoint_sha256"]:
        raise ValueError("Checkpoint differs from selected final freeze")
    if selection.get("round") != 3 or selection["status"] != "frozen_before_final" or selection["selection_basis"] != "development_only" or selection.get("no_final_evidence_used") is not True:
        raise ValueError("Expected explicit development-only final freeze")
    config_path = local_path(selected["training_manifest"]).parent / "config.json"
    if digest(config_path) != selected["training_config_sha256"]:
        raise ValueError("Training configuration differs from freeze")
    config = json.loads(config_path.read_text())
    stair_export = checkpoint.parent / "policy.pt"
    manifest = json.loads((checkpoint.parent / "manifest.json").read_text())
    if digest(checkpoint.parent / "manifest.json") != selected["training_manifest_sha256"]:
        raise ValueError("Training archive manifest changed since round3 freeze")
    if len(manifest["files"]) != 19 or selected["archive_member_sha256"] != {name: member["sha256"] for name, member in manifest["files"].items()}:
        raise ValueError("Expected all nineteen frozen archive members")
    for name, member in manifest["files"].items():
        path = checkpoint.parent / name
        if not path.resolve().is_relative_to(checkpoint.parent.resolve()) or path.stat().st_size != member["bytes"] or digest(path) != member["sha256"]:
            raise ValueError("Training archive member changed: " + name)
    if digest(stair_export) != manifest["files"]["policy.pt"]["sha256"]:
        raise ValueError("Archived stair export differs from training manifest")
    sys.path.insert(0, str(ROOT / "isaaclab/vendor"))
    sys.path.insert(0, str(ROOT / "isaaclab"))
    from checkpoint_transfer import warm_start
    from him_rsl_rl.modules.him_actor_critic import HIMActorCritic
    options = {key: config["train"]["policy"][key] for key in
               ("actor_hidden_dims", "critic_hidden_dims", "activation", "init_noise_std")}
    source = torch.load(checkpoint, map_location="cpu", weights_only=True)
    state = source["model_state_dict"]
    if len(state) != 30 or any(value.device.type != "cpu" or not torch.isfinite(value).all().item() for value in state.values()):
        raise ValueError("Unexpected/nonfinite source model tensors")
    torch.manual_seed(1701)
    with contextlib.redirect_stdout(io.StringIO()):
        stair_model = HIMActorCritic(270, 235, 45, 12, **options).cpu().eval()
        flat_model = HIMActorCritic(270, 48, 45, 12, **options).cpu().eval()
    stair_model.load_state_dict(state, strict=True)
    fresh_critic = {name: value.clone() for name, value in flat_model.state_dict().items() if name.startswith("critic.")}
    optimizer = torch.optim.Adam(flat_model.parameters(), lr=1e-4)
    runner = SimpleNamespace(device="cpu", alg=SimpleNamespace(actor_critic=flat_model, optimizer=optimizer),
                             current_learning_iteration=0, tot_timesteps=0, tot_time=0)
    transfer = warm_start(runner, str(checkpoint), "reset")
    rows = []
    for name, value in flat_model.state_dict().items():
        if not torch.isfinite(value).all().item():
            raise ValueError("Nonfinite target tensor: " + name)
        expected = fresh_critic[name] if name.startswith("critic.") else state[name]
        if not torch.equal(value, expected):
            raise ValueError("Transferred/fresh tensor differs: " + name)
        rows.append({"name": name, "shape": list(value.shape), "dtype": str(value.dtype),
                     "source": "fresh critic initialization" if name.startswith("critic.") else "exact checkpoint tensor",
                     "bitwise_equal": True, "sha256": tensor_digest(value)})
    if len(transfer["copied"]) != 22 or len(transfer["new_initialization"]) != 8:
        raise ValueError("Unexpected actor/HIM or critic transfer counts")
    if optimizer.state or flat_model.estimator.optimizer.state:
        raise ValueError("Expected empty fresh optimizers")
    sample = fixed_histories()
    before = {name: value.clone() for name, value in flat_model.state_dict().items()}
    rng_before = torch.random.get_rng_state().clone()
    with torch.inference_mode():
        reference = stair_model.act_inference(sample)
        transferred = flat_model.act_inference(sample)
        repeated = flat_model.act_inference(sample)
        archived = torch.jit.load(str(stair_export), map_location="cpu").eval()(sample)
    differences = {"transferred_vs_full_stair_model": float((transferred-reference).abs().max()),
                   "transferred_vs_archived_stair_export": float((transferred-archived).abs().max()),
                   "deterministic_repeat": float((transferred-repeated).abs().max())}
    if not torch.equal(rng_before, torch.random.get_rng_state()):
        raise ValueError("Deterministic inference consumed Torch RNG")
    # Counterfactual CPU-only critic/std change establishes that inference does
    # not depend on their values, rather than only observing equal outputs once.
    with torch.no_grad():
        flat_model.std.fill_(7.)
        for value in flat_model.critic.parameters():
            value.fill_(3.)
    with torch.inference_mode():
        unused_values_changed = flat_model.act_inference(sample)
    differences["critic_and_std_counterfactual"] = float((transferred-unused_values_changed).abs().max())
    flat_model.load_state_dict(before, strict=True)
    if any(not torch.equal(value, flat_model.state_dict()[name]) for name, value in before.items()):
        raise ValueError("Inference/counterfactual changed model tensors")
    actual = None
    if args.flat_run:
        run = local_path(args.flat_run)
        flat_config_path, flat_export_path = run / "config.json", run / "policy.pt"
        flat_config = json.loads(flat_config_path.read_text())
        if flat_config["mode"] != "evaluate" or flat_config["terrain"] != "flat" or flat_config["seed"] != 1301 or flat_config["num_envs"] != 64 or flat_config["command_override"] != COMMANDS or flat_config["evaluation_seconds"] != 20:
            raise ValueError("Explicit flat run is not a flat evaluation")
        if local_path(flat_config["checkpoint"]).resolve() != checkpoint.resolve():
            raise ValueError("Actual flat run used a different checkpoint")
        if flat_config["transfer"] != transfer or flat_config["requested_additional_training_updates"] is not None:
            raise ValueError("Actual flat transfer record differs or requested training")
        diagnostic = json.loads((run / "physics-diagnostic.json").read_text())
        if diagnostic["critic_shape"] != [flat_config["num_envs"], 48]:
            raise ValueError("Actual flat critic is not 48-dimensional")
        with torch.inference_mode():
            actual_output = torch.jit.load(str(flat_export_path), map_location="cpu").eval()(sample)
        differences["transferred_vs_actual_flat_export"] = float((transferred-actual_output).abs().max())
        actual = {"run": str(run), "config_sha256": digest(flat_config_path),
                  "export_sha256": digest(flat_export_path), "critic_shape": diagnostic["critic_shape"],
                  "transfer_record_matches": True, "training_updates_requested": None}
    if any(not torch.isfinite(torch.tensor(value)) or value != 0.0 for value in differences.values()):
        raise ValueError("Deterministic actor/export mismatch: " + repr(differences))
    if torch.cuda.is_initialized() or optimizer.state or flat_model.estimator.optimizer.state:
        raise ValueError("Audit unexpectedly initialized CUDA or optimizer state")
    document = {"schema_version": 1, "recorded_local": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                "status": "round3_CPU_transfer_verified", "round": 3, "checkpoint": str(checkpoint),
                "checkpoint_sha256": digest(checkpoint), "selected_actual_training_reward_profile": selected["training_reward_profile"], "selected_actual_training_reward_weights": selected["training_reward_weights"], "selection_file": str(selection_path),
                "selection_file_sha256": digest(selection_path), "source_iteration": source["iter"], "selection_source_proof_sha256": selection["source_proof_sha256"], "audit_tool_sha256": digest(Path(__file__)), "archive_members_verified": 19,
                "torch": torch.__version__, "cuda_initialized": False, "simulator_started": False,
                "gradient_updates": 0, "critic_dimensions": {"source": 235, "target": 48},
                "transfer_record": transfer, "tensor_audits": rows,
                "actor_HIM_std_exact_copies": 22, "fresh_critic_tensors_preserved": 8,
                "all_source_and_target_tensors_finite": True, "fresh_optimizer_state_empty": True,
                "deterministic_inference_rng_unchanged": True, "model_tensors_restored_and_unchanged": True,
                "input_shape": list(sample.shape), "input_sha256": tensor_digest(sample),
                "fixed_inputs": {"noise_seed": 1709, "random_scales": [.01, .1, 1., 3.],
                                 "command_histories": COMMANDS, "command_scales": [2., 2., .25],
                                 "command_slice_in_each_frame": [0, 3],
                                 "other_inputs": "zero history and four fixed newest/oldest-frame impulses"},
                "maximum_absolute_action_differences": differences,
                "archived_stair_export_sha256": digest(stair_export), "actual_flat_run": actual,
                "source_sha256": {name: digest(ROOT/name) for name in
                                  ("isaaclab/checkpoint_transfer.py", "isaaclab/adapter.py",
                                   "isaaclab/vendor/him_rsl_rl/modules/him_actor_critic.py",
                                   "isaaclab/vendor/him_rsl_rl/modules/him_estimator.py")},
                "limits": "Fixed synthetic CPU inputs verify tensor transfer and deterministic actor/export synchronization. They do not verify actual sensor histories, locomotion quality, flat command gates, real-robot interfaces, or the cause of any flat failures. No final-model reselection or retuning."}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": document["status"], "output": str(output),
                      "actor_HIM_std_tensors": 22, "fresh_critic_tensors": 8,
                      "inputs": list(sample.shape), "action_max_differences": differences,
                      "actual_flat_run_checked": actual is not None, "cuda_initialized": False}))


if __name__ == "__main__":
    main()
