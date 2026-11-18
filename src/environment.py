from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import random
from typing import Iterable


@dataclass(frozen=True)
class Rectangle:
    x: float
    y: float
    width: float
    height: float

    def expanded_contains(self, px: float, py: float, margin: float) -> bool:
        return (
            self.x - margin <= px <= self.x + self.width + margin
            and self.y - margin <= py <= self.y + self.height + margin
        )


@dataclass(frozen=True)
class TerrainZone:
    name: str
    rectangle: Rectangle


@dataclass(frozen=True)
class PhysicsProfile:
    name: str
    action_gain: float
    drag: float
    drift_x: float
    drift_y: float
    action_delay: int


@dataclass(frozen=True)
class EpisodeSpec:
    seed: int
    width: float
    height: float
    start: tuple[float, float]
    goal: tuple[float, float]
    obstacles: tuple[Rectangle, ...]
    terrains: tuple[TerrainZone, ...]
    physics: PhysicsProfile
    max_steps: int = 240
    rover_radius: float = 1.5
    goal_radius: float = 4.5


PHYSICS_PROFILES = (
    PhysicsProfile("responsive", 0.68, 0.56, 0.00, 0.00, 0),
    PhysicsProfile("sluggish", 0.43, 0.66, 0.00, 0.00, 0),
    PhysicsProfile("high_momentum", 0.57, 0.87, 0.00, 0.00, 1),
    PhysicsProfile("biased", 0.55, 0.73, 0.025, -0.018, 0),
)


def _jitter(rng: random.Random, amount: float) -> float:
    return rng.uniform(-amount, amount)


def build_episode(seed: int) -> EpisodeSpec:
    rng = random.Random(seed)
    width, height = 100.0, 70.0
    layout = seed % 4

    if layout == 0:
        start = (8.0, 10.0 + _jitter(rng, 2.0))
        goal = (92.0, 60.0 + _jitter(rng, 2.0))
        obstacles = (
            Rectangle(28.0, 0.0, 7.0, 45.0),
            Rectangle(61.0, 25.0, 7.0, 45.0),
        )
        terrains = (
            TerrainZone("sticky", Rectangle(35.0, 44.0, 25.0, 18.0)),
            TerrainZone("slippery", Rectangle(68.0, 4.0, 24.0, 25.0)),
        )
    elif layout == 1:
        start = (8.0, 58.0 + _jitter(rng, 2.0))
        goal = (92.0, 12.0 + _jitter(rng, 2.0))
        obstacles = (
            Rectangle(20.0, 18.0, 52.0, 7.0),
            Rectangle(32.0, 43.0, 48.0, 7.0),
        )
        terrains = (
            TerrainZone("slippery", Rectangle(7.0, 27.0, 28.0, 16.0)),
            TerrainZone("sticky", Rectangle(72.0, 24.0, 21.0, 19.0)),
        )
    elif layout == 2:
        start = (9.0, 35.0 + _jitter(rng, 3.0))
        goal = (91.0, 35.0 + _jitter(rng, 3.0))
        obstacles = (
            Rectangle(29.0, 12.0, 13.0, 46.0),
            Rectangle(58.0, 0.0, 13.0, 39.0),
        )
        terrains = (
            TerrainZone("sticky", Rectangle(42.0, 8.0, 16.0, 24.0)),
            TerrainZone("slippery", Rectangle(42.0, 40.0, 16.0, 24.0)),
        )
    else:
        start = (10.0, 10.0 + _jitter(rng, 2.0))
        goal = (90.0, 58.0 + _jitter(rng, 2.0))
        obstacles = (
            Rectangle(22.0, 25.0, 23.0, 8.0),
            Rectangle(55.0, 38.0, 24.0, 8.0),
            Rectangle(44.0, 8.0, 8.0, 21.0),
        )
        terrains = (
            TerrainZone("slippery", Rectangle(5.0, 39.0, 30.0, 24.0)),
            TerrainZone("sticky", Rectangle(66.0, 8.0, 27.0, 25.0)),
        )

    profile = PHYSICS_PROFILES[(seed * 7 + 3) % len(PHYSICS_PROFILES)]
    return EpisodeSpec(
        seed=seed,
        width=width,
        height=height,
        start=start,
        goal=goal,
        obstacles=obstacles,
        terrains=terrains,
        physics=profile,
    )


