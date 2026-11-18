from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.environment import HiddenPhysicsEnv, load_state, save_state


ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / ".runtime"
STATE_PATH = RUNTIME_DIR / "session.json"
BUDGET_PATH = ROOT / "run_budget.json"
EXPLORE_SEEDS = range(101, 113)


def emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def require_session() -> HiddenPhysicsEnv:
    if not STATE_PATH.exists():
        raise SystemExit("No active episode. Run: python3 agent_api.py reset --seed 101")
    return load_state(str(STATE_PATH))


def consume_budget(seed: int, source: str) -> None:
    if not BUDGET_PATH.exists():
        return
    budget = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
    if budget["used"] >= budget["maximum"]:
        raise SystemExit(
            f"Exploration budget exhausted ({budget['used']}/{budget['maximum']} episodes)."
        )
    budget["used"] += 1
    budget["episodes"].append({"seed": seed, "source": source})
    BUDGET_PATH.write_text(json.dumps(budget, indent=2), encoding="utf-8")


def reset(seed: int) -> None:
    if seed not in EXPLORE_SEEDS:
        allowed = f"{EXPLORE_SEEDS.start}-{EXPLORE_SEEDS.stop - 1}"
        raise SystemExit(f"Seed {seed} is outside the exploration set ({allowed}).")
    consume_budget(seed, "agent_api.reset")
    RUNTIME_DIR.mkdir(exist_ok=True)
    env = HiddenPhysicsEnv.from_seed(seed)
    save_state(env, str(STATE_PATH))
    emit({"event": "reset", "seed": seed, "observation": env.observation()})


def observe() -> None:
    env = require_session()
    emit({"event": "observation", "observation": env.observation()})


def act(ax: float, ay: float, repeat: int) -> None:
    env = require_session()
    transitions = []
    for _ in range(max(1, repeat)):
        if env.done:
            break
        observation, reward, done, info = env.step((ax, ay))
        transitions.append(
            {
                "step": observation["step"],
                "position": observation["position"],
                "velocity": observation["velocity"],
                "terrain": observation["current_terrain"],
                "collision": observation["last_collision"],
                "reward": reward,
                "done": done,
                "success": observation["success"],
                "applied_action": info["applied_action"],
            }
        )
    save_state(env, str(STATE_PATH))
    emit(
        {
            "event": "action",
            "requested_action": [ax, ay],
            "transitions": transitions,
            "observation": env.observation(),
            "score_if_ended_now": round(env.score(), 3),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Black-box interaction API for exploration.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reset_parser = subparsers.add_parser("reset")
    reset_parser.add_argument("--seed", type=int, required=True)

    subparsers.add_parser("observe")

    act_parser = subparsers.add_parser("act")
    act_parser.add_argument("--ax", type=float, required=True)
    act_parser.add_argument("--ay", type=float, required=True)
    act_parser.add_argument("--repeat", type=int, default=1)

    args = parser.parse_args()
    if args.command == "reset":
        reset(args.seed)
    elif args.command == "observe":
        observe()
    else:
        act(args.ax, args.ay, args.repeat)


if __name__ == "__main__":
    main()

