import type { PlanEvent } from "@/lib/types";

type Props = { plan: PlanEvent | null; isRunning: boolean };

export function PlanCard({ plan, isRunning }: Props) {
  if (!plan) {
    return (
      <section aria-label="Pre-registered plan" className="rounded-lg border border-dashed border-line bg-paper/50 p-5">
        <p className="eyebrow">Pre-registered plan</p>
        <p className="mt-3 text-sm text-muted">
          {isRunning
            ? "The agent is choosing a test. It must commit before any code runs."
            : "Before touching the data, the agent commits to one test, one outcome, one alpha and a decision rule. The plan is then frozen and fingerprinted, so it can't be quietly changed after the result is known."}
        </p>
        <div className="mt-4 grid grid-cols-2 gap-3" aria-hidden="true">
          {["Test", "Outcome", "Predictor", "Alpha"].map((k) => (
            <div key={k} className="h-10 rounded-sm bg-surface/70" />
          ))}
        </div>
      </section>
    );
  }
  const p = plan.plan;
  const fields = [
    ["Test", plan.test_label],
    ["Outcome", p.outcome],
    ["Predictor", p.predictor],
    ["Alpha", String(p.alpha)],
  ];
  return (
    <section aria-label="Pre-registered plan" className="log-line rounded-lg border border-line bg-paper p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="eyebrow">Pre-registered plan</p>
        <span className="inline-flex items-center gap-1.5 rounded-sm bg-accent-soft px-2 py-0.5 font-mono text-[11px] text-accent">
          <svg width="10" height="12" viewBox="0 0 10 12" aria-hidden="true">
            <rect x="1" y="5" width="8" height="6.5" rx="1" fill="currentColor" />
            <path d="M2.8 5V3.4a2.2 2.2 0 014.4 0V5" stroke="currentColor" strokeWidth="1.3" fill="none" />
          </svg>
          frozen {new Date(plan.frozen_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
        </span>
      </div>
      <p className="mt-3 text-[15px] leading-snug">{p.hypothesis}</p>
      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
        {fields.map(([k, v]) => (
          <div key={k} className="min-w-0">
            <dt className="text-xs text-muted">{k}</dt>
            <dd className="truncate font-mono text-[13px]">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
        <span className="text-ink">Decision rule:</span> {p.decision_rule}
      </p>
      <p className="mt-2 truncate font-mono text-[11px] text-muted" title={plan.fingerprint}>
        sha256 {plan.fingerprint}
      </p>
    </section>
  );
}
