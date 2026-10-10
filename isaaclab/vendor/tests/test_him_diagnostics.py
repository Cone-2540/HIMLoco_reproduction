"""Read-only PPO instrumentation must preserve the original optimizer step."""

import contextlib
import copy
import io
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import torch

from him_rsl_rl.algorithms.him_ppo import HIMPPO
from test_him_runtime import make_model, make_runner


def reference_single_update(alg):
    """Pre-instrumentation PPO/estimator step, with one epoch and minibatch.

    This independent control checks gradients, optimizer state, adaptive LR,
    random-number consumption and the public losses against the old sequence.
    """
    batch = next(alg.storage.mini_batch_generator(1, 1))
    obs, critic, actions, next_critic, values, advantages, returns, logp, old_mu, old_std = batch
    model = alg.actor_critic
    model.act(obs)
    new_logp = model.get_actions_log_prob(actions)
    new_values = model.evaluate(critic)
    mu, std, entropy = model.action_mean, model.action_std, model.entropy
    if alg.desired_kl is not None and alg.schedule == 'adaptive':
        with torch.inference_mode():
            kl = (torch.log(std / old_std + 1e-5)
                  + (old_std.square() + (old_mu - mu).square()) / (2 * std.square()) - .5).sum(-1).mean()
            if kl > alg.desired_kl * 2:
                alg.learning_rate = max(1e-5, alg.learning_rate / 1.5)
            elif kl < alg.desired_kl / 2 and kl > 0:
                alg.learning_rate = min(1e-2, alg.learning_rate * 1.5)
            for group in alg.optimizer.param_groups:
                group['lr'] = alg.learning_rate
    estimation, swap = model.estimator.update(obs, next_critic, lr=alg.learning_rate)
    ratio = torch.exp(new_logp - logp.squeeze())
    surrogate = torch.max(-advantages.squeeze() * ratio,
                          -advantages.squeeze() * ratio.clamp(1 - alg.clip_param, 1 + alg.clip_param)).mean()
    clipped_values = values + (new_values - values).clamp(-alg.clip_param, alg.clip_param)
    value_loss = torch.max((new_values - returns).square(), (clipped_values - returns).square()).mean()
    loss = surrogate + alg.value_loss_coef * value_loss - alg.entropy_coef * entropy.mean()
    alg.optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), alg.max_grad_norm, error_if_nonfinite=True)
    alg.optimizer.step()
    with torch.no_grad():
        model.std.clamp_(min=1e-3)
    alg.storage.clear()
    return value_loss.item(), surrogate.item(), estimation, swap


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(13)
        torch.set_num_threads(1)

    def populated_algorithm(self, schedule='fixed', learning_rate=3e-4):
        alg = HIMPPO(make_model(), num_mini_batches=1, num_learning_epochs=1,
                     entropy_coef=.01, learning_rate=learning_rate, schedule=schedule)
        alg.init_storage(4, 1, [270], [48], [12])
        alg.act(torch.randn(4, 270), torch.randn(4, 48))
        alg.process_env_step(torch.arange(1, 5, dtype=torch.float), torch.zeros(4, dtype=torch.bool),
                             {}, torch.randn(4, 48))
        alg.compute_returns(torch.randn(4, 48))
        return alg

    def test_fixed_and_adaptive_diagnostics_preserve_losses_parameters_and_rng(self):
        for schedule in ('fixed', 'adaptive'):
            measured = self.populated_algorithm(schedule)
            control = HIMPPO(make_model(), num_mini_batches=1, num_learning_epochs=1,
                             entropy_coef=.01, learning_rate=3e-4, schedule=schedule)
            control.actor_critic.load_state_dict(measured.actor_critic.state_dict())
            control.storage = copy.deepcopy(measured.storage)
            rng = torch.random.get_rng_state()
            expected = reference_single_update(control)
            expected_rng = torch.random.get_rng_state()
            torch.random.set_rng_state(rng)
            actual = measured.update()
            self.assertEqual(len(actual), 4)
            torch.testing.assert_close(torch.tensor(actual), torch.tensor(expected), rtol=0, atol=0)
            for name, value in measured.actor_critic.state_dict().items():
                torch.testing.assert_close(value, control.actor_critic.state_dict()[name], rtol=0, atol=0)
            torch.testing.assert_close(torch.random.get_rng_state(), expected_rng, rtol=0, atol=0)
            self.assertEqual(measured.learning_rate, control.learning_rate)
            self.assertEqual(measured.actor_critic.estimator.learning_rate,
                             control.actor_critic.estimator.learning_rate)
            for actual_optimizer, expected_optimizer in (
                    (measured.optimizer, control.optimizer),
                    (measured.actor_critic.estimator.optimizer, control.actor_critic.estimator.optimizer)):
                actual_state, expected_state = actual_optimizer.state_dict(), expected_optimizer.state_dict()
                self.assertEqual(actual_state['param_groups'], expected_state['param_groups'])
                self.assertEqual(actual_state['state'].keys(), expected_state['state'].keys())
                for parameter, values in actual_state['state'].items():
                    for name, value in values.items():
                        torch.testing.assert_close(value, expected_state['state'][parameter][name], rtol=0, atol=0)
            self.assertTrue(all(math.isfinite(value) for value in measured.last_update_diagnostics.values()))

    def test_fixed_schedule_diagnostics_measure_saved_policy_and_clip_fraction(self):
        alg = self.populated_algorithm(learning_rate=0.)
        storage, model = alg.storage, alg.actor_critic
        ratios = torch.tensor([.5, 1., 1.5, 1.])
        storage.actions_log_prob[0, :, 0] -= ratios.log()
        storage.mu.add_(.3)
        storage.sigma.mul_(1.5)
        expected_kl = (torch.log(1 / storage.sigma[0] + 1e-5)
                       + (storage.sigma[0].square() + .3 ** 2) / 2 - .5).sum(-1).mean()
        with mock.patch.object(model.estimator, 'update', return_value=(0., 0.)):
            alg.update()
        metrics = alg.last_update_diagnostics
        self.assertAlmostEqual(metrics['kl_mean'], expected_kl.item(), places=5)
        self.assertEqual(metrics['kl_mean'], metrics['kl_max_minibatch_mean'])
        self.assertEqual(metrics['clip_fraction'], .5)
        self.assertEqual(metrics['std_min'], 1.)
        self.assertEqual(metrics['std_max'], 1.)
        self.assertEqual(metrics['learning_rate'], 0.)
        self.assertEqual(metrics['learning_rate_min'], 0.)
        self.assertEqual(metrics['learning_rate_max'], 0.)
        self.assertEqual(metrics['learning_rate_mean'], 0.)

    def test_learning_rate_range_uses_each_minibatch_optimizer_rate(self):
        alg = self.populated_algorithm(schedule='adaptive')
        alg.num_mini_batches, alg.num_learning_epochs = 2, 2
        alg.storage.mu.add_(.3)  # KL stays above the adaptive reduction threshold.
        estimator = alg.actor_critic.estimator
        with mock.patch.object(estimator, 'update', wraps=estimator.update) as update:
            alg.update()
        rates = [call.kwargs['lr'] for call in update.call_args_list]
        self.assertEqual(len(rates), 4)
        self.assertLess(min(rates), max(rates))
        metrics = alg.last_update_diagnostics
        self.assertEqual(metrics['learning_rate_min'], min(rates))
        self.assertEqual(metrics['learning_rate_max'], max(rates))
        self.assertEqual(metrics['learning_rate_mean'], sum(rates) / len(rates))
        self.assertEqual(metrics['learning_rate'], rates[-1])

    def test_runner_writes_diagnostics_at_each_update_without_changing_checkpoint_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            runner = make_runner(path)
            writer = mock.Mock()
            runner.writer = writer
            with contextlib.redirect_stdout(io.StringIO()):
                runner.learn(2)
            diagnostic_calls = [call.args for call in writer.add_scalar.call_args_list
                                if call.args[0].startswith('PPO/')]
            self.assertEqual(len(diagnostic_calls), 18)
            self.assertEqual({args[2] for args in diagnostic_calls}, {0, 1})
            self.assertEqual({args[0] for args in diagnostic_calls},
                             {'PPO/' + name for name in runner.alg.last_update_diagnostics})
            checkpoint = torch.load(path / 'model_2.pt', map_location='cpu', weights_only=True)
            self.assertNotIn('last_update_diagnostics', checkpoint)


if __name__ == '__main__':
    unittest.main()
