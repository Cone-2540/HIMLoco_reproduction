"""Check history and pre-reset targets across an episode boundary."""

import unittest
from types import SimpleNamespace

import torch

from adapter import HIMVecEnv


class FakeEnv:
    def __init__(self):
        self.unwrapped = self
        self.num_envs = 2
        self.device = "cpu"
        self.max_episode_length = 1000
        self.episode_length_buf = torch.zeros(2, dtype=torch.long)
        self.observation_manager = SimpleNamespace(group_obs_dim={"critic": (48,)})
        self.action_manager = SimpleNamespace(total_action_dim=12)

    def reset(self):
        return {"policy": torch.ones(2, 45), "critic": torch.ones(2, 48)}, {}

    def step(self, actions):
        obs = {"policy": torch.full((2, 45), 2.0), "critic": torch.full((2, 48), 3.0)}
        final = {"critic": torch.full((2, 48), 9.0)}
        return obs, torch.ones(2), torch.tensor([True, False]), torch.zeros(2, dtype=torch.bool), {"final_obs": final}


class AdapterTest(unittest.TestCase):
    def test_reset_boundary_preserves_terminal_target_and_clears_history(self):
        adapter = HIMVecEnv(FakeEnv())
        adapter.reset()
        obs, critic, _, dones, _, ids, terminal = adapter.step(torch.zeros(2, 12))
        torch.testing.assert_close(terminal, torch.full((1, 48), 9.0))
        self.assertEqual(ids.tolist(), [0])
        self.assertEqual(dones.tolist(), [True, False])
        torch.testing.assert_close(critic, torch.full((2, 48), 3.0))
        torch.testing.assert_close(obs[0, :45], torch.full((45,), 2.0))
        torch.testing.assert_close(obs[0, 45:], torch.zeros(225))
        torch.testing.assert_close(obs[1, :45], torch.full((45,), 2.0))
        torch.testing.assert_close(obs[1, 45:90], torch.ones(45))
        torch.testing.assert_close(obs[1, 90:], torch.zeros(180))


if __name__ == "__main__":
    unittest.main()
