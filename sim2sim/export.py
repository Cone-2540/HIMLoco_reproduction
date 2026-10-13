#!/usr/bin/env python3
"""Export and numerically verify an original HIM checkpoint without launching Isaac."""
import argparse
import copy
import json
from pathlib import Path
import sys
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'isaaclab/vendor'))
from him_rsl_rl.modules import HIMActorCritic


class ExportPolicy(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.encoder=copy.deepcopy(model.estimator.encoder)
        self.actor=copy.deepcopy(model.actor)

    def forward(self, history: torch.Tensor)->torch.Tensor:
        estimate=self.encoder(history)
        return self.actor(torch.cat((history[:,:45],estimate[:,:3],
            torch.nn.functional.normalize(estimate[:,3:],dim=-1)),dim=-1))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('checkpoint',type=Path)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    torch.set_num_threads(1)
    checkpoint=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    state=checkpoint['model_state_dict']
    config=json.loads(a.config.read_text())
    model=HIMActorCritic(270,state['critic.0.weight'].shape[1],45,12,**config['train']['policy']).eval()
    model.load_state_dict(state,strict=True)
    torch.manual_seed(1400)
    sample=torch.randn(128,270)
    with torch.inference_mode():
        expected=model.act_inference(sample)
        export=torch.jit.script(ExportPolicy(model).eval())
        a.output.parent.mkdir(parents=True,exist_ok=True)
        export.save(str(a.output))
        actual=torch.jit.load(str(a.output))(sample)
        torch.testing.assert_close(actual,expected,atol=1e-5,rtol=1e-5)
        difference=float((actual-expected).abs().max())
    report={'checkpoint':str(a.checkpoint.resolve()),'output':str(a.output.resolve()),
            'input_shape':[128,270],'output_shape':[128,12],'max_abs_error':difference,
            'weights_finite':all(torch.isfinite(x).all().item() for x in state.values()),
            'torch_version':torch.__version__}
    a.output.with_suffix('.export.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
