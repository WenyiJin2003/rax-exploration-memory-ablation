from __future__ import annotations

import csv
from dataclasses import asdict
import json
from pathlib import Path

from evaluate import evaluate_controller
from src.environment import build_episode
from src.svg_render import render_trajectory_svg


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CONTROLLERS = (
    ROOT / "controllers" / "naive_controller.py",
    ROOT / "controllers" / "adaptive_reference.py",
)


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    all_results = {}
    summary_rows = []

    for controller_path in CONTROLLERS:
        episodes, summary = evaluate_controller(controller_path, "heldout")
        name = controller_path.stem
        all_results[name] = {
            "label": "reference benchmark; not a language-model result",
            "summary": summary,
            "episodes": [asdict(episode) for episode in episodes],
        }
        summary_rows.append({"controller": name, **summary})

        example = next(episode for episode in episodes if episode.seed == 203)
        render_trajectory_svg(
            build_episode(example.seed),
            example.trace,
            RESULTS_DIR / f"trajectory_{name}_seed_{example.seed}.svg",
            f"{name.replace('_', ' ').title()} · held-out seed {example.seed}",
            example.success,
        )

    with (RESULTS_DIR / "benchmark.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "controller",
            "episodes",
            "success_rate",
            "mean_collisions",
            "mean_steps_success",
            "mean_score",
            "mean_runtime_ms",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    (RESULTS_DIR / "benchmark.json").write_text(
        json.dumps(all_results, indent=2), encoding="utf-8"
    )

    naive = all_results["naive_controller"]["summary"]
    adaptive = all_results["adaptive_reference"]["summary"]
    summary_text = f"""# Reference benchmark

These numbers validate the harness; they are **not** coding-agent results.

| Controller | Held-out success | Mean collisions | Mean steps, successes | Mean score |
|---|---:|---:|---:|---:|
| Direct-to-goal baseline | {naive['success_rate']:.1%} | {naive['mean_collisions']:.2f} | n/a | {naive['mean_score']:.2f} |
| Adaptive reference | {adaptive['success_rate']:.1%} | {adaptive['mean_collisions']:.2f} | {adaptive['mean_steps_success']:.1f} | {adaptive['mean_score']:.2f} |

The direct controller fails because it ignores obstacles and changing momentum. The reference controller demonstrates that the same held-out tasks are solvable using map-aware planning and velocity feedback. The scientifically relevant next step is to run coding agents under matched exploration budgets and compare repeated runs.
"""
    (RESULTS_DIR / "summary.md").write_text(summary_text, encoding="utf-8")
    print(summary_text)


if __name__ == "__main__":
    main()

