import { BrandIcon, type BrandName } from "@/components/ui/BrandIcon";

import { ContainmentDiagram } from "./ContainmentDiagram";

const COMMAND = `docker run --rm --runtime runsc --network none \\
  --memory 512m --memory-swap 512m --cpus 1 --pids-limit 128 \\
  --read-only --tmpfs /tmp:rw,size=64m --cap-drop ALL \\
  --security-opt no-new-privileges --user 1000:1000 \\
  -v $RUN/data:/data:ro -v $RUN/code:/code:ro -v $RUN/out:/out \\
  prereg-sandbox:1 env -i PATH=… HOME=/tmp MPLCONFIGDIR=/tmp/mpl \\
  timeout -k 2 30 python -u -I /code/analysis.py`;

const STACK: { icon: BrandName; name: string; role: string }[] = [
  { icon: "vultr", name: "Vultr Cloud Compute", role: "hosts the control plane and every sandbox" },
  { icon: "vultr", name: "Vultr Serverless Inference", role: "plans, code and explanations" },
  { icon: "docker", name: "Docker + gVisor", role: "one sealed container per step" },
  { icon: "python", name: "pandas · SciPy · statsmodels", role: "pinned inside the sandbox image" },
];

const GUARANTEES = [
  ["The key stays outside", "Only the control plane talks to Vultr Inference. The sandbox starts with env -i: three harmless variables, nothing else."],
  ["Results are re-derived", "A fixed script the model never touches recomputes the pre-registered test. The agent's numbers must match it."],
  ["Nothing outlives a step", "Profile, analysis and verification each get a fresh container, deleted with its folder as soon as it exits."],
];

export function Containment() {
  return (
    <section id="containment" aria-labelledby="containment-heading" className="py-20 lg:py-28">
      <div className="wrap">
        <div className="grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <h2 id="containment-heading" className="h2">
              Containment for every line the agent writes
            </h2>
            <p className="mt-5 max-w-[46ch] text-muted">
              Model-written code is treated as hostile by default. It runs under gVisor, a user-space kernel, so even a
              kernel exploit lands in a fake kernel, not on the Vultr host.
            </p>
            <ul className="mt-9 grid gap-6">
              {GUARANTEES.map(([title, body]) => (
                <li key={title} className="grid grid-cols-[18px_1fr] gap-3">
                  <span className="mt-1.5 h-2.5 w-2.5 rounded-sm bg-accent" aria-hidden="true" />
                  <div>
                    <p className="font-medium">{title}</p>
                    <p className="mt-1 text-sm leading-relaxed text-muted">{body}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid content-start gap-6 lg:col-span-7">
            <div className="rounded-lg border border-line bg-paper p-5 sm:p-7">
              <ContainmentDiagram />
            </div>
            <div className="overflow-hidden rounded-lg bg-inv-bg">
              <p className="border-b border-inv-line px-4 py-2.5 font-mono text-xs text-inv-muted">
                prereg/runner.py · the command for every step (name and log flags omitted)
              </p>
              <pre className="overflow-x-auto px-4 py-4 font-mono text-[12px] leading-[1.75] text-inv-ink">
                <code>{COMMAND}</code>
              </pre>
            </div>
          </div>
        </div>

        <ul className="mt-14 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {STACK.map((s) => (
            <li key={s.name} className="flex items-start gap-3 bg-bg p-5">
              <BrandIcon name={s.icon} size={22} className="mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">{s.name}</p>
                <p className="text-xs leading-relaxed text-muted">{s.role}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
