# codex_zero_01

- Condition: zero-shot
- Exploration episodes: 0
- Persistent memory: no
- Model: `gpt-5.6-sol`
- Held-out result: 23/24 success, 100 total contacts, 191.3 mean steps among successes

The controller was written from the task and public interface without any environment interaction. On held-out seed 222, it chose a plausible route but repeatedly corrected too late near an obstacle.

