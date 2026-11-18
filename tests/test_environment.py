from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluate import evaluate_controller
from src.environment import HiddenPhysicsEnv, load_state, save_state


ROOT = Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    def test_seed_is_deterministic(self) -> None:
        first = HiddenPhysicsEnv.from_seed(101)
        second = HiddenPhysicsEnv.from_seed(101)
        self.assertEqual(first.observation(), second.observation())
        for action in [(1.0, 0.0), (0.2, 0.8), (-0.5, 0.1)]:
            first.step(action)
            second.step(action)
        self.assertEqual(first.observation(), second.observation())

    def test_hidden_parameters_are_not_observed(self) -> None:
        observation = HiddenPhysicsEnv.from_seed(101).observation()
        self.assertNotIn("physics", observation)
        self.assertNotIn("action_gain", observation)
        self.assertNotIn("drag", observation)

    def test_state_round_trip(self) -> None:
        env = HiddenPhysicsEnv.from_seed(102)
        env.step((0.7, -0.2))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_state(env, str(path))
            restored = load_state(str(path))
        self.assertEqual(env.observation(), restored.observation())
        self.assertEqual(env.trace, restored.trace)

    def test_reference_benchmark_separates_controllers(self) -> None:
        _, naive = evaluate_controller(ROOT / "controllers" / "naive_controller.py", "heldout")
        _, adaptive = evaluate_controller(
            ROOT / "controllers" / "adaptive_reference.py", "heldout"
        )
        self.assertLessEqual(naive["success_rate"], 0.25)
        self.assertGreaterEqual(adaptive["success_rate"], 0.90)
        self.assertLess(adaptive["mean_collisions"], naive["mean_collisions"])


if __name__ == "__main__":
    unittest.main()

