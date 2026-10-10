"""Adapt Isaac Lab 3 observations and terminal states to the original HIM runner."""

import torch


class HIMVecEnv:
    def __init__(self, env):
        self.env = env.unwrapped
        self.num_envs = self.env.num_envs
        self.device = self.env.device
        self.num_one_step_obs = 45
        self.num_obs = 45 * 6
        self.num_privileged_obs = self.env.observation_manager.group_obs_dim["critic"][0]
        self.num_actions = self.env.action_manager.total_action_dim
        self.max_episode_length = self.env.max_episode_length
        self.obs_buf = torch.zeros(self.num_envs, self.num_obs, device=self.device)
        self.privileged_obs_buf = None

    @property
    def episode_length_buf(self):
        return self.env.episode_length_buf

    @episode_length_buf.setter
    def episode_length_buf(self, value):
        self.env.episode_length_buf[:] = value

    def reset(self):
        obs, _ = self.env.reset()
        self.obs_buf.zero_()
        self.obs_buf[:, :45] = obs["policy"]
        self.privileged_obs_buf = obs["critic"]
        return self.obs_buf, self.privileged_obs_buf

    def get_observations(self):
        return self.obs_buf

    def get_privileged_observations(self):
        return self.privileged_obs_buf

    def step(self, actions):
        obs, rewards, terminated, truncated, extras = self.env.step(actions.clamp(-100, 100))
        dones = terminated | truncated
        ids = dones.nonzero(as_tuple=False).flatten()
        terminal = extras["final_obs"]["critic"][ids].clone() if ids.numel() else obs["critic"][:0]
        # Newest frame first. Clear all history on reset to prevent episode leakage.
        history = torch.cat((obs["policy"], self.obs_buf[:, :-45]), dim=-1)
        history[ids] = 0
        history[ids, :45] = obs["policy"][ids]
        self.obs_buf = history
        self.privileged_obs_buf = obs["critic"]
        infos = {"time_outs": truncated, "terminated": terminated}
        if ids.numel() and extras.get("log"):
            infos["episode"] = extras["log"]
        return history, self.privileged_obs_buf, rewards, dones, infos, ids, terminal
