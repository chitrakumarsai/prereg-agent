"use client";

import { useState } from "react";

import { SandboxLog } from "@/components/workspace/SandboxLog";
import { useRunStream } from "@/hooks/useRunStream";
import { startConsole } from "@/lib/api";
import { ATTACK_PRESETS, type AttackPreset } from "@/lib/presets";

const MAX_CODE = 20_000;

function Verdict({ preset, status, log }: { preset: AttackPreset | null; status: string; log: string }) {
  if (!preset) {
    return <p className="text-sm text-inv-muted">Custom code ran with status “{status}”. Read the log for what it reached.</p>;
  }
  const held = preset.containedWhen(status as never, log);
  return (
    <p className={`flex items-start gap-2.5 text-sm ${held ? "text-term-pass" : "text-term-fail"}`}>
      <span className="font-mono">{held ? "■" : "▲"}</span>
      <span>
        <span className="font-medium">{held ? "Contained." : "Unexpected result."}</span>{" "}
        <span className="text-inv-ink/80">{held ? preset.expect : "Containment did not behave as expected; see the log."}</span>
      </span>
    </p>
  );
}

export function BreakIt() {
  const [presetId, setPresetId] = useState<string | null>(ATTACK_PRESETS[0].id);
  const [code, setCode] = useState(ATTACK_PRESETS[0].code);
  const { state, run } = useRunStream();

  const preset = ATTACK_PRESETS.find((p) => p.id === presetId) ?? null;
  const isBusy = state.phase === "starting" || state.phase === "running";
  const lastRun = state.runs.at(-1);
  const logText = state.logs.map((l) => l.line).join("\n");

  const choose = (p: AttackPreset) => {
    setPresetId(p.id);
    setCode(p.code);
  };

  return (
    <section id="break-it" aria-labelledby="break-heading" className="on-dark bg-inv-bg py-20 text-inv-ink lg:py-28">
      <div className="wrap">
        <div className="grid gap-4 lg:grid-cols-12 lg:items-end">
          <h2 id="break-heading" className="h2 lg:col-span-6">
            Try to break the sandbox
          </h2>
          <p className="max-w-[52ch] text-inv-muted lg:col-span-5 lg:col-start-8">
            This console runs your Python in the exact sandbox the agent uses. Pick an attack or write your own, and watch
            what it can actually reach.
          </p>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-12">
          <ul className="grid content-start gap-2 lg:col-span-4" aria-label="Attack presets">
            {ATTACK_PRESETS.map((p) => {
              const isActive = p.id === presetId;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    aria-pressed={isActive}
                    disabled={isBusy}
                    onClick={() => choose(p)}
                    className={`card-lift w-full rounded-md border px-4 py-3 text-left disabled:opacity-60 ${isActive ? "border-term-pass/70 bg-inv-surface" : "border-inv-line hover:border-inv-muted/60"}`}
                  >
                    <span className="block text-[15px] font-medium">{p.label}</span>
                    <span className="mt-0.5 block text-xs leading-snug text-inv-muted">{p.threat}</span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-4 lg:col-span-8">
            <div className="overflow-hidden rounded-lg border border-inv-line">
              <div className="flex items-center justify-between border-b border-inv-line bg-inv-surface/60 px-4 py-2">
                <label htmlFor="attack-code" className="font-mono text-xs text-inv-muted">
                  attempt.py {preset ? "" : "· custom"}
                </label>
                <span className="font-mono text-[11px] text-inv-muted">{code.length.toLocaleString()} / 20,000</span>
              </div>
              <textarea
                id="attack-code"
                value={code}
                spellCheck={false}
                maxLength={MAX_CODE}
                disabled={isBusy}
                onChange={(e) => {
                  setCode(e.target.value);
                  setPresetId(null);
                }}
                className="block h-[230px] w-full resize-none bg-inv-bg p-4 font-mono text-[12.5px] leading-[1.7] text-inv-ink focus:outline-none"
              />
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                type="button"
                className="btn bg-inv-ink text-inv-bg hover:bg-white"
                disabled={isBusy || !code.trim()}
                onClick={() => void run(() => startConsole(code, "support_tickets"))}
              >
                {isBusy ? "Running sealed…" : "Run it in the sandbox"}
              </button>
              {preset && <p className="text-sm text-inv-muted">Expected: {preset.expect}</p>}
            </div>
            <SandboxLog
              logs={state.logs}
              runs={state.runs}
              isLive={isBusy}
              title="attempt.py output"
              heightClass="h-[240px]"
              idleHint="pick an attack and press run."
            />
            {state.error && <p className="text-sm text-term-fail">{state.error}</p>}
            {lastRun && !isBusy && <Verdict preset={preset} status={lastRun.status} log={logText} />}
          </div>
        </div>
      </div>
    </section>
  );
}
