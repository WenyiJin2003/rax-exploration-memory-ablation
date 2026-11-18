# Skills

Record reusable control procedures here.

## Robust navigation procedure

1. Convert each obstacle to configuration space by expanding it by the rover
   radius plus an additional dynamic margin.
2. Build a visibility graph from current position, goal, and expanded rectangle
   corners; use shortest-path search to select the next safe corner.
3. Track a modest desired velocity rather than commanding position directly.
   Compute action from measured velocity error so unknown strength and drag are
   corrected online.
4. Reduce desired speed on slippery terrain and as a corner or goal approaches.
5. On collision, brake against measured velocity for several feedback steps and
   replan from the new position.

## Validation procedure

Use fresh episodes individually while tuning so failures remain attributable.
Reserve an untouched batch for the official evaluator, then verify import,
reset/act behavior, finite bounded actions, and the automatic budget record.

