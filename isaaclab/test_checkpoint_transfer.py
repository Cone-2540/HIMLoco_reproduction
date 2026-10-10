import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import torch
from checkpoint_transfer import warm_start


class Model(torch.nn.Module):
    def __init__(self, critic_dim):
        super().__init__()
        self.actor = torch.nn.Linear(4, 2)
        self.critic = torch.nn.Sequential(torch.nn.Linear(critic_dim, 8), torch.nn.ELU(), torch.nn.Linear(8, 1))
        self.estimator = torch.nn.Linear(4, 3)
        self.estimator.optimizer = torch.optim.Adam(self.estimator.parameters())


def runner(model):
    return SimpleNamespace(device="cpu", alg=SimpleNamespace(actor_critic=model,
        optimizer=torch.optim.Adam(model.parameters())), current_learning_iteration=0,
        tot_timesteps=0, tot_time=0)


class TransferTests(unittest.TestCase):
    def test_expand_preserves_value_without_new_columns(self):
        old, new = Model(48), Model(235)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            torch.save({"model_state_dict": old.state_dict(), "iter": 460}, path)
            r = runner(new)
            report = warm_start(r, path, "expand")
        x = torch.randn(12, 235)
        torch.testing.assert_close(old.critic(x[:, :48]), new.critic(x))
        torch.testing.assert_close(old.actor.weight, new.actor.weight)
        self.assertFalse(r.alg.optimizer.state)
        self.assertEqual(report["source_iteration"], 460)
        self.assertEqual(r.current_learning_iteration, 0)

    def test_reset_keeps_new_critic_and_transfers_estimator(self):
        old, new = Model(48), Model(235)
        untouched = new.critic[0].weight.detach().clone()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            torch.save({"model_state_dict": old.state_dict(), "iter": 460}, path)
            warm_start(runner(new), path, "reset")
        torch.testing.assert_close(untouched, new.critic[0].weight)
        torch.testing.assert_close(old.estimator.weight, new.estimator.weight)

    def test_actor_mismatch_is_rejected(self):
        old, new = Model(48), Model(235)
        source = old.state_dict()
        source["actor.weight"] = torch.zeros(2, 5)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            torch.save({"model_state_dict": source}, path)
            with self.assertRaisesRegex(ValueError, "shape mismatch"):
                warm_start(runner(new), path)


if __name__ == "__main__":
    unittest.main()
