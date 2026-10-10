"""Explicit flat-to-terrain transfer; optimizer moments never cross shapes."""

import torch


def warm_start(runner, path, critic_mode="reset"):
    """Keep actor/HIM weights, reset training state, optionally expand critic.

    ``expand`` preserves the original first-layer proprioceptive columns and
    initializes new privileged terrain columns to zero. ``reset`` uses a new
    critic because the terrain return distribution differs from flat ground.
    """
    if critic_mode not in ("reset", "expand"):
        raise ValueError("critic_mode must be reset or expand")
    checkpoint = torch.load(path, map_location=runner.device, weights_only=True)
    source = checkpoint["model_state_dict"]
    model = runner.alg.actor_critic
    target = model.state_dict()
    copied, skipped = [], []
    for name, value in target.items():
        if name not in source:
            raise ValueError(f"Missing checkpoint weight: {name}")
        old = source[name]
        if name.startswith("critic."):
            if critic_mode == "reset":
                skipped.append(name)
                continue
            if old.shape != value.shape:
                if name != "critic.0.weight" or old.ndim != 2 or old.shape[0] != value.shape[0] or old.shape[1] > value.shape[1]:
                    raise ValueError(f"Unsupported critic transfer: {name}: {old.shape} -> {value.shape}")
                value.zero_()
                value[:, :old.shape[1]] = old
                copied.append(name + ":zero_extended")
                continue
        if old.shape != value.shape:
            raise ValueError(f"HIM/actor shape mismatch: {name}: {old.shape} -> {value.shape}")
        value.copy_(old)
        copied.append(name)
    unexpected = set(source) - set(target)
    if unexpected:
        raise ValueError(f"Unexpected checkpoint weights: {sorted(unexpected)}")
    model.load_state_dict(target, strict=True)
    # The caller has just constructed this runner; refuse accidental transfer
    # after learning, since retained Adam moments would silently corrupt it.
    if runner.alg.optimizer.state or model.estimator.optimizer.state:
        raise ValueError("Warm start requires fresh optimizers")
    runner.current_learning_iteration = 0
    runner.tot_timesteps = 0
    runner.tot_time = 0
    return {"source_iteration": checkpoint.get("iter"), "critic_mode": critic_mode,
            "copied": copied, "new_initialization": skipped,
            "optimizer": "fresh", "training_iteration": 0}
