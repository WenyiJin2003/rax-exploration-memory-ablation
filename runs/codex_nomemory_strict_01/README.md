# codex_nomemory_strict_01

- Condition: exploration without persistent memory
- Exploration episodes: 12/12
- Persistent memory: no
- Model: `gpt-5.6-sol`
- Held-out result: 24/24 success, 0 total contacts, 124.2 mean steps among successes

Only the final `controller.py` was retained. The controller uses map-aware path planning, terrain-sensitive speed limits, velocity feedback, and collision recovery.

