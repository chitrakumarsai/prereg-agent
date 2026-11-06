const CHECKS = [
  ["Ran the pre-registered test", "welch_t = welch_t"],
  ["Statistic reproduces", "−1.13175 = −1.13175"],
  ["p-value reproduces", "0.258319 = 0.258319"],
  ["Decision follows the rule", "p 0.258 ≥ α 0.05"],
] as const;

const LOOP_S = 3.2;

/** The product's own receipt UI, with the numbers from a real run on the checkout demo data. */
export function HeroReceipt() {
  return (
    <div className="group relative h-full overflow-hidden rounded-lg border border-line bg-paper shadow-[0_30px_60px_-30px_rgb(51_50_49/0.35)]">
      <div className="flex items-center gap-2 border-b border-line bg-surface/60 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-line" />
        <span className="h-2.5 w-2.5 rounded-full bg-line" />
        <span className="h-2.5 w-2.5 rounded-full bg-line" />
        <span className="ml-3 truncate font-mono text-xs text-muted">prereg / receipt / checkout_ab_test.csv</span>
      </div>

      <div className="grid gap-5 p-5 sm:p-7">
        <div>
          <p className="eyebrow">Question</p>
          <p className="mt-1.5 text-[1.05rem] leading-snug">
            Did the one-page checkout change the average order value compared with control?
          </p>
        </div>

        <div className="rounded-md border border-line bg-bg/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="eyebrow">Pre-registered plan · frozen 11:39:02 UTC</p>
            <span className="rounded-sm bg-accent-soft px-2 py-0.5 font-mono text-[11px] text-accent">sha256 7c4e…a91f</span>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
            {[
              ["Test", "Welch's t"],
              ["Outcome", "order_value_usd"],
              ["Groups", "variant"],
              ["Alpha", "0.05"],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-muted">{k}</dt>
                <dd className="truncate font-mono text-[13px]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="grid gap-4 sm:grid-cols-[1fr_150px]">
          <ul className="grid gap-2" aria-label="Independent verification">
            {CHECKS.map(([name, detail], i) => (
              <li
                key={name}
                className="flex items-center gap-3 text-sm group-hover:[animation-play-state:running]"
                style={{ animation: `check-in ${LOOP_S}s ${i * 0.35}s ease-out infinite` }}
              >
                <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" className="shrink-0">
                  <circle cx="9" cy="9" r="8.25" fill="var(--p-accent)" />
                  <path d="M5.5 9.2l2.3 2.3 4.7-4.9" stroke="#fff" strokeWidth="1.6" fill="none" />
                </svg>
                <span className="min-w-0 flex-1 truncate">{name}</span>
                <span className="hidden font-mono text-xs text-muted lg:inline">{detail}</span>
              </li>
            ))}
          </ul>
          <MeansChart />
        </div>

        <div className="flex items-center justify-between border-t border-dashed border-line pt-4">
          <p className="text-sm">
            <span className="font-medium">No significant difference</span>
            <span className="text-muted"> · t = −1.13, p = 0.258, n = 480</span>
          </p>
          <span className="rounded-sm bg-accent px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-white">
            Verified
          </span>
        </div>
      </div>
    </div>
  );
}

function MeansChart() {
  const bars = [
    { label: "control", value: 78.23 },
    { label: "one-page", value: 81.63 },
  ];
  const max = 90;
  return (
    <figure className="hidden flex-col justify-end sm:flex" aria-label="Mean order value by variant">
      <div className="flex h-28 items-end gap-4 border-b border-ink/30 px-2">
        {bars.map((b, i) => (
          <div key={b.label} className="flex flex-1 flex-col items-center gap-1">
            <span className="font-mono text-[11px]">${b.value.toFixed(0)}</span>
            <div
              className="w-full rounded-t-sm"
              style={{ height: `${(b.value / max) * 88}px`, background: i ? "var(--p-accent)" : "#a3a29f" }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-4 px-2 text-center font-mono text-[10px] text-muted">
        {bars.map((b) => (
          <span key={b.label} className="flex-1">
            {b.label}
          </span>
        ))}
      </div>
    </figure>
  );
}
