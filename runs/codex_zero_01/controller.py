"""Conservative zero-shot controller for the hidden-physics rover task.

The controller uses only fields documented in OBSERVATION_CONTRACT.md.  Static
geometry is handled by a visibility graph; motion is controlled from measured
velocity, so no particular acceleration, drag, or action latency is assumed.
"""

import heapq
import math


class Controller:
    def __init__(self):
        self.path = []
        self.last_position = None
        self.last_goal_distance = None
        self.stalled_steps = 0
        self.extra_clearance = 0.0
        self.hard_rects = []
        self.safe_rects = []

    @staticmethod
    def _clip(value, low=-1.0, high=1.0):
        return max(low, min(high, value))

    @staticmethod
    def _distance(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _inside(point, rect, eps=1e-10):
        x, y = point
        left, bottom, right, top = rect
        return (left - eps <= x <= right + eps and
                bottom - eps <= y <= top + eps)

    @staticmethod
    def _segment_intersects_rect(a, b, rect):
        """Closed segment/rectangle intersection using the slab method."""
        left, bottom, right, top = rect
        dx, dy = b[0] - a[0], b[1] - a[1]
        enter, leave = 0.0, 1.0
        for origin, delta, low, high in (
                (a[0], dx, left, right), (a[1], dy, bottom, top)):
            if abs(delta) < 1e-12:
                if origin < low or origin > high:
                    return False
                continue
            t0 = (low - origin) / delta
            t1 = (high - origin) / delta
            if t0 > t1:
                t0, t1 = t1, t0
            enter = max(enter, t0)
            leave = min(leave, t1)
            if enter > leave:
                return False
        return True

    def _segment_clear(self, a, b, rects):
        for rect in rects:
            # A rover can occasionally start within the *additional* safety
            # margin.  Let it leave that convex region instead of trapping it.
            if self._inside(a, rect) and not self._inside(b, rect):
                continue
            if self._segment_intersects_rect(a, b, rect):
                return False
        return True

    def _build_rectangles(self, observation, extra):
        radius = float(observation["rover_radius"])
        hard_pad = radius + max(1e-4, radius * 0.015)
        safe_pad = hard_pad + extra
        hard, safe = [], []
        for obstacle in observation["obstacles"]:
            x, y = float(obstacle["x"]), float(obstacle["y"])
            w, h = float(obstacle["width"]), float(obstacle["height"])
            hard.append((x - hard_pad, y - hard_pad,
                         x + w + hard_pad, y + h + hard_pad))
            safe.append((x - safe_pad, y - safe_pad,
                         x + w + safe_pad, y + h + safe_pad))
        return hard, safe

    def _plan_with_clearance(self, start, goal, observation, extra):
        hard, safe = self._build_rectangles(observation, extra)
        width = float(observation["world"]["width"])
        height = float(observation["world"]["height"])
        radius = float(observation["rover_radius"])
        corner_gap = max(0.05, radius * 0.12)
        xmin, xmax = radius + 1e-3, width - radius - 1e-3
        ymin, ymax = radius + 1e-3, height - radius - 1e-3

        nodes = [tuple(start), tuple(goal)]
        for left, bottom, right, top in safe:
            candidates = (
                (left - corner_gap, bottom - corner_gap),
                (left - corner_gap, top + corner_gap),
                (right + corner_gap, bottom - corner_gap),
                (right + corner_gap, top + corner_gap),
            )
            for x, y in candidates:
                point = (self._clip(x, xmin, xmax),
                         self._clip(y, ymin, ymax))
                if not any(self._inside(point, rectangle) for rectangle in hard):
                    if all(self._distance(point, old) > 1e-7 for old in nodes):
                        nodes.append(point)

        count = len(nodes)
        graph = [[] for _ in range(count)]
        for i in range(count):
            for j in range(i + 1, count):
                if self._segment_clear(nodes[i], nodes[j], safe):
                    distance = self._distance(nodes[i], nodes[j])
                    graph[i].append((j, distance))
                    graph[j].append((i, distance))

        distances = [float("inf")] * count
        parent = [-1] * count
        distances[0] = 0.0
        queue = [(0.0, 0)]
        while queue:
            cost, node = heapq.heappop(queue)
            if cost != distances[node]:
                continue
            if node == 1:
                break
            for neighbor, edge_cost in graph[node]:
                new_cost = cost + edge_cost
                if new_cost < distances[neighbor]:
                    distances[neighbor] = new_cost
                    parent[neighbor] = node
                    heapq.heappush(queue, (new_cost, neighbor))
        if not math.isfinite(distances[1]):
            return None, hard, safe

        indices = []
        node = 1
        while node != 0:
            indices.append(node)
            node = parent[node]
            if node < 0:
                return None, hard, safe
        indices.reverse()
        return [nodes[index] for index in indices], hard, safe

    def _replan(self, observation):
        start = tuple(float(v) for v in observation["position"])
        goal = tuple(float(v) for v in observation["goal"]["position"])
        radius = float(observation["rover_radius"])
        preferred = max(self.extra_clearance, max(0.06, radius * 0.20))
        # Narrow passages may require dropping only the optional safety margin.
        attempts = (preferred, max(0.02, radius * 0.06), 0.0)
        for extra in attempts:
            path, hard, safe = self._plan_with_clearance(
                start, goal, observation, extra)
            if path is not None:
                self.path, self.hard_rects, self.safe_rects = path, hard, safe
                self.extra_clearance = extra
                return
        # Degenerate maps still get a bounded fallback. Emergency avoidance
        # below remains active even if no complete visibility path was found.
        self.hard_rects, self.safe_rects = self._build_rectangles(observation, 0.0)
        self.path = [goal]

    def reset(self, observation):
        self.path = []
        self.last_position = tuple(float(v) for v in observation["position"])
        self.last_goal_distance = float(observation["goal"]["distance"])
        self.stalled_steps = 0
        self.extra_clearance = max(0.06, float(observation["rover_radius"]) * 0.20)
        self._replan(observation)

    def _nearest_obstacle_escape(self, position):
        best_distance = float("inf")
        best_away = (0.0, 0.0)
        for left, bottom, right, top in self.hard_rects:
            qx = self._clip(position[0], left, right)
            qy = self._clip(position[1], bottom, top)
            dx, dy = position[0] - qx, position[1] - qy
            distance = math.hypot(dx, dy)
            if distance < 1e-9 and self._inside(position, (left, bottom, right, top)):
                choices = ((position[0] - left, (-1.0, 0.0)),
                           (right - position[0], (1.0, 0.0)),
                           (position[1] - bottom, (0.0, -1.0)),
                           (top - position[1], (0.0, 1.0)))
                _, away = min(choices, key=lambda item: item[0])
            elif distance > 0.0:
                away = (dx / distance, dy / distance)
            else:
                away = (0.0, 0.0)
            if distance < best_distance:
                best_distance, best_away = distance, away
        return best_distance, best_away

    def act(self, observation):
        if observation.get("done", False):
            return (0.0, 0.0)

        position = tuple(float(v) for v in observation["position"])
        velocity = tuple(float(v) for v in observation["velocity"])
        speed = math.hypot(velocity[0], velocity[1])
        goal = tuple(float(v) for v in observation["goal"]["position"])
        goal_distance = float(observation["goal"]["distance"])
        goal_radius = float(observation["goal"]["radius"])
        rover_radius = float(observation["rover_radius"])

        moved = self._distance(position, self.last_position) if self.last_position else 0.0
        progress = ((self.last_goal_distance - goal_distance)
                    if self.last_goal_distance is not None else 0.0)
        if moved < max(1e-4, rover_radius * 0.008) and speed < 0.08 and progress < 1e-4:
            self.stalled_steps += 1
        else:
            self.stalled_steps = max(0, self.stalled_steps - 2)

        if observation.get("last_collision", False):
            self.extra_clearance = max(self.extra_clearance, rover_radius * 0.35)
            self._replan(observation)
        elif not self.path:
            self._replan(observation)

        # Remove passed waypoints and opportunistically smooth the remaining
        # polyline using current line of sight.
        reach = max(rover_radius * 0.35, 0.08) + min(0.35, speed * 0.35)
        while len(self.path) > 1 and self._distance(position, self.path[0]) <= reach:
            self.path.pop(0)
        farthest = 0
        for index in range(len(self.path) - 1, -1, -1):
            if self._segment_clear(position, self.path[index], self.safe_rects):
                farthest = index
                break
        if farthest > 0:
            self.path = self.path[farthest:]
        target = self.path[0] if self.path else goal
        dx, dy = target[0] - position[0], target[1] - position[1]
        target_distance = math.hypot(dx, dy)
        if target_distance > 1e-9:
            direction = (dx / target_distance, dy / target_distance)
        else:
            direction = (0.0, 0.0)

        terrain = observation.get("current_terrain", "normal")
        cruise = {"sticky": 0.80, "slippery": 0.38}.get(terrain, 0.68)
        remaining_steps = max(1, int(observation["max_steps"]) - int(observation["step"]))
        rough_remaining = target_distance
        if len(self.path) > 1:
            rough_remaining += sum(self._distance(self.path[i], self.path[i + 1])
                                   for i in range(len(self.path) - 1))
        required_speed = rough_remaining / remaining_steps
        cruise = max(cruise, min(1.25, required_speed * 1.35))
        if self.stalled_steps > 10:
            cruise = max(cruise, 1.0)

        # Brake before a corner, and even earlier for the final goal.  The
        # square-root profile is deliberately conservative under high momentum.
        corner_speed = 0.10 + math.sqrt(max(0.0, 0.38 * target_distance))
        desired_speed = min(cruise, corner_speed)
        if len(self.path) == 1:
            goal_clearance = max(0.0, goal_distance - goal_radius * 0.78)
            goal_speed = 0.05 + math.sqrt(0.32 * goal_clearance)
            desired_speed = min(desired_speed, goal_speed)
        if goal_distance <= goal_radius:
            desired_speed = 0.0
            direction = (0.0, 0.0)

        desired_velocity = (direction[0] * desired_speed,
                            direction[1] * desired_speed)
        gain = 1.85 if terrain != "slippery" else 1.45
        ax = gain * (desired_velocity[0] - velocity[0]) + 0.10 * direction[0]
        ay = gain * (desired_velocity[1] - velocity[1]) + 0.10 * direction[1]

        # If current momentum predicts contact, prioritize braking and moving
        # away from the nearest obstacle over path tracking.
        lookahead = 1.5 + (1.2 if terrain == "slippery" else 0.0)
        projected = (position[0] + velocity[0] * lookahead,
                     position[1] + velocity[1] * lookahead)
        predicted_contact = any(self._segment_intersects_rect(position, projected, rect)
                                for rect in self.hard_rects)
        obstacle_distance, away = self._nearest_obstacle_escape(position)
        approaching = -(velocity[0] * away[0] + velocity[1] * away[1])
        if predicted_contact and approaching > 0.01:
            ax = -2.4 * velocity[0] + 0.75 * away[0] + 0.35 * direction[0]
            ay = -2.4 * velocity[1] + 0.75 * away[1] + 0.35 * direction[1]
        elif obstacle_distance < max(0.10, rover_radius * 0.30) and approaching > 0.0:
            ax += away[0] * 0.65
            ay += away[1] * 0.65

        if observation.get("last_collision", False):
            ax = away[0] - 2.0 * velocity[0]
            ay = away[1] - 2.0 * velocity[1]

        # Soft world-boundary protection for drift and delayed actions.
        width = float(observation["world"]["width"])
        height = float(observation["world"]["height"])
        boundary_band = rover_radius * 1.35
        if position[0] < boundary_band and velocity[0] < 0.0:
            ax += 0.8
        elif position[0] > width - boundary_band and velocity[0] > 0.0:
            ax -= 0.8
        if position[1] < boundary_band and velocity[1] < 0.0:
            ay += 0.8
        elif position[1] > height - boundary_band and velocity[1] > 0.0:
            ay -= 0.8

        # Mild action smoothing avoids exciting delayed/slippery dynamics, but
        # collision and predicted-contact responses remain immediate.
        if not observation.get("last_collision", False) and not predicted_contact:
            previous = observation.get("previous_action", (0.0, 0.0))
            blend = 0.76 if terrain != "slippery" else 0.64
            ax = blend * ax + (1.0 - blend) * float(previous[0])
            ay = blend * ay + (1.0 - blend) * float(previous[1])

        self.last_position = position
        self.last_goal_distance = goal_distance
        if not (math.isfinite(ax) and math.isfinite(ay)):
            return (0.0, 0.0)
        return (self._clip(ax), self._clip(ay))
