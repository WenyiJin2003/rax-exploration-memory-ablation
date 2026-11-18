from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluate import evaluate_controller


def main() -> None:
    parser = argparse.ArgumentParser(description="Score one isolated agent submission.")
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    run_dir = args.run_directory.resolve()
    controller = run_dir / "controller.py"
    if not controller.exists():
        raise SystemExit(f"Missing controller: {controller}")
    metadata_path = run_dir / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    budget_path = run_dir / "run_budget.json"
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    if budget["used"] > budget["maximum"]:
        raise SystemExit(
            f"Invalid run: exploration budget exceeded ({budget['used']}/{budget['maximum']})."
        )
    episodes, summary = evaluate_controller(controller, "heldout")
    metadata.update(
        {
            "status": "scored",
            "model": args.model,
            "scored_at_utc": datetime.now(timezone.utc).isoformat(),
            "heldout_summary": summary,
            "exploration_budget": budget,
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (run_dir / "heldout_results.json").write_text(
        json.dumps(
            {"summary": summary, "episodes": [asdict(episode) for episode in episodes]},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

