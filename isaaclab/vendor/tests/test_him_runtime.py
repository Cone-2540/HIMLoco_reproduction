"""CPU regression tests for compatibility fixes, without importing Isaac Sim."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def make_runner(path):
    cfg = {
        'runner': {'policy_class_name': 'HIMActorCritic', 'algorithm_class_name': 'HIMPPO',
                   'num_steps_per_env': 1, 'save_interval': 1},
        'policy': {'actor_hidden_dims': [16], 'critic_hidden_dims': [16]},
        'algorithm': {'num_learning_epochs': 1, 'num_mini_batches': 2},
    }
    with contextlib.redirect_stdout(io.StringIO()):
        return HIMOnPolicyRunner(FakeEnv(), cfg, str(path), device='cpu')


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
