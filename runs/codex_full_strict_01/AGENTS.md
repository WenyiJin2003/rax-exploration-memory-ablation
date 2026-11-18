# Coding-agent experiment rules

Your goal is to solve the task in `TASK.md` and leave a final `controller.py`.

## Condition: full_memory


- You may use up to 12 exploration episodes through `agent_api.py`.
- Maintain `workspace/memory.md`, `workspace/skills.md`, and `workspace/run_log.md`.
- Use the workspace to preserve empirical findings and reusable control ideas.


## Shared restrictions

- Treat `src/environment.pyc` as a black box. Do not inspect, disassemble, or reverse engineer it.
- Do not access parent directories, reference controllers, held-out seeds, the internet, or external tools.
- Do not install packages. Use the Python standard library.
- `run_budget.json` is an automatic audit record. You may read it but must not edit it.
- You may run `python3 explore_evaluate.py` on the public exploration seeds.
- Actions must stay in [-1, 1]. Do not hard-code seed-specific trajectories.
- Finish by checking that `controller.py` imports and runs.
