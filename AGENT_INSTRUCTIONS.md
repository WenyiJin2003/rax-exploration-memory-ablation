# Experimental rules for the coding agent

## Allowed

- Read `TASK.md` and this file.
- Use `python3 agent_api.py ...` to interact with exploration worlds.
- Read and update files inside `workspace/`.
- Create and edit `controller.py`.
- Run `python3 evaluate.py controller.py --split explore` while developing.

## Not allowed during the agent run

- Do not read `src/environment.py`, `evaluate.py`, the reference controllers, tests, or held-out result files.
- Do not use held-out seeds or edit the evaluator.
- Do not install packages or access the internet.
- Do not hard-code a list of exploration trajectories or seed-specific answers.

## Budget

- At most 12 exploration episodes.
- At most 240 control steps per episode.
- Exploration seeds are 101 through 112.

## Submission

Leave these files when finished:

- `controller.py`
- `workspace/memory.md`
- `workspace/skills.md`
- `workspace/run_log.md`, with each explored seed and the purpose of the run

The evaluator imports only `controller.py`. It does not execute arbitrary setup scripts.

