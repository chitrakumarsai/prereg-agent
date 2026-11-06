"use client";

import type { Receipt } from "@/lib/types";

import { VerificationList } from "./VerificationList";

function formatNumber(value: unknown): string {
  if (typeof value !== "number") return "—";
  if (value !== 0 && (Math.abs(value) < 1e-3 || Math.abs(value) >= 1e6)) return value.toExponential(3);
  return value.toFixed(4).replace(/\.?0+$/, "");
}

function downloadReceipt(receipt: Receipt): void {
  const withoutChart = { ...receipt, chart: null };
  const blob = new Blob([JSON.stringify(withoutChart, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: `prereg-receipt-${receipt.fingerprint.slice(0, 8)}.json` });
  a.click();
  URL.revokeObjectURL(url);
}

type Props = { receipt: Receipt };

export function ReceiptCard({ receipt }: Props) {
  const truth = receipt.verification.recomputed ?? {};
  const verified = receipt.verification.passed;
  const decision = receipt.result.decision === "reject" ? "Significant difference" : "No significant difference";
  const rows: [string, string][] = [
    ["Test", receipt.test_label],
    ["Statistic", formatNumber(truth.statistic)],
    ["p-value", formatNumber(truth.p_value)],
    ["Alpha", String(receipt.plan.alpha)],
    ["Rows used", String(truth.n_used ?? "—")],
    ["Code attempts", String(receipt.code_attempts)],
    ["Total time", `${receipt.duration_s} s`],
  ];

  return (
    <article aria-label="Analysis receipt" className="log-line grid gap-6 lg:grid-cols-[1.1fr_1fr]">
      <div className="receipt-edge self-start bg-paper px-6 py-8 font-mono text-[13px] shadow-[0_24px_50px_-30px_rgb(51_50_49/0.5)] sm:px-8">
        <div className="text-center">
          <p className="font-sans text-lg font-medium tracking-tight">Prereg receipt</p>
          <p className="text-xs text-muted">{new Date(receipt.completed_at).toUTCString()}</p>
        </div>
        <p className="mt-5 border-y border-dashed border-line py-3 font-sans text-sm leading-snug">{receipt.question}</p>
        <dl className="mt-3 grid gap-1.5">
          {rows.map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-2">
              <dt className="text-muted">{k}</dt>
              <span className="flex-1 translate-y-[-3px] border-b border-dotted border-line" aria-hidden="true" />
              <dd className="text-right">{v}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-4 border-t border-dashed border-line pt-3">
          <p className="text-muted">plan fingerprint (sha256)</p>
          <p className="break-all text-[11.5px]">{receipt.fingerprint}</p>
          <p className="mt-2 text-muted">stack</p>
          <p className="text-[11.5px]">
            {Object.entries(receipt.versions)
              .map(([k, v]) => `${k} ${v}`)
              .join(" · ")}
          </p>
          <p className="mt-2 text-muted">sandbox</p>
          <p className="text-[11.5px]">
            {receipt.sandbox.runtime} · net {receipt.sandbox.network} · {receipt.sandbox.memory} ·{" "}
            {receipt.sandbox.timeout_s}s · destroyed
          </p>
        </div>
        <div className="mt-5 flex items-center justify-between border-t border-dashed border-line pt-4">
          <span className="font-sans text-[15px] font-medium">{decision}</span>
          <span className={`rounded-sm px-2 py-1 text-[11px] uppercase tracking-wider text-white ${verified ? "bg-pass" : "bg-fail"}`}>
            {verified ? "Verified" : "Not verified"}
          </span>
        </div>
      </div>

      <div className="grid content-start gap-5">
        <div>
          <p className="eyebrow">What it means</p>
          <p className="mt-2 text-[15px] leading-relaxed">{receipt.explanation}</p>
        </div>
        {receipt.chart && (
          <figure className="overflow-hidden rounded-lg border border-line bg-white">
            {/* eslint-disable-next-line @next/next/no-img-element -- a base64 chart made in the sandbox */}
            <img src={`data:image/png;base64,${receipt.chart}`} alt={`Chart of ${receipt.plan.outcome} by ${receipt.plan.predictor}, drawn inside the sandbox`} className="h-auto w-full" width={960} height={600} />
          </figure>
        )}
        <div>
          <p className="eyebrow">Independent verification</p>
          <VerificationList checks={receipt.verification.checks} />
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn btn-secondary" onClick={() => downloadReceipt(receipt)}>
            Download receipt JSON
          </button>
        </div>
      </div>
    </article>
  );
}
