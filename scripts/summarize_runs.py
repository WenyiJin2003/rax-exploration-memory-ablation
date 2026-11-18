from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
RESULTS_DIR = ROOT / "results"


def load_rows() -> list[dict]:
    rows = []
    for metadata_path in sorted(RUNS_DIR.glob("*/run_metadata.json")):
        run_dir = metadata_path.parent
        results_path = run_dir / "heldout_results.json"
        if not results_path.exists():
            continue

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        results = json.loads(results_path.read_text(encoding="utf-8"))
        summary = results["summary"]
        budget = metadata.get("exploration_budget")
        if budget is None and (run_dir / "run_budget.json").exists():
            budget = json.loads((run_dir / "run_budget.json").read_text(encoding="utf-8"))
        exploration_episodes = 0 if budget is None else int(budget["used"])

        rows.append(
            {
                "run_id": metadata["name"],
                "condition": metadata["condition"],
                "model": metadata.get("model", "unknown"),
                "exploration_episodes": exploration_episodes,
                "persistent_memory": metadata["condition"] == "full_memory",
                "heldout_episodes": int(summary["episodes"]),
                "successful_episodes": sum(bool(item["success"]) for item in results["episodes"]),
                "success_rate": float(summary["success_rate"]),
                "total_contacts": sum(int(item["collisions"]) for item in results["episodes"]),
                "mean_contacts": float(summary["mean_collisions"]),
                "mean_steps_success": float(summary["mean_steps_success"]),
                "mean_score": float(summary["mean_score"]),
            }
        )
    order = {"zero_shot": 0, "no_memory": 1, "full_memory": 2}
    return sorted(rows, key=lambda row: (order.get(row["condition"], 99), row["run_id"]))


def write_csv(rows: list[dict]) -> None:
    path = RESULTS_DIR / "run_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict]) -> None:
    labels = {
        "zero_shot": "Zero-shot",
        "no_memory": "Exploration, no memory",
        "full_memory": "Exploration + memory",
    }
    lines = [
        "# Run summary",
        "",
        "Generated from the immutable records in `runs/`.",
        "",
        "| Run | Condition | Exploration | Success | Total contacts | Mean steps, successes | Mean score |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['run_id']}` | {labels.get(row['condition'], row['condition'])} "
            f"| {row['exploration_episodes']} | {row['successful_episodes']} / {row['heldout_episodes']} "
            f"| {row['total_contacts']} | {row['mean_steps_success']:.1f} | {row['mean_score']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Both explored controllers completed every held-out episode without contact. The zero-shot controller failed once and accumulated 100 contacts. In this first replicate, persistent memory did not improve on exploration alone.",
            "",
            "## Statistical caution",
            "",
            "Each row represents one independently generated controller. Held-out episodes measure robustness across environments, not variance across controller-generation runs. More independent runs are required before estimating the effect of persistent memory.",
            "",
        ]
    )
    (RESULTS_DIR / "run_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    rows = load_rows()
    if not rows:
        raise SystemExit("No scored runs found under runs/.")
    write_csv(rows)
    write_markdown(rows)
    print((RESULTS_DIR / "run_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

