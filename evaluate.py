from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import statistics
import time
from types import ModuleType

from src.environment import HiddenPhysicsEnv


EXPLORE_SEEDS = list(range(101, 113))
HELDOUT_SEEDS = list(range(201, 225))


@dataclass
class EpisodeResult:
    seed: int
    success: bool
    steps: int
    collisions: int
    score: float
    runtime_ms: float
    trace: list[tuple[float, float]]


def load_controller(path: Path):
    module_name = f"submitted_controller_{path.stem}_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "Controller"):
        raise ValueError(f"{path} must define class Controller")
    return module.Controller


def normalize_action(action) -> tuple[float, float]:
    if isinstance(action, dict):
        action = action["ax"], action["ay"]
    if not isinstance(action, (tuple, list)) or len(action) != 2:
        raise ValueError("Controller action must be (ax, ay) or {'ax': ax, 'ay': ay}.")
    return float(action[0]), float(action[1])


def run_episode(controller_class, seed: int) -> EpisodeResult:
    env = HiddenPhysicsEnv.from_seed(seed)
    controller = controller_class()
    observation = env.observation()
    if hasattr(controller, "reset"):
        controller.reset(observation)

    started = time.perf_counter()
    while not env.done:
        action = normalize_action(controller.act(observation))
        observation, _, _, _ = env.step(action)
    runtime_ms = (time.perf_counter() - started) * 1000.0
    return EpisodeResult(
        seed=seed,
        success=env.success,
        steps=env.step_count,
        collisions=env.collisions,
        score=round(env.score(), 4),
        runtime_ms=round(runtime_ms, 4),
        trace=list(env.trace),
    )


def summarize(results: list[EpisodeResult]) -> dict:
    successes = [result for result in results if result.success]
    return {
        "episodes": len(results),
        "success_rate": sum(result.success for result in results) / len(results),
        "mean_collisions": statistics.fmean(result.collisions for result in results),
        "mean_steps_success": (
            statistics.fmean(result.steps for result in successes) if successes else None
        ),
        "mean_score": statistics.fmean(result.score for result in results),
        "mean_runtime_ms": statistics.fmean(result.runtime_ms for result in results),
    }


def evaluate_controller(path: Path, split: str) -> tuple[list[EpisodeResult], dict]:
    seeds = EXPLORE_SEEDS if split == "explore" else HELDOUT_SEEDS
    controller_class = load_controller(path)
    results = [run_episode(controller_class, seed) for seed in seeds]
    return results, summarize(results)


def print_table(rows: list[tuple[str, dict]]) -> None:
    print(
        f"{'controller':<28} {'success':>9} {'collisions':>11} "
        f"{'steps*':>9} {'score':>9} {'runtime ms':>11}"
    )
    print("-" * 83)
    for name, summary in rows:
        steps = summary["mean_steps_success"]
        steps_text = "n/a" if steps is None else f"{steps:.1f}"
        print(
            f"{name:<28} {summary['success_rate']:>8.1%} "
            f"{summary['mean_collisions']:>11.2f} {steps_text:>9} "
            f"{summary['mean_score']:>9.2f} {summary['mean_runtime_ms']:>11.3f}"
        )
    print("* Mean steps among successful episodes only.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate controllers on fixed seeds.")
    parser.add_argument("controllers", nargs="+", type=Path)
    parser.add_argument("--split", choices=("explore", "heldout"), default="heldout")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    output = {}
    rows = []
    for path in args.controllers:
        results, summary = evaluate_controller(path, args.split)
        display_name = path.parent.name if path.stem == "controller" else path.stem
        rows.append((display_name, summary))
        output[display_name] = {
            "path": str(path),
            "split": args.split,
            "summary": summary,
            "episodes": [asdict(result) for result in results],
        }
    print_table(rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

