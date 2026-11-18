# Memory

Record empirical observations here. Separate measured behavior from hypotheses.

## Measured

- Seed 101 starts at `(8, 58.3246)` with a goal near `(92, 10.7790)` and two
  horizontal rectangular barriers. Normal-terrain response to repeated `(1,0)`:
  step 1 applied `(0,0)`, then x velocities `0.57, 1.0659, 1.4973, 1.8727`.
- Seed 101 has a one-step action delay. After switching from `+1` to `-1`, the
  old `+1` was applied once more; velocities then changed from `2.1992` through
  `1.3433, 0.5987, -0.0491`. Momentum therefore requires anticipatory braking.
- No collision occurred in these probes.
- Controller trials on fresh seeds 102--108 all succeeded with zero collisions.
  Completion steps were respectively `153, 139, 193, 122, 148, 142, 197`.
  Thus the slowest observed case retained 43 of 240 steps.
- Public maps include horizontal alternating barriers, tall offset vertical
  walls, and staggered mixed rectangles. The inflated-corner visibility planner
  found valid routes for each observed family.
- Final untouched public batch (109--112) also achieved 4/4 success and zero
  collisions, in `120, 148, 140, 194` steps. Across all 12 exploration seeds,
  the delivered controller therefore achieved 100% success with no collisions.

## Hypotheses

- Dynamics resemble damped acceleration with episode-dependent acceleration,
  drag, drift, and delay. Closed-loop desired-velocity tracking should transfer
  better than fixed action sequences.
- Inflating obstacles by rover radius plus a momentum margin, routing through
  visibility-graph corners, and limiting speed near corners should prevent most
  delayed corner clips.
- The zero-collision record across eight physics/map combinations supports
  retaining the 2.2-unit dynamic margin and conservative terrain speeds rather
  than optimizing public-seed completion time.

