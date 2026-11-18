"""Robust feedback controller for the hidden-physics rover task.

The geometric planner treats obstacles as inflated rectangles (configuration
space for the circular rover).  A small visibility graph supplies a safe path;
the tracker asks for a modest velocity and closes the loop using the measured
velocity, which makes it insensitive to the episode's acceleration and drag.
"""

from __future__ import annotations

import heapq
import math


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


class Controller:
    def reset(self, observation):
        self.goal = tuple(observation["goal"]["position"])
        self.goal_radius = float(observation["goal"]["radius"])
        self.width = float(observation["world"]["width"])
        self.height = float(observation["world"]["height"])
        self.radius = float(observation["rover_radius"])
        self.obstacles = list(observation["obstacles"])
        self.last_action = (0.0, 0.0)
        self.collision_cooldown = 0

    def _rectangles(self):
        # Clearance is deliberately generous: delayed braking can otherwise
        # clip a corner even when the rover's centre follows a valid segment.
        pad = self.radius + 2.2
        out = []
        for o in self.obstacles:
            out.append((o["x"] - pad, o["y"] - pad,
                        o["x"] + o["width"] + pad,
                        o["y"] + o["height"] + pad))
        return out

    @staticmethod
    def _segment_hits_rect(a, b, rect):
        """Liang-Barsky test against the *open* rectangle interior."""
        x0, y0 = a
        dx, dy = b[0] - x0, b[1] - y0
        xmin, ymin, xmax, ymax = rect
        # Shrinking by epsilon permits graph edges that run on a padded side.
        eps = 1e-7
        xmin += eps; ymin += eps; xmax -= eps; ymax -= eps
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, x0 - xmin), (dx, xmax - x0),
                     (-dy, y0 - ymin), (dy, ymax - y0)):
            if abs(p) < 1e-12:
                if q < 0.0:
                    return False
            else:
                r = q / p
                if p < 0.0:
                    if r > t1: return False
                    if r > t0: t0 = r
                else:
                    if r < t0: return False
                    if r < t1: t1 = r
        return t0 <= t1 and t1 >= 0.0 and t0 <= 1.0

    def _visible(self, a, b, rects):
        return not any(self._segment_hits_rect(a, b, r) for r in rects)

    def _plan(self, start):
        rects = self._rectangles()
        nodes = [start, self.goal]
        for xmin, ymin, xmax, ymax in rects:
            for p in ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax)):
                # A corner outside the usable world cannot be a waypoint.
                if self.radius <= p[0] <= self.width - self.radius and \
                   self.radius <= p[1] <= self.height - self.radius:
                    nodes.append(p)

        n = len(nodes)
        graph = [[] for _ in nodes]
        for i in range(n):
            for j in range(i + 1, n):
                if self._visible(nodes[i], nodes[j], rects):
                    w = _dist(nodes[i], nodes[j])
                    graph[i].append((j, w))
                    graph[j].append((i, w))

        best = [float("inf")] * n
        parent = [-1] * n
        best[0] = 0.0
        heap = [(0.0, 0)]
        while heap:
            cost, i = heapq.heappop(heap)
            if cost != best[i]:
                continue
            if i == 1:
                break
            for j, w in graph[i]:
                nc = cost + w
                if nc < best[j]:
                    best[j], parent[j] = nc, i
                    heapq.heappush(heap, (nc, j))
        if not math.isfinite(best[1]):
            return [self.goal]
        path = []
        cur = 1
        while cur != 0 and cur >= 0:
            path.append(nodes[cur])
            cur = parent[cur]
        path.reverse()
        return path or [self.goal]

    def act(self, observation):
        p = tuple(observation["position"])
        vx, vy = map(float, observation["velocity"])
        terrain = observation["current_terrain"]
        goal_d = _dist(p, self.goal)
        path = self._plan(p)
        target = path[0]
        dx, dy = target[0] - p[0], target[1] - p[1]
        d = math.hypot(dx, dy)
        if d < 1e-9:
            ux = uy = 0.0
        else:
            ux, uy = dx / d, dy / d

        # Cruise slowly enough that a delayed command cannot jump the 2.2-unit
        # planning margin.  Corners and the goal get a long braking approach.
        cruise = {"normal": 1.25, "sticky": 1.15, "slippery": 0.78}.get(terrain, 1.0)
        if len(path) > 1:
            desired_speed = min(cruise, 0.32 + 0.20 * d)
        else:
            # Aim to arrive nearly stopped, while still overcoming drift/drag.
            desired_speed = min(cruise, 0.18 + 0.22 * max(0.0, goal_d - 0.7 * self.goal_radius))
        if goal_d < 0.72 * self.goal_radius:
            desired_speed = 0.0

        dvx, dvy = desired_speed * ux - vx, desired_speed * uy - vy
        gain = 1.05 if terrain != "slippery" else 0.78
        ax, ay = gain * dvx, gain * dvy

        # A collision normally means delayed momentum carried us into a face.
        # Brake hard briefly; replanning on every call then chooses open space.
        if observation.get("last_collision"):
            self.collision_cooldown = 3
        if self.collision_cooldown > 0:
            ax, ay = -1.4 * vx + 0.25 * ux, -1.4 * vy + 0.25 * uy
            self.collision_cooldown -= 1

        # Mild action smoothing avoids delay-driven oscillation, except where
        # braking demands an immediate reversal.
        raw = (_clip(ax), _clip(ay))
        if vx * dvx + vy * dvy < -0.15:
            action = raw
        else:
            action = (_clip(0.78 * raw[0] + 0.22 * self.last_action[0]),
                      _clip(0.78 * raw[1] + 0.22 * self.last_action[1]))
        self.last_action = action
        return action
