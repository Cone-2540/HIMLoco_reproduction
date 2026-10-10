"""CPU regression tests for compatibility fixes, without importing Isaac Sim."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from collections import deque

import torch

from him_rsl_rl.algorithms.him_ppo import HIMPPO
from him_rsl_rl.modules.him_actor_critic import HIMActorCritic
from him_rsl_rl.runners.him_on_policy_runner import HIMOnPolicyRunner


def make_model():
    with contextlib.redirect_stdout(io.StringIO()):
        return HIMActorCritic(270, 48, 45, 12, actor_hidden_dims=[16], critic_hidden_dims=[16])


class FakeEnv:
    num_envs = 4
    num_obs = 270
    num_one_step_obs = 45
    num_privileged_obs = 48
    num_actions = 12
    max_episode_length = 1000

    def __init__(self):
        self.episode_length_buf = torch.zeros(self.num_envs, dtype=torch.long)
        self.obs = torch.zeros(self.num_envs, self.num_obs)
        self.critic = torch.zeros(self.num_envs, self.num_privileged_obs)

    def reset(self):
        return self.obs, self.critic

    def get_observations(self):
        return self.obs

    def get_privileged_observations(self):
        return self.critic

    def step(self, actions):
        return (self.obs, self.critic, torch.ones(self.num_envs), torch.zeros(self.num_envs, dtype=torch.bool),
                {}, torch.empty(0, dtype=torch.long), self.critic[:0])


def make_runner(path, env=None, steps=1):
    cfg = {
        'runner': {'policy_class_name': 'HIMActorCritic', 'algorithm_class_name': 'HIMPPO',
                   'num_steps_per_env': steps, 'save_interval': 1},
        'policy': {'actor_hidden_dims': [16], 'critic_hidden_dims': [16]},
        'algorithm': {'num_learning_epochs': 1, 'num_mini_batches': 2},
    }
    with contextlib.redirect_stdout(io.StringIO()):
        return HIMOnPolicyRunner(env if env is not None else FakeEnv(), cfg, str(path), device='cpu')


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        torch.set_num_threads(1)

    def test_non_positive_std_still_produces_finite_gaussian(self):
        model = make_model()
        with torch.no_grad():
            model.std.fill_(-0.5)
        actions = model.act(torch.zeros(4, 270))
        self.assertTrue(torch.isfinite(actions).all())
        self.assertTrue(torch.isfinite(model.get_actions_log_prob(actions)).all())
        torch.testing.assert_close(model.action_std, torch.full((4, 12), 1e-3))

    def test_timeout_uses_next_state_and_termination_overrides_timeout(self):
        model = make_model()
        alg = HIMPPO(model, gamma=0.99)
        alg.init_storage(3, 1, [270], [48], [12])
        current = torch.zeros(3, 48)
        current[:, 0] = 2
        next_critic = torch.zeros(3, 48)
        next_critic[:, 0] = torch.tensor([7.0, 8.0, 9.0])
        with mock.patch.object(model, 'evaluate', side_effect=lambda x: x[:, :1]):
            alg.act(torch.zeros(3, 270), current)
            alg.process_env_step(torch.ones(3), torch.ones(3, dtype=torch.bool),
                                 {'time_outs': torch.tensor([True, True, False]),
                                  'terminated': torch.tensor([False, True, True])}, next_critic)
        torch.testing.assert_close(alg.storage.rewards[0, :, 0], torch.tensor([7.93, 1.0, 1.0]))
        torch.testing.assert_close(alg.storage.next_privileged_observations[0], next_critic)

    def test_sparse_timeout_bootstrap_matches_full_batch_values_and_returns(self):
        model = make_model()
        alg = HIMPPO(model, gamma=.99, lam=.95)
        n = 7
        alg.init_storage(n, 1, [270], [48], [12])
        current, next_critic = torch.randn(n, 48), torch.randn(n, 48)
        rewards = torch.randn(n)
        original_rewards = rewards.clone()
        timeouts = torch.tensor([True, False, True, True, False, False, True])
        terminated = torch.tensor([False, False, True, False, False, False, True])
        true_timeouts = timeouts & ~terminated
        with torch.no_grad():
            expected_rewards = rewards + .99 * model.evaluate(next_critic).squeeze(-1) * true_timeouts
        alg.act(torch.randn(n, 270), current)
        with mock.patch.object(model, 'evaluate', wraps=model.evaluate) as evaluate:
            alg.process_env_step(rewards, timeouts | terminated,
                                 {'time_outs': timeouts, 'terminated': terminated}, next_critic)
        self.assertEqual(evaluate.call_count, 1)
        torch.testing.assert_close(evaluate.call_args.args[0], next_critic[true_timeouts])
        torch.testing.assert_close(alg.storage.rewards[0, :, 0], expected_rewards, atol=1e-6, rtol=1e-6)
        with torch.no_grad():
            last_values = model.evaluate(next_critic).squeeze(-1)
            expected_returns = expected_rewards + .99 * last_values * ~(timeouts | terminated)
        alg.compute_returns(next_critic)
        torch.testing.assert_close(alg.storage.returns[0, :, 0], expected_returns, atol=1e-6, rtol=1e-6)
        torch.testing.assert_close(rewards, original_rewards)

    def test_no_true_timeouts_skips_critic_forward_and_preserves_rewards(self):
        for info in ({'time_outs': torch.zeros(4, dtype=torch.bool)},
                     {'time_outs': torch.ones(4, dtype=torch.bool),
                      'terminated': torch.ones(4, dtype=torch.bool)}):
            model = make_model()
            alg = HIMPPO(model)
            alg.init_storage(4, 1, [270], [48], [12])
            rewards = torch.tensor([-1., .25, .5, 3.])
            alg.act(torch.zeros(4, 270), torch.zeros(4, 48))
            with mock.patch.object(model, 'evaluate', side_effect=AssertionError('unexpected critic forward')):
                alg.process_env_step(rewards, info['time_outs'], info, torch.ones(4, 48))
            torch.testing.assert_close(alg.storage.rewards[0, :, 0], rewards)

    def test_episode_logs_keep_tick_id_order_and_last_100_across_iterations(self):
        class ScriptedEpisodes(FakeEnv):
            def __init__(self):
                self.num_envs = 64
                super().__init__()
                self.tick = 0

            @staticmethod
            def ended(tick):
                ids = torch.arange(64)
                if tick in (1, 6):
                    return ids % 2 == 0
                if tick == 2:
                    return ids % 2 == 1
                if tick in (3, 8):
                    return torch.ones(64, dtype=torch.bool)
                if tick == 5:
                    return ids % 3 == 0
                return torch.zeros(64, dtype=torch.bool)

            @staticmethod
            def reward(tick):
                return torch.arange(64, dtype=torch.float) / 10. + 100. * tick + 1.

            def step(self, actions):
                self.tick += 1
                dones = self.ended(self.tick)
                ids = dones.nonzero(as_tuple=False).flatten()
                return self.obs, self.critic, self.reward(self.tick), dones, {}, ids, self.critic[ids]

        expected = []
        reference_rewards, reference_lengths = torch.zeros(64), torch.zeros(64)
        reward_deque, length_deque = deque(maxlen=100), deque(maxlen=100)
        for tick in range(1, 9):
            reference_rewards += ScriptedEpisodes.reward(tick)
            reference_lengths += 1
            ids = ScriptedEpisodes.ended(tick).nonzero(as_tuple=False).flatten()
            reward_deque.extend(reference_rewards[ids].tolist())
            length_deque.extend(reference_lengths[ids].tolist())
            reference_rewards[ids], reference_lengths[ids] = 0, 0
            if tick % 4 == 0:
                expected.append((list(reward_deque), list(length_deque)))
        with tempfile.TemporaryDirectory() as directory:
            runner = make_runner(Path(directory), env=ScriptedEpisodes(), steps=4)
            original_log, captured = runner.log, []
            def record(locs):
                captured.append((list(locs['rewbuffer']), list(locs['lenbuffer'])))
                original_log(locs)
            with mock.patch.object(runner, 'log', side_effect=record), contextlib.redirect_stdout(io.StringIO()):
                runner.learn(2)
            self.assertEqual(captured, expected)
            self.assertEqual(len(captured[0][0]), 100)
            self.assertEqual(runner.tot_timesteps, 2 * 4 * 64)

    def test_estimator_target_excludes_commands_and_includes_next_velocity(self):
        estimator = make_model().estimator
        next_critic = torch.arange(48, dtype=torch.float).unsqueeze(0).repeat(4, 1)
        captured = []
        handle = estimator.target.register_forward_pre_hook(lambda _, inputs: captured.append(inputs[0].clone()))
        with mock.patch('torch.nn.functional.mse_loss', wraps=torch.nn.functional.mse_loss) as mse:
            losses = estimator.update(torch.zeros(4, 270), next_critic)
        handle.remove()
        torch.testing.assert_close(captured[0], next_critic[:, 3:48])
        torch.testing.assert_close(mse.call_args.args[1], next_critic[:, 45:48])
        self.assertTrue(all(torch.isfinite(torch.tensor(x)) for x in losses))

    def test_update_reports_mean_losses_and_projects_std(self):
        model = make_model()
        alg = HIMPPO(model, num_mini_batches=2, num_learning_epochs=1)
        alg.init_storage(4, 1, [270], [48], [12])
        alg.act(torch.zeros(4, 270), torch.zeros(4, 48))
        alg.process_env_step(torch.ones(4), torch.zeros(4, dtype=torch.bool), {}, torch.zeros(4, 48))
        alg.compute_returns(torch.zeros(4, 48))
        actual_step = alg.optimizer.step

        def step_with_negative_std():
            actual_step()
            with torch.no_grad():
                model.std.fill_(-0.5)

        with mock.patch.object(model.estimator, 'update', side_effect=[(2.0, 4.0), (4.0, 8.0)]), \
             mock.patch.object(alg.optimizer, 'step', side_effect=step_with_negative_std):
            _, _, estimation, swap = alg.update()
        self.assertEqual((estimation, swap), (3.0, 6.0))
        torch.testing.assert_close(model.std, torch.full((12,), 1e-3))

    def test_periodic_checkpoints_resume_completed_iteration_and_optimizer_lr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            runner = make_runner(path)
            with contextlib.redirect_stdout(io.StringIO()):
                runner.learn(3)
            self.assertEqual(runner.current_learning_iteration, 3)
            for iteration in (1, 2, 3):
                checkpoint = torch.load(path / f'model_{iteration}.pt', map_location='cpu', weights_only=True)
                self.assertEqual(checkpoint['iter'], iteration)
            runner.alg.learning_rate = 3e-4
            runner.alg.optimizer.param_groups[0]['lr'] = 3e-4
            runner.alg.actor_critic.estimator.learning_rate = 4e-4
            runner.alg.actor_critic.estimator.optimizer.param_groups[0]['lr'] = 4e-4
            runner.save(path / 'resume.pt')
            expected = runner.get_inference_policy()(torch.zeros(4, 270))
            restored = make_runner(path)
            restored.load(path / 'resume.pt')
            self.assertEqual(restored.current_learning_iteration, 3)
            self.assertEqual(restored.alg.learning_rate, 3e-4)
            self.assertEqual(restored.alg.actor_critic.estimator.learning_rate, 4e-4)
            self.assertEqual(restored.tot_timesteps, runner.tot_timesteps)
            torch.testing.assert_close(restored.get_inference_policy()(torch.zeros(4, 270)), expected)
            with contextlib.redirect_stdout(io.StringIO()):
                restored.learn(2)
            self.assertEqual(restored.current_learning_iteration, 5)
            self.assertEqual(torch.load(path / 'model_4.pt', weights_only=True)['iter'], 4)
            self.assertEqual(torch.load(path / 'model_5.pt', weights_only=True)['iter'], 5)


if __name__ == '__main__':
    unittest.main()
