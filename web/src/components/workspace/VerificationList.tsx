import type { Check } from "@/lib/types";

type Props = { checks: Check[] };

export function VerificationList({ checks }: Props) {
  return (
    <ul className="divide-y divide-line" aria-label="Verification checks">
      {checks.map((c) => (
        <li key={c.name} className="log-line flex gap-3 py-2.5">
          <span
            className={`mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full text-[11px] text-white ${c.passed ? "bg-pass" : "bg-fail"}`}
            aria-label={c.passed ? "passed" : "failed"}
          >
            {c.passed ? "✓" : "✕"}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium">{c.name}</p>
            <p className="break-words font-mono text-xs text-muted">{c.detail}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
