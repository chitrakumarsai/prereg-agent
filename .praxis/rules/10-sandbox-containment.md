---
scope: glob
globs: ["prereg/runner.py"]
checks:
  - forbid: '"--network", "(host|bridge)"'
    message: the sandbox never gets a network
  - forbid: '"(-e|--env|--env-file)"'
    message: no variables are passed into the sandbox; it starts under env -i
  - forbid: '"--privileged"|"--cap-add"'
    message: the sandbox keeps every capability dropped
  - run: uv run pytest -q tests/test_runner.py
---
Every sandbox is built by `build_command` alone and keeps all of its controls: gVisor runtime, no network,
an empty environment, memory/CPU/process caps, a read-only root, read-only data and code, and destruction
after the step. Files the sandbox writes are untrusted: open them with O_NOFOLLOW and O_NONBLOCK, require a
regular file, and cap the size.
