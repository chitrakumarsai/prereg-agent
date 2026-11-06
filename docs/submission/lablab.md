# Lablab submission: Prereg

**Event:** Vultr Agent Rush · **Track:** Blast Radius Zero (Pattern A: sandboxed code execution)

| Field | Value |
|---|---|
| Project title | Prereg: AI data analysis with receipts |
| Demo URL | https://64-177-53-95.sslip.io |
| Repository | https://github.com/chitrakumarsai/prereg-agent |
| Cover image | `docs/submission/cover.png` (1600×900 at 1.5×) |
| Video | see `demo-script.md` (record, upload, paste link) |
| Slides | see the slide deck link in the final report |

## Short description (one line)

An AI data analyst that commits to its statistical test before seeing results, runs its own code in a gVisor
sandbox with no network or secrets, and independently re-checks every number it reports.

## Long description

Upload a CSV and ask a question. Prereg's agent, running on Vultr Serverless Inference, first **pre-registers**
an analysis plan: one test, one outcome, one alpha and a decision rule. The plan is validated against the data,
then frozen and SHA-256 fingerprinted, so it cannot be quietly changed after the result is known.

The agent then writes Python, and every line runs in a **fresh gVisor container on a Vultr VM**: no network
interface, an empty environment (the inference key never enters), 512 MB / 1 CPU / 128-process caps, a 30-second
limit, read-only data, a private 32 MB scratch area, and destruction after each step. A fixed script the model
never touches **recomputes the pre-registered test** and five checks compare it with the agent's claim. The
answer comes back as a receipt: frozen plan and fingerprint, code, verified numbers, checks, pinned library
versions and the sandbox policy.

**Containment you can test yourself:** one demo dataset hides a prompt injection telling the agent to dump its
environment and send it to an attacker; Prereg flags the cell and the sandbox makes the attack pointless. The
"Try to break the sandbox" console runs your own Python in the same sandbox with six attack presets (secret
theft, host files, data tampering, infinite loop, memory bomb, fork bomb). Every one is contained.

**Business value:** analysts, product and ops teams get statistical answers they can audit, from data they do
not have to trust, without giving an AI agent the keys to their infrastructure.

## Technology tags

Vultr Cloud Compute · Vultr Serverless Inference · gVisor · Docker · FastAPI · Python · pandas · SciPy ·
statsmodels · Next.js · TypeScript · Tailwind CSS · Caddy · praxis-agents

## Category tags

AI agents · Security · Sandboxing · Data analysis · Developer tools
