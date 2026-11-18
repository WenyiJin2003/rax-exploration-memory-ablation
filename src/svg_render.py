from __future__ import annotations

import html
from pathlib import Path

from src.environment import EpisodeSpec


def render_trajectory_svg(
    spec: EpisodeSpec,
    trace: list[tuple[float, float]],
    output_path: Path,
    title: str,
    success: bool,
) -> None:
    scale = 7.4
    margin = 34.0
    canvas_width = spec.width * scale + 2 * margin
    canvas_height = spec.height * scale + 2 * margin + 46.0

    def sx(x: float) -> float:
        return margin + x * scale

    def sy(y: float) -> float:
        return margin + (spec.height - y) * scale

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width:.0f}" '
        f'height="{canvas_height:.0f}" viewBox="0 0 {canvas_width:.0f} {canvas_height:.0f}">',
        "<style>text{font-family:Inter,Arial,sans-serif}.label{font-size:13px;fill:#334155}</style>",
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="{margin:.1f}" y="22" font-size="17" font-weight="700" fill="#0f172a">'
        f"{html.escape(title)}</text>",
        f'<rect x="{margin}" y="{margin}" width="{spec.width * scale}" '
        f'height="{spec.height * scale}" rx="5" fill="#ffffff" stroke="#94a3b8" stroke-width="1.5"/>',
    ]

    terrain_colors = {"sticky": "#f59e0b", "slippery": "#38bdf8"}
    for zone in spec.terrains:
        rect = zone.rectangle
        elements.append(
            f'<rect x="{sx(rect.x):.2f}" y="{sy(rect.y + rect.height):.2f}" '
            f'width="{rect.width * scale:.2f}" height="{rect.height * scale:.2f}" '
            f'fill="{terrain_colors.get(zone.name, "#cbd5e1")}" opacity="0.22"/>'
        )
        elements.append(
            f'<text class="label" x="{sx(rect.x) + 5:.2f}" y="{sy(rect.y + rect.height) + 16:.2f}">'
            f"{html.escape(zone.name)}</text>"
        )

    for obstacle in spec.obstacles:
        elements.append(
            f'<rect x="{sx(obstacle.x):.2f}" y="{sy(obstacle.y + obstacle.height):.2f}" '
            f'width="{obstacle.width * scale:.2f}" height="{obstacle.height * scale:.2f}" '
            'fill="#334155" rx="2"/>'
        )

    points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in trace)
    elements.append(
        f'<polyline points="{points}" fill="none" stroke="#7c3aed" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round" opacity="0.92"/>'
    )
    start_x, start_y = spec.start
    goal_x, goal_y = spec.goal
    elements.extend(
        [
            f'<circle cx="{sx(start_x):.2f}" cy="{sy(start_y):.2f}" r="7" fill="#f97316" stroke="#fff" stroke-width="2"/>',
            f'<circle cx="{sx(goal_x):.2f}" cy="{sy(goal_y):.2f}" r="{spec.goal_radius * scale:.2f}" fill="#22c55e" opacity="0.25" stroke="#16a34a" stroke-width="2"/>',
            f'<circle cx="{sx(trace[-1][0]):.2f}" cy="{sy(trace[-1][1]):.2f}" r="6" '
            f'fill="{"#16a34a" if success else "#dc2626"}" stroke="#fff" stroke-width="2"/>',
            f'<text class="label" x="{margin}" y="{canvas_height - 14:.1f}">'
            'start = orange · goal = green · final position = '
            f'{"green" if success else "red"} · trajectory = purple</text>',
            "</svg>",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(elements), encoding="utf-8")

