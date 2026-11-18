from __future__ import annotations

import argparse
import json
from pathlib import Path
import py_compile
import shutil


ROOT = Path(__file__).resolve().parents[1]


def condition_rules(condition: str) -> str:
    if condition == "full_memory":
        return """
- You may use up to 12 exploration episodes through `agent_api.py`.
- Maintain `workspace/memory.md`, `workspace/skills.md`, and `workspace/run_log.md`.
- Use the workspace to preserve empirical findings and reusable control ideas.
"""
    if condition == "no_memory":
        return """
- You may use up to 12 exploration episodes through `agent_api.py`.
- Do not create or read persistent notes. The `workspace/` directory is unavailable.
- You may use observations in the current context, but only `controller.py` is retained.
"""
    return """
- Do not call `agent_api.py` and do not inspect exploration trajectories.
- Write `controller.py` directly from `TASK.md` and the public observation/action contract.
- This is the zero-shot condition.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an isolated coding-agent run directory.")
    parser.add_argument("name")
    parser.add_argument(
        "--condition",
        choices=("full_memory", "no_memory", "zero_shot"),
        required=True,
    )
    args = parser.parse_args()

    run_dir = ROOT / "runs" / args.name
    if run_dir.exists():
        raise SystemExit(f"Run directory already exists: {run_dir}")
    (run_dir / "src").mkdir(parents=True)

    shutil.copy2(ROOT / "TASK.md", run_dir / "TASK.md")
    shutil.copy2(ROOT / "OBSERVATION_CONTRACT.md", run_dir / "OBSERVATION_CONTRACT.md")
    shutil.copy2(ROOT / "agent_api.py", run_dir / "agent_api.py")
    shutil.copy2(ROOT / "agent_assets" / "explore_evaluate.py", run_dir / "explore_evaluate.py")
    (run_dir / "src" / "__init__.py").write_text("", encoding="utf-8")
    py_compile.compile(
        str(ROOT / "src" / "environment.py"),
        cfile=str(run_dir / "src" / "environment.pyc"),
        doraise=True,
    )

    if args.condition == "full_memory":
        (run_dir / "workspace").mkdir()
        for filename in ("memory.md", "skills.md", "run_log.md"):
            shutil.copy2(ROOT / "workspace" / filename, run_dir / "workspace" / filename)

    evaluation_rule = (
        "- Do not run `explore_evaluate.py`; evaluation feedback is unavailable in this condition."
        if args.condition == "zero_shot"
        else "- You may run `python3 explore_evaluate.py` on the public exploration seeds."
    )
    rules = f"""# Coding-agent experiment rules

Your goal is to solve the task in `TASK.md` and leave a final `controller.py`.

## Condition: {args.condition}

{condition_rules(args.condition)}

## Shared restrictions

- Treat `src/environment.pyc` as a black box. Do not inspect, disassemble, or reverse engineer it.
- Do not access parent directories, reference controllers, held-out seeds, the internet, or external tools.
- Do not install packages. Use the Python standard library.
- `run_budget.json` is an automatic audit record. You may read it but must not edit it.
{evaluation_rule}
- Actions must stay in [-1, 1]. Do not hard-code seed-specific trajectories.
- Finish by checking that `controller.py` imports and runs.
"""
    (run_dir / "AGENTS.md").write_text(rules, encoding="utf-8")
    metadata = {
        "name": args.name,
        "condition": args.condition,
        "status": "prepared",
        "exploration_seeds": list(range(101, 113)),
        "heldout_seeds_visible_to_agent": False,
    }
    (run_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    maximum = 0 if args.condition == "zero_shot" else 12
    (run_dir / "run_budget.json").write_text(
        json.dumps({"maximum": maximum, "used": 0, "episodes": []}, indent=2),
        encoding="utf-8",
    )
    print(run_dir)


if __name__ == "__main__":
    main()

