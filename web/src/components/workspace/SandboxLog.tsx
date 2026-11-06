"use client";

import { useEffect, useRef } from "react";

import type { LogLine, SandboxRun } from "@/lib/types";

const STAGE_TAG: Record<string, string> = {
  profile: "profile",
  plan: "plan",
  execute: "analysis",
  verify: "verifier",
  explain: "explain",
  console: "attempt",
};

const ALERT = /BLOCKED|blocked|Error|denied|Killed|timed out|WARNING/;
const WIN = /EXFILTRATED|TAMPERED|LEAKED|SUCCEEDED/;

function lineTone(line: string): string {
  if (WIN.test(line)) return "text-term-fail";
  if (ALERT.test(line)) return "text-term-warn";
  return "text-inv-ink/90";
}

const STATUS_TEXT: Record<SandboxRun["status"], string> = {
  ok: "exited 0",
  error: "exited with an error",
  timeout: "killed at the time limit",
  killed: "killed (memory or process limit)",
};

type Props = {
  logs: LogLine[];
  runs: SandboxRun[];
  isLive: boolean;
  idleHint: string;
  title?: string;
  heightClass?: string;
};

export function SandboxLog({ logs, runs, isLive, idleHint, title = "Sandbox log", heightClass = "h-[360px]" }: Props) {
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs.length, runs.length]);

  const lastRun = runs.at(-1);

  return (
    <section aria-label={title} className="flex flex-col overflow-hidden rounded-lg bg-inv-bg text-inv-ink">
      <header className="flex items-center justify-between border-b border-inv-line px-4 py-2.5">
        <p className="font-mono text-xs text-inv-muted">
          {title} <span className="text-inv-muted/60">· gVisor · network none</span>
        </p>
        <span className="flex items-center gap-2 font-mono text-[11px] text-inv-muted">
          <span className={`h-1.5 w-1.5 rounded-full ${isLive ? "dot-breathe bg-term-pass" : "bg-inv-muted/50"}`} />
          {isLive ? "live" : "idle"}
        </span>
      </header>
      <div
        ref={scroller}
        role="log"
        aria-live="polite"
        className={`${heightClass} overflow-y-auto px-4 py-3 font-mono text-[12.5px] leading-[1.7]`}
      >
        {logs.length === 0 && (
          <p className="text-inv-muted">
            <span className="text-term-pass">$</span> {idleHint}
            <span className="dot-breathe ml-1 inline-block h-3.5 w-1.5 translate-y-0.5 bg-inv-muted" />
          </p>
        )}
        {logs.map((l) => (
          <p key={l.key} className="log-line flex gap-3 whitespace-pre-wrap break-words">
            <span className="w-16 shrink-0 select-none text-inv-muted/60">{STAGE_TAG[l.stage] ?? l.stage}</span>
            <span className={`min-w-0 ${lineTone(l.line)}`}>{l.line}</span>
          </p>
        ))}
        {lastRun && !isLive && (
          <p className="log-line mt-2 border-t border-inv-line pt-2 text-inv-muted">
            <span className={lastRun.status === "ok" ? "text-term-pass" : "text-term-warn"}>■</span> container{" "}
            {STATUS_TEXT[lastRun.status]} after {lastRun.duration_s.toFixed(1)} s · exit code {lastRun.exit_code} ·
            destroyed
          </p>
        )}
      </div>
    </section>
  );
}
