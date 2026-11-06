# Demo video script (about 3 minutes)

Record the live site at https://64-177-53-95.sslip.io in a 1440×900 browser window. Two containment moments
are required by the track; they are marked ★.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | Hero | "AI agents that run code are one prompt injection away from leaking your keys. Prereg is a data analyst built containment-first, on Vultr." |
| 0:15–0:35 | Scroll to **Ask a question of your data**; pick **Support ticket times** (hostile cell badge) | "This support dataset has a poisoned row: an agent note telling the AI to dump its environment and send it to an attacker." |
| 0:35–1:15 | Press **Run the analysis**. Point at the orange **Prompt injection spotted** banner, then the frozen plan and its fingerprint, then the live sandbox log | ★ "The profiler runs inside the sandbox and flags the cell. The agent commits to a Mann-Whitney test and the plan is frozen before any code runs. The code runs in gVisor: no network, no environment, the key never enters." |
| 1:15–1:45 | The receipt: **Verified** badge, five green checks, chart | "A fixed script the model never touches recomputes the test. Statistic, p-value and decision all match. That's the receipt: plan, code, numbers, library versions, sandbox policy." |
| 1:45–2:10 | **Try to break the sandbox** → **Steal secrets and phone home** → Run | ★ "Now the attack itself. The environment holds only PATH, HOME and a cache folder. The POST fails: there is no network interface at all." |
| 2:10–2:40 | **Run forever** → Run (wait for the 30 s kill), then **Eat all the memory** | ★ "An infinite loop is killed at 30 seconds and the container destroyed. A memory bomb dies at the 512 MB cap. The Vultr host never notices." |
| 2:40–3:00 | Scroll to **Containment**: diagram, the docker command, the Vultr tiles | "Every step is one command: gVisor, no network, empty env, caps, read-only data, destroyed after. Vultr Cloud Compute runs it; Vultr Serverless Inference does the thinking. Prereg: answers you can audit, from code you never had to trust." |

**Tips:** hide the bookmarks bar; run the hostile dataset once before recording so the model is warm; the
infinite-loop wait is 30 s, so speed that segment up 2× in editing.
