---
scope: glob
globs: ["prereg/agent.py"]
checks:
  - forbid: 'while\s+True'
    message: agent loops use a bounded range from config
  - run: uv run pytest -q tests/test_agent.py tests/test_verifier.py
---
Every agent loop has an iteration cap from `prereg/config.py` and a deterministic stop. Numbers shown to users
come from the trusted recomputation, never from the model's own claim.
