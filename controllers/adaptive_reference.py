from __future__ import annotations

import heapq
import math


class Controller:
    """Reference planner plus terrain-aware velocity feedback."""

    def __init__(self) -> None:
        self.waypoints: list[tuple[float, float]] = []
        self.waypoint_index = 0
        self.recovery_steps = 0

    def reset(self, observation: dict) -> None:
        self.waypoints = self._plan(observation)
        self.waypoint_index = 0
        self.recovery_steps = 0

    @staticmethod
    def _inside_obstacle(
        point: tuple[float, float], obstacles: list[dict], margin: float
    ) -> bool:
        x, y = point
        return any(
            obstacle["x"] - margin <= x <= obstacle["x"] + obstacle["width"] + margin
            and obstacle["y"] - margin <= y <= obstacle["y"] + obstacle["height"] + margin
            for obstacle in obstacles
        )

    def _line_is_clear(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        obstacles: list[dict],
        margin: float,
    ) -> bool:
        distance = math.dist(start, end)
        samples = max(2, int(distance / 1.25))
        for index in range(samples + 1):
            alpha = index / samples
            point = (
                start[0] + alpha * (end[0] - start[0]),
                start[1] + alpha * (end[1] - start[1]),
            )
            if self._inside_obstacle(point, obstacles, margin):
                return False
        return True

    def _plan(self, observation: dict) -> list[tuple[float, float]]:
        resolution = 3.0
        width = observation["world"]["width"]
        height = observation["world"]["height"]
        radius = observation["rover_radius"]
        obstacles = observation["obstacles"]
        start = tuple(observation["position"])
        goal = tuple(observation["goal"]["position"])
        max_x = int(width // resolution)
        max_y = int(height // resolution)

        def to_node(point: tuple[float, float]) -> tuple[int, int]:
            return round(point[0] / resolution), round(point[1] / resolution)

        def to_point(node: tuple[int, int]) -> tuple[float, float]:
            return node[0] * resolution, node[1] * resolution

        def valid(node: tuple[int, int]) -> bool:
            px, py = to_point(node)
            if px < radius + 0.8 or px > width - radius - 0.8:
                return False
            if py < radius + 0.8 or py > height - radius - 0.8:
                return False
            return not self._inside_obstacle((px, py), obstacles, radius + 2.8)

        start_node, goal_node = to_node(start), to_node(goal)
        frontier: list[tuple[float, tuple[int, int]]] = [(0.0, start_node)]
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start_node: None}
        cost_so_far = {start_node: 0.0}
        neighbors = (
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        )

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal_node:
                break
            for delta_x, delta_y in neighbors:
                nxt = current[0] + delta_x, current[1] + delta_y
                if not (0 <= nxt[0] <= max_x and 0 <= nxt[1] <= max_y and valid(nxt)):
                    continue
                move_cost = math.hypot(delta_x, delta_y)
                new_cost = cost_so_far[current] + move_cost
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    heuristic = math.dist(nxt, goal_node)
                    heapq.heappush(frontier, (new_cost + heuristic, nxt))
                    came_from[nxt] = current

        if goal_node not in came_from:
            return [goal]

        nodes = []
        current: tuple[int, int] | None = goal_node
        while current is not None:
            nodes.append(current)
            current = came_from[current]
        points = [start] + [to_point(node) for node in reversed(nodes[1:-1])] + [goal]

        simplified = [points[0]]
        anchor = 0
        while anchor < len(points) - 1:
            candidate = len(points) - 1
            while candidate > anchor + 1:
                if self._line_is_clear(
                    points[anchor], points[candidate], obstacles, radius + 2.8
                ):
                    break
                candidate -= 1
            simplified.append(points[candidate])
            anchor = candidate
        return simplified[1:]

    def act(self, observation: dict) -> tuple[float, float]:
        x, y = observation["position"]
        vx, vy = observation["velocity"]
        goal = tuple(observation["goal"]["position"])

        if observation["last_collision"]:
            self.recovery_steps = 6
            self.waypoints = self._plan(observation)
            self.waypoint_index = 0
        if self.recovery_steps > 0:
            self.recovery_steps -= 1
            previous_ax, previous_ay = observation["previous_action"]
            magnitude = max(math.hypot(previous_ax, previous_ay), 1e-6)
            return -previous_ax / magnitude, -previous_ay / magnitude

        while self.waypoint_index < len(self.waypoints) - 1:
            waypoint = self.waypoints[self.waypoint_index]
            if math.dist((x, y), waypoint) >= 4.0:
                break
            self.waypoint_index += 1
        target = (
            self.waypoints[self.waypoint_index]
            if self.waypoints
            else goal
        )
        dx, dy = target[0] - x, target[1] - y
        distance = max(math.hypot(dx, dy), 1e-8)
        direction_x, direction_y = dx / distance, dy / distance

        terrain = observation["current_terrain"]
        if terrain == "slippery":
            desired_speed, estimated_drag, estimated_gain = 0.72, 0.94, 0.58
        elif terrain == "sticky":
            desired_speed, estimated_drag, estimated_gain = 0.92, 0.48, 0.30
        else:
            desired_speed, estimated_drag, estimated_gain = 1.18, 0.72, 0.55

        nearest_clearance = float("inf")
        for obstacle in observation["obstacles"]:
            nearest_x = min(max(x, obstacle["x"]), obstacle["x"] + obstacle["width"])
            nearest_y = min(max(y, obstacle["y"]), obstacle["y"] + obstacle["height"])
            nearest_clearance = min(
                nearest_clearance, math.dist((x, y), (nearest_x, nearest_y))
            )
        if nearest_clearance < 9.0:
            desired_speed = min(desired_speed, 0.62)

        goal_distance = math.dist((x, y), goal)
        desired_speed = min(desired_speed, max(0.25, 0.12 * goal_distance))
        if self.waypoint_index < len(self.waypoints) - 1 and distance < 8.0:
            desired_speed *= 0.72

        desired_vx = desired_speed * direction_x
        desired_vy = desired_speed * direction_y
        ax = (desired_vx - estimated_drag * vx) / estimated_gain
        ay = (desired_vy - estimated_drag * vy) / estimated_gain
        magnitude = max(1.0, math.hypot(ax, ay))
        return ax / magnitude, ay / magnitude

