# Task: deliver a fragile sample across unknown terrain

You control a rover in a 2-D environment. Reach the circular goal without colliding with obstacles. The world contains normal, sticky, and slippery regions. Hidden physical properties—including control strength, momentum, drift, and possible action delay—change between episodes.

You may explore only through `agent_api.py`. Use the exploration episodes to learn robust control principles. Store useful observations in `workspace/memory.md` and reusable procedures in `workspace/skills.md`.

Your final output is `controller.py`, containing:

```python
class Controller:
    def reset(self, observation):
        ...

    def act(self, observation):
        # Return either (ax, ay) or {"ax": ax, "ay": ay}.
        ...
```

Both action components must be between -1 and 1. During evaluation, your controller runs without a language model on unseen maps and physics settings.

Success is more important than speed. Collisions are penalized. A good controller should plan around obstacles, slow down before turns and goals, and use observed velocity feedback rather than assuming fixed dynamics.

