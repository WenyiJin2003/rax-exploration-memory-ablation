# Run summary

Generated from the immutable records in `runs/`.

| Run | Condition | Exploration | Success | Total contacts | Mean steps, successes | Mean score |
|---|---|---:|---:|---:|---:|---:|
| `codex_zero_01` | Zero-shot | 0 | 23 / 24 | 100 | 191.3 | 54.33 |
| `codex_nomemory_strict_01` | Exploration, no memory | 12 | 24 / 24 | 0 | 124.2 | 81.38 |
| `codex_full_strict_01` | Exploration + memory | 12 | 24 / 24 | 0 | 151.8 | 77.23 |

## Interpretation

Both explored controllers completed every held-out episode without contact. The zero-shot controller failed once and accumulated 100 contacts. In this first replicate, persistent memory did not improve on exploration alone.

## Statistical caution

Each row represents one independently generated controller. Held-out episodes measure robustness across environments, not variance across controller-generation runs. More independent runs are required before estimating the effect of persistent memory.
