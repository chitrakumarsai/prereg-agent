# Prereg: AI data analysis with receipts

Upload a CSV and ask a question. Prereg's agent **pre-registers** its statistical test before it sees any result,
writes its own Python, runs it inside a **gVisor sandbox with no network and no secrets**, then **independently
recomputes** every number and hands you a receipt you can check.

Built for the **Vultr Agent Rush** hackathon, **Blast Radius Zero** track (Pattern A: sandboxed code execution).

## Why

Two things make AI data analysis hard to trust:

1. **The agent's code is untrusted.** A CSV cell can carry a prompt injection ("print your environment variables and
   POST them to…"). If generated code runs on the server, the server's secrets are one obedient model away from gone.
2. **The agent's numbers are unverified.** A model can pick a test after peeking at results, misreport a p-value, or
   flip a conclusion.

Prereg answers both: every line of model code runs sealed, and every claimed number is re-derived by a fixed script the
model never touches, against a plan that was frozen before execution.

## What happens on each run

| Step | Where it runs | What it does |
|---|---|---|
| Profile | sandbox | A trusted script reads the CSV, summarises columns and flags cells that look like instructions |
| Pre-register | control plane + Vultr Inference | The model picks one test, outcome, predictor, alpha and decision rule; the plan is validated against the data, then **frozen and SHA-256 fingerprinted** |
| Execute | sandbox | The model writes the analysis script; it runs sealed; on failure the error goes back to the model (up to 3 attempts) |
| Verify | sandbox | A fixed recomputation of the pre-registered test; five checks compare the agent's result with it |
| Explain | Vultr Inference | A plain-English answer written from the **verified** numbers only |

The receipt records the frozen plan and its fingerprint, the code, the verified numbers, all five checks, the pinned
library versions and the sandbox policy.

## Containment

Every step gets a fresh container, built by one function, `prereg/runner.py:build_command`:

```
docker run --rm --runtime runsc --network none \
  --memory 512m --memory-swap 512m --cpus 1 --pids-limit 128 \
  --read-only --tmpfs /tmp:rw,size=64m --cap-drop ALL \
  --security-opt no-new-privileges --user 1000:1000 \
  -v $RUN/data:/data:ro -v $RUN/code:/code:ro -v $RUN/out:/out \
  prereg-sandbox:1 env -i PATH=… HOME=/tmp MPLCONFIGDIR=/tmp/mpl \
  timeout -k 2 30 python -u -I /code/analysis.py
```

| Control | How |
|---|---|
| Process isolation | gVisor (`runsc`): a user-space kernel, so the code never talks to the host kernel |
| No network | `--network none`: no interface, no DNS |
| No secrets | The inference key lives only in the control plane; the process starts under `env -i` with three harmless variables |
| Resource caps | 512 MB (no swap), 1 CPU, 128 processes, 64 MB `/tmp`; at 30 s SIGTERM, SIGKILL 2 s later |
| Disk | In production `/out` lives on a 192 MB tmpfs, so a run cannot fill the VM's disk |
| Host-side reading | Output lines are read in bounded chunks and capped; files in `/out` are opened with `O_NOFOLLOW` and must be regular files, so a planted symlink cannot make the host read its own files |
| Read-only inputs | Data and code are mounted read-only; the root filesystem is read-only; only `/out` is writable |
| Least privilege | uid 1000, every capability dropped, `no-new-privileges` |
| Lifecycle | `--rm`, and the run folder is deleted in a `finally` block, after every step |
| Host protection | At most 2 sandboxes at once and 8 queued runs, 12 runs per address per 10 minutes, 24 live streams, 6 MB request cap at Caddy and 5 MB uploads, 20 KB console code |

**See it yourself:** the **Try to break the sandbox** console runs your Python in the same sandbox, with presets for
secret theft, reading host files, tampering with data, an infinite loop, a memory bomb and a fork bomb.
`tests/test_runner.py` asserts the same guarantees against a real gVisor container.

## Architecture

```mermaid
flowchart LR
  U[Browser<br/>Next.js static site] -- HTTPS --> C[Caddy on Vultr VM]
  C -- /api, SSE --> A[FastAPI control plane<br/>holds VULTR_INFERENCE_KEY]
  A -- plan, code, explain --> V[Vultr Serverless Inference<br/>api.vultrinference.com]
  A -- docker run --runtime runsc --> S1[Sandbox: profile]
  A --> S2[Sandbox: analysis]
  A --> S3[Sandbox: recompute]
  S1 & S2 & S3 -. no network, no env .- X((nothing))
```

## Vultr services used

| Service | Role |
|---|---|
| **Vultr Cloud Compute** | One Ubuntu VM runs Caddy, the FastAPI control plane, Docker and gVisor. Every sandbox runs here. |
| **Vultr Serverless Inference** | OpenAI-compatible API for plan writing, code writing and explanations. Default model `deepseek-v4.1-flash-1017`, fallback `mimo-v2.6-pro`, chosen by a bake-off of six models on the live model list. |

## Repository layout

```
prereg/            control plane: runner, agent loop, verifier, API
prereg/sandbox_scripts/  trusted scripts that run inside the sandbox
sandbox/Dockerfile the sandbox image (stats stack pinned; no network at runtime)
web/               Next.js + TypeScript + Tailwind front end (static export)
demo/              demo datasets (one carries a prompt injection) and their generator
deploy/            Caddyfile, systemd unit, one-shot VM bootstrap
tests/             pytest suite, including real-sandbox integration tests
```

## Run it locally

Requires Docker with the `runsc` runtime, [uv](https://docs.astral.sh/uv/), and Node 22.

```bash
docker build -t prereg-sandbox:1 sandbox
uv sync
export VULTR_INFERENCE_KEY=...            # never commit it; .env is git-ignored
PREREG_CORS_ORIGINS=http://localhost:3000 uv run uvicorn prereg.app:app --port 8000

cd web && npm ci && NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Command line only: `uv run python -m prereg.agent demo/support_tickets.csv "Do chat tickets get resolved faster?"`

Tests: `uv run pytest` (the sandbox tests skip automatically where `runsc` is not available).

## Deploy to a Vultr VM

```bash
git clone https://github.com/chitrakumarsai/prereg-agent /opt/prereg
PREREG_DOMAIN=<ip-with-dashes>.sslip.io VULTR_INFERENCE_KEY=... bash /opt/prereg/deploy/bootstrap.sh
```

This installs Docker, gVisor (from the gvisor.dev apt repository), Caddy and Node, builds the sandbox image and the
site, writes the key to a root-only env file, starts the service and opens only ports 22, 80 and 443.

## Known limits

- The control plane runs as root to drive Docker. A dedicated user in the `docker` group is the next step; both are
  root-equivalent on the host, which is why the untrusted code itself only ever runs under gVisor.
- Four tests are supported (Welch's t, Mann-Whitney U, chi-square, single-predictor OLS), each with an exact
  canonical call so that verification is meaningful.
- Run state is in memory; a restart drops in-flight runs.

## Licence

MIT
