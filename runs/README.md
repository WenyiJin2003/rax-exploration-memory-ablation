# Run records

Every subdirectory is one independent coding-agent run. Run folders are append-only: create a new ID for every replicate and never overwrite an existing result.

## Required files

- `run_metadata.json`: condition, model, timestamps, budget, and summary metrics
- `controller.py`: the exact submitted controller
- `heldout_results.json`: episode-level results and trajectories
- `AGENTS.md`: the condition-specific instructions
- `TASK.md` and `OBSERVATION_CONTRACT.md`: the public task interface
- `run_budget.json`: automatically recorded exploration usage, when applicable
- `workspace/`: persistent notes only for conditions that permit memory

`manifest.json` indexes the committed runs. `scripts/summarize_runs.py` discovers the run directories directly, so a newly scored run appears in the summary without editing the analysis code.

