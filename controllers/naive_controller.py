from __future__ import annotations

import math


class Controller:
    """A deliberately weak controller: always accelerate directly at the goal."""

    def reset(self, observation: dict) -> None:
        pass

    def act(self, observation: dict) -> tuple[float, float]:
        x, y = observation["position"]
        goal_x, goal_y = observation["goal"]["position"]
        dx, dy = goal_x - x, goal_y - y
        distance = max(math.hypot(dx, dy), 1e-8)
        return dx / distance, dy / distance

