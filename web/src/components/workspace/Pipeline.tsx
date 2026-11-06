import type { RunState, StageName, StageStatus } from "@/lib/types";

const STEPS: { stage: StageName; label: string; hint: string }[] = [
  { stage: "profile", label: "Profile", hint: "read the CSV inside the sandbox" },
  { stage: "plan", label: "Pre-register", hint: "commit to one test, then freeze it" },
  { stage: "execute", label: "Execute", hint: "write code, run it sealed" },
  { stage: "verify", label: "Verify", hint: "recompute every number independently" },
  { stage: "explain", label: "Explain", hint: "plain-English answer" },
];

const DOT: Record<StageStatus, string> = {
  pending: "border-line bg-paper",
  running: "border-accent bg-accent-soft",
  done: "border-accent bg-accent",
  error: "border-fail bg-fail",
};

type Props = { stages: RunState["stages"] };

export function Pipeline({ stages }: Props) {
  return (
    <ol className="grid grid-cols-5 gap-1.5" aria-label="Analysis steps">
      {STEPS.map(({ stage, label, hint }, i) => {
        const status = stages[stage] ?? "pending";
        return (
          <li key={stage} className="min-w-0">
            <div className={`h-1 rounded-full ${status === "pending" ? "bg-line" : status === "error" ? "bg-fail" : "bg-accent"} ${status === "running" ? "dot-breathe" : ""}`} />
            <div className="mt-2.5 flex items-center gap-2">
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] ${DOT[status]} ${status === "done" || status === "error" ? "text-white" : "text-muted"}`}>
                {status === "done" ? "✓" : status === "error" ? "!" : i + 1}
              </span>
              <span className={`truncate text-sm ${status === "pending" ? "text-muted" : "font-medium"}`}>{label}</span>
            </div>
            <p className="mt-1 hidden truncate text-xs text-muted lg:block">{hint}</p>
            <span className="sr-only">{status}</span>
          </li>
        );
      })}
    </ol>
  );
}
