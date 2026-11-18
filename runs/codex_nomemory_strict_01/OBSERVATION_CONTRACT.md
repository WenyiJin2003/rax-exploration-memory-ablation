# Public controller interface

The evaluator constructs `Controller`, calls `reset(observation)` once, then repeatedly calls `act(observation)` until the episode ends.

The observation is a dictionary with this public structure:

```text
position: [x, y]
velocity: [vx, vy]
speed: float
goal:
  position: [x, y]
  radius: float
  distance: float
world:
  width: float
  height: float
rover_radius: float
obstacles: list of {x, y, width, height}
terrain_zones: list of {name, x, y, width, height}
current_terrain: "normal", "sticky", or "slippery"
previous_action: [ax, ay]
last_collision: bool
collisions: int
step: int
max_steps: int
done: bool
success: bool
```

Coordinates use a standard Cartesian frame. Obstacle and terrain rectangles are axis-aligned and begin at their lower-left `(x, y)` coordinate.

`act` must return `(ax, ay)` or `{"ax": ax, "ay": ay}`, with each component in `[-1, 1]`.

