#!/usr/bin/env python3
"""Render one three-controller comparison GIF for every held-out episode."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.environment import build_episode


DEFAULT_OUTPUT = ROOT / "classroom_artifacts" / "heldout_gifs"
WIDTH, HEIGHT = 800, 450
MAP = (28, 78, 520, 416)
MAX_STEPS = 240
MOVING_FRAMES = 54
HOLD_FRAMES = 10

SERIES = (
    ("ZERO-SHOT", "codex_zero_01", "#8D99A8"),
    ("EXPLORE", "codex_nomemory_strict_01", "#16A6B8"),
    ("EXPLORE + MEMORY", "codex_full_strict_01", "#7657E8"),
)

COLORS = {
    "bg": "#0D1117",
    "panel": "#151B23",
    "map": "#F4F0E8",
    "grid": "#DDD8CE",
    "obstacle": "#222B35",
    "sticky": "#E5B24C",
    "slippery": "#72C2DF",
    "goal": "#2EBD73",
    "start": "#F2A45F",
    "text": "#F3F1EC",
    "muted": "#96A0AD",
    "rule": "#303844",
    "danger": "#F45B55",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


FONTS = {
    "kicker": font(10, True),
    "title": font(23, True),
    "small": font(10),
    "small_bold": font(10, True),
    "status": font(18, True),
    "micro": font(8, True),
}


def load_episodes() -> dict[str, dict[int, dict]]:
    loaded: dict[str, dict[int, dict]] = {}
    for _, run_name, _ in SERIES:
        path = ROOT / "runs" / run_name / "heldout_results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        loaded[run_name] = {int(item["seed"]): item for item in data["episodes"]}
    return loaded


def xy(spec, x: float, y: float) -> tuple[float, float]:
    left, top, right, bottom = MAP
    return (
        left + x / spec.width * (right - left),
        bottom - y / spec.height * (bottom - top),
    )


def rect_xy(spec, rect) -> tuple[int, int, int, int]:
    x0, y1 = xy(spec, rect.x, rect.y)
    x1, y0 = xy(spec, rect.x + rect.width, rect.y + rect.height)
    return (round(x0), round(y0), round(x1), round(y1))


def draw_map(draw: ImageDraw.ImageDraw, spec) -> None:
    left, top, right, bottom = MAP
    draw.rounded_rectangle(MAP, radius=7, fill=COLORS["map"])

    for x in range(10, 100, 10):
        px, _ = xy(spec, x, 0)
        draw.line((px, top, px, bottom), fill=COLORS["grid"], width=1)
    for y in range(10, 70, 10):
        _, py = xy(spec, 0, y)
        draw.line((left, py, right, py), fill=COLORS["grid"], width=1)

    for zone in spec.terrains:
        box = rect_xy(spec, zone.rectangle)
        fill = COLORS[zone.name]
        draw.rectangle(box, fill=fill)
        x0, y0, x1, y1 = box
        if zone.name == "sticky":
            for offset in range(-80, 160, 12):
                draw.line((x0 + offset, y1, x0 + offset + (y1 - y0), y0), fill="#C58B27", width=2)
        else:
            for yy in range(y0 + 8, y1, 13):
                points = []
                for xx in range(x0, x1 + 1, 4):
                    points.append((xx, yy + 2.2 * math.sin((xx - x0) / 7)))
                if len(points) > 1:
                    draw.line(points, fill="#3E9DC4", width=1)
        draw.text((x0 + 5, y0 + 5), zone.name.upper(), font=FONTS["micro"], fill="#1F2A33")

    for obstacle in spec.obstacles:
        draw.rounded_rectangle(rect_xy(spec, obstacle), radius=2, fill=COLORS["obstacle"])

    gx, gy = xy(spec, *spec.goal)
    goal_r = spec.goal_radius / spec.width * (right - left)
    draw.ellipse((gx - goal_r - 5, gy - goal_r - 5, gx + goal_r + 5, gy + goal_r + 5), outline="#89DDB0", width=2)
    draw.ellipse((gx - goal_r, gy - goal_r, gx + goal_r, gy + goal_r), fill="#C5F0D7", outline=COLORS["goal"], width=2)
    draw.text((gx - 11, gy - 4), "GOAL", font=FONTS["micro"], fill="#14633C")

    sx, sy = xy(spec, *spec.start)
    draw.ellipse((sx - 4, sy - 4, sx + 4, sy + 4), fill=COLORS["start"], outline="#FFFFFF", width=1)
    draw.text((sx - 23, sy - 17), "START", font=FONTS["micro"], fill="#4D5863")


def collision_count(trace: list[list[float]], step: int) -> int:
    count = 0
    for index in range(2, min(step, len(trace) - 1) + 1):
        x, y = trace[index]
        px, py = trace[index - 1]
        if abs(x - px) < 1e-9 and abs(y - py) < 1e-9:
            count += 1
    return count


def draw_series(draw: ImageDraw.ImageDraw, spec, episode: dict, color: str, global_step: int) -> tuple[int, int, str]:
    trace = episode["trace"]
    step = min(global_step, len(trace) - 1)
    visible = trace[: step + 1]
    points = [xy(spec, x, y) for x, y in visible]
    if len(points) > 1:
        draw.line(points, fill=color, width=4, joint="curve")
        tail = points[max(0, len(points) - 10) :]
        if len(tail) > 1:
            draw.line(tail, fill=color, width=6, joint="curve")
    px, py = points[-1]
    draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=color, outline="#FFFFFF", width=2)

    contacts = collision_count(trace, step)
    if episode["success"] and global_step >= episode["steps"]:
        state = f"arrived · {episode['steps']} steps"
    elif global_step >= episode["steps"]:
        state = f"stopped · {episode['steps']} steps"
    else:
        state = f"step {min(global_step, episode['steps'])}"
    return contacts, step, state


def make_frame(seed: int, frame_index: int, episodes: dict[str, dict[int, dict]]) -> Image.Image:
    spec = build_episode(seed)
    progress = min(1.0, frame_index / (MOVING_FRAMES - 1))
    global_step = round(progress * MAX_STEPS)

    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(image)
    draw.text((28, 17), f"HELD-OUT TEST  {seed - 200:02d} / 24   ·   SEED {seed}", font=FONTS["kicker"], fill=COLORS["muted"])
    draw.text((28, 38), "Same world, three compiled controllers", font=FONTS["title"], fill=COLORS["text"])
    draw.text((772, 48), f"step {global_step:03d} / 240", anchor="ra", font=FONTS["small"], fill=COLORS["muted"])

    draw_map(draw, spec)
    status_x = 573
    for index, (label, run_name, color) in enumerate(SERIES):
        episode = episodes[run_name][seed]
        contacts, _, state = draw_series(draw, spec, episode, color, global_step)
        y = 111 + index * 101
        draw.line((status_x, y - 17, 772, y - 17), fill=COLORS["rule"], width=1)
        draw.ellipse((status_x, y, status_x + 9, y + 9), fill=color)
        draw.text((status_x + 16, y - 1), label, font=FONTS["small_bold"], fill="#D8DDE4")
        state_color = COLORS["goal"] if state.startswith("arrived") else COLORS["danger"] if state.startswith("stopped") else COLORS["text"]
        draw.text((status_x, y + 25), state, font=FONTS["status"], fill=state_color)
        draw.text((status_x, y + 51), f"{contacts} contacts", font=FONTS["small"], fill=COLORS["muted"])

    draw.text((573, 394), "The coding agent is absent at test time.", font=FONTS["small_bold"], fill="#D8DDE4")
    draw.text((573, 410), "Only the saved controller.py is running.", font=FONTS["small"], fill=COLORS["muted"])

    timeline_left, timeline_right, timeline_y = 28, 772, 439
    draw.line((timeline_left, timeline_y, timeline_right, timeline_y), fill=COLORS["rule"], width=2)
    progress_x = timeline_left + progress * (timeline_right - timeline_left)
    draw.line((timeline_left, timeline_y, progress_x, timeline_y), fill="#E9E3D9", width=2)
    draw.ellipse((progress_x - 3, timeline_y - 3, progress_x + 3, timeline_y + 3), fill=COLORS["start"])
    return image


def render_seed(seed: int, episodes: dict[str, dict[int, dict]], output_dir: Path) -> Path:
    frames = [make_frame(seed, index, episodes) for index in range(MOVING_FRAMES)]
    final_frame = frames[-1]
    frames.extend(final_frame.copy() for _ in range(HOLD_FRAMES))
    output = output_dir / f"test_{seed - 200:02d}_seed_{seed}.gif"
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=85,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, action="append", help="Render only this seed; may be repeated.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    episodes = load_episodes()
    seeds = args.seed or sorted(set.intersection(*(set(items) for items in episodes.values())))
    for index, seed in enumerate(seeds, start=1):
        output = render_seed(seed, episodes, args.output)
        print(f"[{index:02d}/{len(seeds):02d}] {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
