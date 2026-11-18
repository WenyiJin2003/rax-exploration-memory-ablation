from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import statistics

from src.environment import HiddenPhysicsEnv


EXPLORE_SEEDS = list(range(101, 113))
BUDGET_PATH = Path("run_budget.json")


def load_controller():
    path = Path("controller.py")
    if not path.exists():
        raise SystemExit("Create controller.py before running this evaluation.")
    spec = importlib.util.spec_from_file_location("candidate_controller", path)
    if spec is None or spec.loader is None:
        raise SystemExit("Could not import controller.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Controller


def normalize_action(action) -> tuple[float, float]:
    if isinstance(action, dict):
        action = action["ax"], action["ay"]
    return float(action[0]), float(action[1])


def main() -> None:
    controller_class = load_controller()
    seeds = list(EXPLORE_SEEDS)
    if BUDGET_PATH.exists():
        budget = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
        remaining = budget["maximum"] - budget["used"]
        previously_used = {item["seed"] for item in budget["episodes"]}
        seeds = [seed for seed in seeds if seed not in previously_used][:remaining]
        if not seeds:
            raise SystemExit(
                f"No evaluation episodes remain ({budget['used']}/{budget['maximum']} used)."
            )
        for seed in seeds:
            budget["episodes"].append({"seed": seed, "source": "explore_evaluate"})
        budget["used"] += len(seeds)
        BUDGET_PATH.write_text(json.dumps(budget, indent=2), encoding="utf-8")
    rows = []
    for seed in seeds:
        env = HiddenPhysicsEnv.from_seed(seed)
        controller = controller_class()
        observation = env.observation()
        if hasattr(controller, "reset"):
            controller.reset(observation)
        while not env.done:
            observation, _, _, _ = env.step(normalize_action(controller.act(observation)))
        rows.append((seed, env.success, env.step_count, env.collisions, env.score()))

    success_rate = sum(row[1] for row in rows) / len(rows)
    mean_collisions = statistics.fmean(row[3] for row in rows)
    successful_steps = [row[2] for row in rows if row[1]]
    mean_steps = statistics.fmean(successful_steps) if successful_steps else None
    print("seed  success  steps  collisions  score")
    for seed, success, steps, collisions, score in rows:
        print(f"{seed:<5} {str(success):<8} {steps:<6} {collisions:<11} {score:.2f}")
    print(f"success_rate={success_rate:.1%}")
    print(f"mean_collisions={mean_collisions:.2f}")
    print(f"mean_steps_success={'n/a' if mean_steps is None else f'{mean_steps:.1f}'}")
    if BUDGET_PATH.exists():
        print(f"budget_used={budget['used']}/{budget['maximum']}")


if __name__ == "__main__":
    main()

