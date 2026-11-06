# Runbook: running Prereg and common tasks

## What you need

| Tool | Version | Why |
|---|---|---|
| Docker with the `runsc` (gVisor) runtime | Docker 29+, gVisor 2026 releases | every sandbox |
| [uv](https://docs.astral.sh/uv/) | any recent | Python 3.12 and dependencies |
| Node.js | 22 | the web front end |
| A Vultr Serverless Inference key | | `VULTR_INFERENCE_KEY` |

Secrets go in `.env` at the repo root (git-ignored): `VULTR_INFERENCE_KEY=...`. Never commit it.

## Run it locally

**1. Build the sandbox image (once, and after changing `sandbox/Dockerfile`):**

```bash
docker build -t prereg-sandbox:1 sandbox
```

**2. Install Python dependencies:**

```bash
uv sync
```

**3. Start the API** (terminal 1):

```bash
export VULTR_INFERENCE_KEY=$(sed -n 's/^VULTR_INFERENCE_KEY=//p' .env)
PREREG_CORS_ORIGINS=http://localhost:3000 uv run uvicorn prereg.app:app --port 8000
```

Check it: `curl localhost:8000/api/health` should return `"ok":true` and `"runtime":"runsc"`.

**4. Start the website** (terminal 2):

```bash
cd web
npm ci
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Open http://localhost:3000.

**Command line only** (no web UI):

```bash
uv run python -m prereg.agent demo/support_tickets.csv "Do chat tickets get resolved faster than email tickets?"
```

> Don't `source .env` in zsh: if it ever holds a `USERNAME=` line, zsh treats that as a request to switch user.
> Read single values with `sed` as above.

## Check your work

| Command | What it proves |
|---|---|
| `uv run pytest -q` | 70 tests; the sandbox ones run against real gVisor and skip where `runsc` is missing |
| `uv run praxis verify` | the containment, secrets and agent-loop rules in `.praxis/rules/` |
| `cd web && npx tsc --noEmit && npm run lint` | front-end types and lint |
| `cd web && npm run build` | the static site builds into `web/out/` |

## Common tasks

### Try the sample data

The site's three dataset cards are `demo/*.csv`. For the upload path, use
`demo/upload_samples/email_subject_test.csv` and ask *"Does the subject line affect whether people click?"*
(a chi-square test). Regenerate the demo CSVs with `uv run python demo/make_datasets.py`.

### Add a demo dataset

1. Put the CSV in `demo/` as `<id>.csv`.
2. Add an entry to `demo/datasets.json` (`id`, `title`, `domain`, `rows`, `question`, `blurb`, optional `hostile`).
3. Add the same entry to `web/src/components/workspace/demo-datasets.ts` (shown before the API answers).

### Change the model

Set `PREREG_MODEL` and/or `PREREG_FALLBACK_MODEL` in the environment (defaults in `prereg/config.py`). List the
available models:

```bash
curl -s https://api.vultrinference.com/v1/models -H "Authorization: Bearer $VULTR_INFERENCE_KEY" | python3 -m json.tool
```

### Change a sandbox limit

All limits live in `prereg/config.py` (timeout, memory, CPUs, processes, scratch size, per-address caps). Every
sandbox is built by `build_command` in `prereg/runner.py`; don't add flags anywhere else. After a change, run
`uv run pytest -q tests/test_runner.py` and `uv run praxis verify`, and update the README's *Containment* table.

### Add an attack preset

Add an entry to `ATTACK_PRESETS` in `web/src/lib/presets.ts`: the code, what it threatens, what containment should
do, and a `containedWhen(status, log)` check that matches what gVisor really does. Run it in the console to confirm
it shows *Contained.*

## Deploy

Production is one Ubuntu 24.04+ VM (currently 64.177.53.95) behind Caddy at https://64-177-53-95.sslip.io.

**First deploy on a fresh VM** (as root):

```bash
git clone https://github.com/chitrakumarsai/prereg-agent /opt/prereg
cd /opt/prereg
read -rs VULTR_INFERENCE_KEY && export VULTR_INFERENCE_KEY   # paste the key; it isn't echoed or saved in history
PREREG_DOMAIN=64-177-53-95.sslip.io bash deploy/bootstrap.sh
```

The script installs Docker, gVisor, Caddy, uv and Node; builds the sandbox image and the site; writes the key to
`/etc/prereg.env` (mode 600); mounts the run tmpfs; starts `prereg` and `caddy`; and opens only ports 22, 80, 443.

**Redeploy after pushing to GitHub:**

```bash
ssh -i ~/.ssh/vultr_ed25519 root@64.177.53.95
cd /opt/prereg && git pull
read -rs VULTR_INFERENCE_KEY && export VULTR_INFERENCE_KEY
PREREG_DOMAIN=64-177-53-95.sslip.io bash deploy/bootstrap.sh
```

Only Python changes (no front-end or deploy changes)? `git pull && systemctl restart prereg` is enough.

## Operate the VM

| Task | Command |
|---|---|
| Service status | `systemctl status prereg caddy docker` |
| Live API logs | `journalctl -u prereg -f` |
| Caddy logs | `journalctl -u caddy -f` |
| Restart the API | `systemctl restart prereg` |
| Health from anywhere | `curl https://64-177-53-95.sslip.io/api/health` |
| Prove gVisor is used | `docker run --rm --runtime=runsc --network none alpine uname -r` (shows `4.19.0-gvisor`) |
| Run the tests on the VM | `cd /opt/prereg && PREREG_SCRATCH_TMPFS=1 PREREG_RUNS_DIR=/var/lib/prereg/test-runs uv run --frozen pytest -q; rm -rf /var/lib/prereg/test-runs` |
| Rotate the inference key | edit `/etc/prereg.env` (keep mode 600), then `systemctl restart prereg` |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/api/health` shows `"docker": false` or runs fail at once | Docker or `runsc` missing | `docker info --format '{{json .Runtimes}}'` must list `runsc`; re-run `runsc install && systemctl restart docker` |
| "You already have runs in progress" | 2 unfinished runs from your address | wait for one to finish |
| "Too many runs from your address" | 12 runs in 10 minutes | wait a few minutes |
| "The sandbox queue is full" | 8 runs in progress site-wide | retry in a minute |
| Receipt never arrives, log shows retries | the model's code kept failing | try again; check `journalctl -u prereg` for the inference error |
| Plan rejected | the question doesn't fit one of the four tests, or a column has a single value | rephrase, naming the outcome and the grouping column |
| macOS: `operation not permitted` on `~/.docker` or `~/.cache` | the session can't write there | point `DOCKER_CONFIG` and `UV_CACHE_DIR` at a writable folder |
