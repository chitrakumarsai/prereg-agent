import { HeroReceipt } from "./HeroReceipt";

export function Hero() {
  return (
    <section
      id="top"
      aria-labelledby="hero-heading"
      className="relative flex min-h-[calc(100svh-4rem)] items-center py-10 lg:py-14"
    >
      <div className="wrap grid grid-cols-[minmax(0,1fr)] items-center gap-10 lg:grid-cols-12 lg:gap-8">
        <div className="lg:col-span-5">
          <p className="mb-5 inline-flex items-center gap-2 font-mono text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            Built on Vultr · gVisor sandbox · Agent Rush 2026
          </p>
          <h1 id="hero-heading" className="display text-[2.5rem] sm:text-[3.5rem] xl:text-[4.5rem]">
            AI data analysis with receipts
          </h1>
          <p className="mt-6 max-w-[42ch] text-lg leading-relaxed text-muted sm:text-xl sm:leading-[1.5]">
            Upload a CSV and ask a question. Prereg commits to its test before it sees a result, runs its own code in a
            sealed sandbox, then re-checks every number independently.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <a href="#analyse" className="btn btn-primary w-full sm:w-auto">
              Analyse a CSV
            </a>
            <a href="#break-it" className="btn btn-secondary w-full sm:w-auto">
              Try to break the sandbox
            </a>
          </div>
          <dl className="mt-10 grid max-w-md grid-cols-4 border-t border-line pt-5">
            {[
              ["none", "network"],
              ["0", "secrets"],
              ["30 s", "time cap"],
              ["512 MB", "memory cap"],
            ].map(([v, k]) => (
              <div key={k}>
                <dt className="sr-only">{k}</dt>
                <dd className="font-mono text-[15px] font-medium">{v}</dd>
                <dd className="text-xs text-muted">{k}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="relative lg:col-span-6 lg:col-start-7">
          <HeroReceipt />
          <div className="absolute -bottom-12 left-5 hidden w-[300px] items-center gap-3 rounded-md border border-line bg-paper px-4 py-3 sm:flex">
            <span className="dot-breathe h-2 w-2 shrink-0 rounded-full bg-accent" />
            <p className="font-mono text-xs leading-snug">
              sandbox exited 0 in 2.1 s
              <span className="block text-muted">network none · env empty · destroyed</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
