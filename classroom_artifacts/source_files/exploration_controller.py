"""Robust feedback controller for the hidden-physics rover task.

The planner uses only the public observation.  Motion control deliberately favors
clearance and low speed over time because acceleration, drag, drift, and delay are
not known in advance.
"""

from __future__ import annotations

import heapq
import math


class Controller:
    def __init__(self):
        self.path = []
        self.path_index = 0
        self.clearance = 0.0
        self.last_velocity = (0.0, 0.0)
        self.recovery = 0

    @staticmethod
    def _clamp(value, low=-1.0, high=1.0):
        return max(low, min(high, value))

    @staticmethod
    def _distance(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def reset(self, observation):
        self.clearance = float(observation["rover_radius"]) + 1.15
        self.path = self._plan(observation)
        self.path_index = 1 if len(self.path) > 1 else 0
        self.last_velocity = tuple(observation["velocity"])
        self.recovery = 0

    def _blocked(self, point, observation, extra=0.0):
        x, y = point
        radius = float(observation["rover_radius"]) + 0.35 + extra
        width = float(observation["world"]["width"])
        height = float(observation["world"]["height"])
        if x < radius or x > width - radius or y < radius or y > height - radius:
            return True
        margin = self.clearance + extra
        for obstacle in observation["obstacles"]:
            if (obstacle["x"] - margin <= x <= obstacle["x"] + obstacle["width"] + margin and
                    obstacle["y"] - margin <= y <= obstacle["y"] + obstacle["height"] + margin):
                return True
        return False

    def _segment_clear(self, start, end, observation):
        distance = self._distance(start, end)
        # Dense sampling makes smoothed diagonal segments respect inflated boxes.
        samples = max(1, int(math.ceil(distance / 0.45)))
        for i in range(1, samples):
            t = i / samples
            point = (start[0] + (end[0] - start[0]) * t,
                     start[1] + (end[1] - start[1]) * t)
            if self._blocked(point, observation):
                return False
        return True

    @staticmethod
    def _terrain_multiplier(point, observation):
        x, y = point
        for zone in observation["terrain_zones"]:
            if (zone["x"] <= x <= zone["x"] + zone["width"] and
                    zone["y"] <= y <= zone["y"] + zone["height"]):
                return 1.32 if zone["name"] == "slippery" else 1.10
        return 1.0

    def _plan(self, observation):
        start = tuple(map(float, observation["position"]))
        goal = tuple(map(float, observation["goal"]["position"]))
        if self._segment_clear(start, goal, observation):
            return [start, goal]

        width = float(observation["world"]["width"])
        height = float(observation["world"]["height"])
        spacing = 2.0
        edge = float(observation["rover_radius"]) + 0.55
        xs = []
        x = edge
        while x <= width - edge + 1e-9:
            xs.append(x)
            x += spacing
        ys = []
        y = edge
        while y <= height - edge + 1e-9:
            ys.append(y)
            y += spacing

        cells = {}
        for ix, x in enumerate(xs):
            for iy, y in enumerate(ys):
                if not self._blocked((x, y), observation):
                    cells[(ix, iy)] = (x, y)
        if not cells:
            return [start, goal]

        start_cell = min(cells, key=lambda c: self._distance(cells[c], start))
        goal_cell = min(cells, key=lambda c: self._distance(cells[c], goal))
        frontier = [(0.0, start_cell)]
        cost = {start_cell: 0.0}
        parent = {}
        directions = ((-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1))

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal_cell:
                break
            base = cost[current]
            for dx, dy in directions:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt not in cells:
                    continue
                # Prevent diagonals from cutting between blocked grid cells.
                if dx and dy:
                    if ((current[0] + dx, current[1]) not in cells or
                            (current[0], current[1] + dy) not in cells):
                        continue
                step_cost = math.hypot(dx, dy) * spacing
                step_cost *= self._terrain_multiplier(cells[nxt], observation)
                new_cost = base + step_cost
                if new_cost < cost.get(nxt, float("inf")):
                    cost[nxt] = new_cost
                    parent[nxt] = current
                    heuristic = self._distance(cells[nxt], cells[goal_cell])
                    heapq.heappush(frontier, (new_cost + heuristic, nxt))

        if goal_cell not in cost:
            return [start, goal]
        chain = [goal_cell]
        while chain[-1] != start_cell:
            chain.append(parent[chain[-1]])
        chain.reverse()
        raw = [start] + [cells[cell] for cell in chain[1:-1]] + [goal]

        # Greedily retain the farthest visible point for a short, smooth route.
        smooth = [raw[0]]
        anchor = 0
        while anchor < len(raw) - 1:
            candidate = len(raw) - 1
            while candidate > anchor + 1:
                if self._segment_clear(raw[anchor], raw[candidate], observation):
                    break
                candidate -= 1
            smooth.append(raw[candidate])
            anchor = candidate
        return smooth

    def _near_obstacle(self, position, observation):
        x, y = position
        best = float("inf")
        for obstacle in observation["obstacles"]:
            left, right = obstacle["x"], obstacle["x"] + obstacle["width"]
            bottom, top = obstacle["y"], obstacle["y"] + obstacle["height"]
            dx = max(left - x, 0.0, x - right)
            dy = max(bottom - y, 0.0, y - top)
            best = min(best, math.hypot(dx, dy) - observation["rover_radius"])
        return best

    def act(self, observation):
        if not self.path:
            self.reset(observation)

        position = tuple(map(float, observation["position"]))
        velocity = tuple(map(float, observation["velocity"]))
        goal = tuple(map(float, observation["goal"]["position"]))
        goal_distance = float(observation["goal"]["distance"])

        if observation["last_collision"]:
            self.recovery = 5
            self.path = self._plan(observation)
            self.path_index = 1 if len(self.path) > 1 else 0

        # Advance only after getting close enough to a waypoint.  At low speed a
        # modest radius avoids dithering around an exact grid coordinate.
        while self.path_index < len(self.path) - 1:
            target = self.path[self.path_index]
            if self._distance(position, target) > 2.25:
                break
            self.path_index += 1

        target = self.path[min(self.path_index, len(self.path) - 1)]
        to_target = (target[0] - position[0], target[1] - position[1])
        target_distance = math.hypot(*to_target)
        if target_distance < 1e-7:
            direction = (0.0, 0.0)
        else:
            direction = (to_target[0] / target_distance, to_target[1] / target_distance)

        terrain = observation["current_terrain"]
        max_speed = 1.85
        if terrain == "slippery":
            max_speed = 1.05
        elif terrain == "sticky":
            max_speed = 1.45
        if self._near_obstacle(position, observation) < 3.3:
            max_speed = min(max_speed, 1.0)

        final_leg = self.path_index == len(self.path) - 1
        if final_leg:
            remaining = max(0.0, goal_distance - float(observation["goal"]["radius"]))
            max_speed = min(max_speed, max(0.28, 0.58 * remaining + 0.18))
            target = goal
        else:
            # Approach a sharp waypoint slowly enough to turn despite delay.
            max_speed = min(max_speed, max(0.48, 0.48 * target_distance))

        desired_velocity = (direction[0] * max_speed, direction[1] * max_speed)
        gain = 0.78 if terrain != "slippery" else 0.62
        ax = gain * (desired_velocity[0] - velocity[0])
        ay = gain * (desired_velocity[1] - velocity[1])

        # A collision normally zeroes a component of velocity.  Briefly push
        # toward the current safe waypoint at reduced authority to separate.
        if self.recovery > 0:
            self.recovery -= 1
            ax = 0.65 * direction[0] - 0.45 * velocity[0]
            ay = 0.65 * direction[1] - 0.45 * velocity[1]

        self.last_velocity = velocity
        return (self._clamp(ax), self._clamp(ay))
