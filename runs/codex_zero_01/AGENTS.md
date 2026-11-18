# Coding-agent experiment rules

Your goal is to solve the task in `TASK.md` and leave a final `controller.py`.

## Condition: zero_shot


- Do not call `agent_api.py` and do not inspect exploration trajectories.
- Write `controller.py` directly from `TASK.md` and the public observation/action contract.
- This is the zero-shot condition.


## Shared restrictions

- Treat `src/environment.pyc` as a black box. Do not inspect, disassemble, or reverse engineer it.
- Do not access parent directories, reference controllers, held-out seeds, the internet, or external tools.
- Do not install packages. Use the Python standard library.
- Do not run `explore_evaluate.py`; evaluation feedback is unavailable in this condition.
- Actions must stay in [-1, 1]. Do not hard-code seed-specific trajectories.
- Finish by checking that `controller.py` imports and runs.
