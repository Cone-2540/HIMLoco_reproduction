#!/usr/bin/env python3
"""CPU presentation adapter: keep frozen plotting source unchanged.

Moves the first-row contact legend away from the highest faithful descent bar.
All counts/identity/row checks use the existing plotting module unchanged.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    source = here / "plot-stair-night2-reward-comparison.py"
    spec = importlib.util.spec_from_file_location("night2_reward_plot", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round3-directory", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, default=here / "stair-night2-reward-comparison-three-rounds")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    args.round1_directory = here / "stair-night2-round1-development"
    args.round2_directory = here / "stair-night2-round2-development"
    data = module.collect(args)
    data["presentation_adapter"] = {
        "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "override": "Contact legend upper right instead of upper left; no data/gate/identity changes",
    }
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.axes
    original_legend = matplotlib.axes.Axes.legend
    def visible_legend(self, *items, **options):
        if options.get("loc") == "upper left":
            options["loc"] = "upper right"
        return original_legend(self, *items, **options)
    matplotlib.axes.Axes.legend = visible_legend
    try:
        outputs = module.render(data, args.output_prefix, args.overwrite)
    finally:
        matplotlib.axes.Axes.legend = original_legend
    print(json.dumps({"outputs": [str(path) for path in outputs], "tracked_plot_source_changed": False}))


if __name__ == "__main__":
    main()
