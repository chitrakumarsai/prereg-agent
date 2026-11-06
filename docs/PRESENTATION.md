# Presenting Prereg

Talking points for the demo video and a live presentation. The timed, screen-by-screen video script is in
[`submission/demo-script.md`](submission/demo-script.md); this page is what to *say* and how to answer questions.

Live site: https://64-177-53-95.sslip.io · Deck: https://claude.ai/artifact/5o6vxjfNw4YyHXrBuKNcrW

## The one-sentence pitch

> Prereg is an AI data analyst that commits to its test before it sees a result, runs every line of its own code
> in a gVisor sandbox with no network and no secrets, and independently re-checks every number it reports.

## The story in five beats

1. **The problem (20 s).** AI agents that run code are one prompt injection away from leaking your keys. And an
   AI analyst's numbers are unaccountable: it can pick a test after peeking, or misreport a p-value.
2. **The answer (20 s).** Containment and verification, together. The agent writes code, but the code runs sealed;
   the agent reports numbers, but a script it never touches re-derives them.
3. **Watch it work (60 s).** Run the *Support ticket times* dataset. It contains a poisoned row.
4. **Watch it hold (60 s).** Open *Try to break the sandbox* and run the attacks.
5. **Why it matters (20 s).** Teams get statistics they can audit, from data they don't have to trust, without
   handing an agent the keys to their infrastructure.

## What to point at on screen

| On screen | Say |
|---|---|
| Orange **Prompt injection spotted** banner | "The profiler runs inside the sandbox and flags the cell. It's treated as data, never as instructions." |
| **Pre-registered plan**, lock and `sha256` | "The test is chosen and frozen before any code runs. This fingerprint proves it wasn't changed after the result." |
| Dark **Sandbox log** streaming | "This is the agent's own code, running in gVisor right now. No network, no environment, 30 seconds, 512 MB." |
| Receipt: **Verified** badge, five checks | "A fixed script recomputed the test. Statistic, p-value and decision all match the agent's claim." |
| Receipt footer: stack and sandbox lines | "Pinned library versions and the exact sandbox policy: anyone can reproduce this." |
| Break-it: **Steal secrets** output | "The environment holds PATH, HOME and a cache folder. Nothing else. And the POST fails: there's no network interface." |
| Break-it: **Run forever** | "Killed at 30 seconds, container destroyed." |
| Break-it: **Eat all the memory** | "Dies at the 512 MB cap. The Vultr host never notices." |
| **Containment** section, the command | "One function builds every sandbox. A praxis rule fails the build if anyone ever adds a network or a variable." |

## The containment moments (required by the track)

Show at least one; showing three is stronger:

1. **Prompt injection** in the CSV, flagged and harmless (analysis section).
2. **Secret theft and exfiltration** attempt: empty environment, network failure (break-it console).
3. **Runaway code**: infinite loop killed at 30 s, or memory bomb killed at 512 MB (break-it console).

## Vultr, said plainly

- **Vultr Cloud Compute** runs everything that executes: Caddy, the FastAPI control plane, Docker and every gVisor
  sandbox, on one VM.
- **Vultr Serverless Inference** does all the reasoning: the plan, the code and the explanation, through its
  OpenAI-compatible API. We picked the model by running six models from the live list on the same task:
  `deepseek-v4.1-flash` leads, with `mimo-v2.6-pro` as automatic fallback.
- **The key never leaves the control plane.** It sits in a root-only file on the VM and never enters a sandbox,
  a log or the browser.

## Numbers worth saying

- About 30 seconds from question to verified receipt.
- 6 of 6 attacks contained on the live site.
- 70 automated tests, most against a real gVisor container.
- 5 rounds of independent dual code review before shipping.
- 32 MB private scratch per run, 512 MB memory, 128 processes, 30 seconds.

## Likely questions

**"Why gVisor and not just Docker?"** Docker shares the host kernel; a kernel exploit in model-written code would
reach the host. gVisor gives each container a user-space kernel, so the exploit lands in a fake kernel.

**"What stops the model from lying about the result?"** It can't change the plan (frozen and fingerprinted before
code runs), and its numbers don't count: the receipt's headline comes from an independent recomputation. If they
disagree, the receipt says *Not verified*.

**"What if the injected instruction works on the model?"** Then the code it writes still runs with no network, no
keys and no host files. The point isn't that the model is obedient or not; it's that obedience doesn't matter.

**"Which tests does it support?"** Welch's t-test, Mann-Whitney U, chi-square and single-predictor regression, each
with one canonical call so verification is exact.

**"Can it scale?"** Sandboxes are cheap and stateless; the control plane caps 2 concurrent containers on this VM.
More VMs, or a queue, scale it out.

**"Is this production-ready?"** It's a hackathon build with production habits: rate limits, per-address caps, HTTPS
with security headers, startup clean-up, and every review finding fixed with a test. The README's *Known limits*
section is honest about what's next (a non-root control plane, persistent run storage).

## Before you record or present

- [ ] Open the live site once and run the hostile dataset, so the model is warm.
- [ ] Use a 1440×900 browser window; hide the bookmarks bar.
- [ ] Keep at most two runs going at once (the per-address limit).
- [ ] Have the deck open in another tab for the opening and closing slides.
- [ ] If the network is slow, the receipt can take up to a minute; keep talking over the live log.
