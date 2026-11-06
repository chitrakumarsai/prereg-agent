---
checks:
  - forbid: "VULTR_(INFERENCE|API)_KEY\\s*=\\s*[\"'][A-Za-z0-9]"
    message: keys come from the environment, never from source
  - forbid: "NEXT_PUBLIC_[A-Z_]*(KEY|SECRET|TOKEN)"
    message: NEXT_PUBLIC_ variables ship to every browser
---
The Vultr inference key lives only in the control plane's environment (`/etc/prereg.env` in production,
`.env` locally, both git-ignored). It is never logged, never sent to the browser and never enters a sandbox.