class HiddenPhysicsEnv:
    def __init__(self, spec: EpisodeSpec):
        self.spec = spec
        self.x, self.y = spec.start
        self.vx = 0.0
        self.vy = 0.0
        self.step_count = 0
        self.collisions = 0
        self.done = False
        self.success = False
        self.last_collision = False
        self.previous_action = (0.0, 0.0)
        self.action_queue = [(0.0, 0.0)] * spec.physics.action_delay
        self.trace = [(self.x, self.y)]

    @classmethod
    def from_seed(cls, seed: int) -> "HiddenPhysicsEnv":
        return cls(build_episode(seed))

    def current_terrain(self) -> str:
        for zone in self.spec.terrains:
            if zone.rectangle.expanded_contains(self.x, self.y, 0.0):
                return zone.name
        return "normal"

    def observation(self) -> dict:
        distance = math.hypot(self.spec.goal[0] - self.x, self.spec.goal[1] - self.y)
        return {
            "position": [round(self.x, 4), round(self.y, 4)],
            "velocity": [round(self.vx, 4), round(self.vy, 4)],
            "speed": round(math.hypot(self.vx, self.vy), 4),
            "goal": {
                "position": [self.spec.goal[0], self.spec.goal[1]],
                "radius": self.spec.goal_radius,
                "distance": round(distance, 4),
            },
            "world": {"width": self.spec.width, "height": self.spec.height},
            "rover_radius": self.spec.rover_radius,
            "obstacles": [asdict(rect) for rect in self.spec.obstacles],
            "terrain_zones": [
                {"name": zone.name, **asdict(zone.rectangle)} for zone in self.spec.terrains
            ],
            "current_terrain": self.current_terrain(),
            "previous_action": [self.previous_action[0], self.previous_action[1]],
            "last_collision": self.last_collision,
            "collisions": self.collisions,
            "step": self.step_count,
            "max_steps": self.spec.max_steps,
            "done": self.done,
            "success": self.success,
        }

    def _collides(self, x: float, y: float) -> bool:
        radius = self.spec.rover_radius
        if x < radius or x > self.spec.width - radius:
            return True
        if y < radius or y > self.spec.height - radius:
            return True
        return any(rect.expanded_contains(x, y, radius) for rect in self.spec.obstacles)

    def step(self, action: tuple[float, float] | list[float]) -> tuple[dict, float, bool, dict]:
        if self.done:
            raise RuntimeError("Episode is already finished; reset before stepping again.")

        ax = max(-1.0, min(1.0, float(action[0])))
        ay = max(-1.0, min(1.0, float(action[1])))
        self.previous_action = (ax, ay)
        self.action_queue.append((ax, ay))
        applied_ax, applied_ay = self.action_queue.pop(0)

        terrain = self.current_terrain()
        profile = self.spec.physics
        gain = profile.action_gain
        drag = profile.drag
        if terrain == "sticky":
            gain *= 0.56
            drag = min(drag, 0.48)
        elif terrain == "slippery":
            gain *= 1.06
            drag = max(drag, 0.94)

        self.vx = drag * self.vx + gain * applied_ax + profile.drift_x
        self.vy = drag * self.vy + gain * applied_ay + profile.drift_y
        speed = math.hypot(self.vx, self.vy)
        max_speed = 3.6
        if speed > max_speed:
            scale = max_speed / speed
            self.vx *= scale
            self.vy *= scale

        proposed_x = self.x + self.vx
        proposed_y = self.y + self.vy
        self.last_collision = self._collides(proposed_x, proposed_y)
        if self.last_collision:
            self.collisions += 1
            self.vx *= -0.12
            self.vy *= -0.12
        else:
            self.x = proposed_x
            self.y = proposed_y

        self.step_count += 1
        self.trace.append((self.x, self.y))
        distance = math.hypot(self.spec.goal[0] - self.x, self.spec.goal[1] - self.y)
        self.success = distance <= self.spec.goal_radius
        self.done = self.success or self.step_count >= self.spec.max_steps

        reward = -0.05 - 0.35 * float(self.last_collision)
        if self.success:
            reward += 10.0
        info = {
            "applied_action": [applied_ax, applied_ay],
            "terrain": terrain,
            "success": self.success,
        }
        return self.observation(), reward, self.done, info

    def score(self) -> float:
        return (
            100.0 * float(self.success)
            - 0.15 * self.step_count
            - 3.0 * self.collisions
        )

    def export_state(self) -> dict:
        return {
            "spec": {
                "seed": self.spec.seed,
                "width": self.spec.width,
                "height": self.spec.height,
                "start": list(self.spec.start),
                "goal": list(self.spec.goal),
                "obstacles": [asdict(rect) for rect in self.spec.obstacles],
                "terrains": [
                    {"name": zone.name, "rectangle": asdict(zone.rectangle)}
                    for zone in self.spec.terrains
                ],
                "physics": asdict(self.spec.physics),
                "max_steps": self.spec.max_steps,
                "rover_radius": self.spec.rover_radius,
                "goal_radius": self.spec.goal_radius,
            },
            "dynamic": {
                "x": self.x,
                "y": self.y,
                "vx": self.vx,
                "vy": self.vy,
                "step_count": self.step_count,
                "collisions": self.collisions,
                "done": self.done,
                "success": self.success,
                "last_collision": self.last_collision,
                "previous_action": list(self.previous_action),
                "action_queue": [list(action) for action in self.action_queue],
                "trace": [list(point) for point in self.trace],
            },
        }

    @classmethod
    def import_state(cls, payload: dict) -> "HiddenPhysicsEnv":
        raw_spec = payload["spec"]
        spec = EpisodeSpec(
            seed=int(raw_spec["seed"]),
            width=float(raw_spec["width"]),
            height=float(raw_spec["height"]),
            start=tuple(raw_spec["start"]),
            goal=tuple(raw_spec["goal"]),
            obstacles=tuple(Rectangle(**item) for item in raw_spec["obstacles"]),
            terrains=tuple(
                TerrainZone(item["name"], Rectangle(**item["rectangle"]))
                for item in raw_spec["terrains"]
            ),
            physics=PhysicsProfile(**raw_spec["physics"]),
            max_steps=int(raw_spec["max_steps"]),
            rover_radius=float(raw_spec["rover_radius"]),
            goal_radius=float(raw_spec["goal_radius"]),
        )
        env = cls(spec)
        dynamic = payload["dynamic"]
        env.x = float(dynamic["x"])
        env.y = float(dynamic["y"])
        env.vx = float(dynamic["vx"])
        env.vy = float(dynamic["vy"])
        env.step_count = int(dynamic["step_count"])
        env.collisions = int(dynamic["collisions"])
        env.done = bool(dynamic["done"])
        env.success = bool(dynamic["success"])
        env.last_collision = bool(dynamic["last_collision"])
        env.previous_action = tuple(dynamic["previous_action"])
        env.action_queue = [tuple(action) for action in dynamic["action_queue"]]
        env.trace = [tuple(point) for point in dynamic["trace"]]
        return env


def save_state(env: HiddenPhysicsEnv, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(env.export_state(), handle, indent=2)


def load_state(path: str) -> HiddenPhysicsEnv:
    with open(path, "r", encoding="utf-8") as handle:
        return HiddenPhysicsEnv.import_state(json.load(handle))


def run_actions(env: HiddenPhysicsEnv, actions: Iterable[tuple[float, float]]) -> dict:
    for action in actions:
        if env.done:
            break
        env.step(action)
    return env.observation()

