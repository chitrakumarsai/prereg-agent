"use client";

import { useEffect, useState } from "react";

import { useRunStream } from "@/hooks/useRunStream";
import { fetchDatasets, startAnalysis } from "@/lib/api";
import type { Dataset } from "@/lib/types";

import { DEMO_DATASETS } from "./demo-datasets";
import { DatasetPicker, type Source } from "./DatasetPicker";
import { Pipeline } from "./Pipeline";
import { PlanCard } from "./PlanCard";
import { ReceiptCard } from "./ReceiptCard";
import { SandboxLog } from "./SandboxLog";

const MIN_QUESTION = 5;
const MAX_QUESTION = 500;

export function Workspace() {
  const [datasets, setDatasets] = useState<Dataset[]>(DEMO_DATASETS);
  const [source, setSource] = useState<Source | null>({ kind: "demo", id: DEMO_DATASETS[0].id });
  const [question, setQuestion] = useState(DEMO_DATASETS[0].question);
  const [formError, setFormError] = useState<string | null>(null);
  const { state, run } = useRunStream();

  useEffect(() => {
    fetchDatasets().then((d) => d?.length && setDatasets(d));
  }, []);

  const isBusy = state.phase === "starting" || state.phase === "running";
  const trimmed = question.trim();
  const canRun = !isBusy && source !== null && trimmed.length >= MIN_QUESTION;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!source) return setFormError("Choose a dataset or upload a CSV first.");
    if (trimmed.length < MIN_QUESTION) return setFormError("Ask a question of at least a few words.");
    setFormError(null);
    const payload = source.kind === "demo" ? { dataset: source.id } : { file: source.file };
    void run(() => startAnalysis(trimmed, payload));
  };

  return (
    <section id="analyse" aria-labelledby="analyse-heading" className="border-t border-line bg-surface/50 py-20 lg:py-24">
      <div className="wrap">
        <div className="grid gap-4 lg:grid-cols-12 lg:items-end">
          <h2 id="analyse-heading" className="h2 lg:col-span-6">
            Ask a question of your data
          </h2>
          <p className="max-w-[52ch] text-muted lg:col-span-5 lg:col-start-8">
            Pick a demo dataset or upload a CSV. You will watch every step: the frozen plan, the sandbox output as it
            happens, and the independent check of each number.
          </p>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-12">
          <form onSubmit={handleSubmit} className="grid content-start gap-7 lg:col-span-4" noValidate>
            <DatasetPicker
              datasets={datasets}
              source={source}
              isDisabled={isBusy}
              onError={setFormError}
              onPick={(next, suggested) => {
                setSource(next);
                setFormError(null);
                if (suggested) setQuestion(suggested);
              }}
            />
            <div>
              <label htmlFor="question" className="eyebrow mb-3 block">
                2 · Ask one question
              </label>
              <textarea
                id="question"
                value={question}
                maxLength={MAX_QUESTION}
                rows={3}
                disabled={isBusy}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full resize-none rounded-md border border-line bg-paper p-3.5 text-[15px] leading-snug transition-colors focus:border-accent focus:outline-none disabled:opacity-60"
              />
              <p className="mt-1 text-right font-mono text-[11px] text-muted">
                {question.length}/{MAX_QUESTION}
              </p>
            </div>
            <div>
              <button type="submit" className="btn btn-primary w-full" disabled={!canRun}>
                {isBusy ? "Running in the sandbox…" : "Run the analysis"}
              </button>
              {(formError || state.error) && (
                <p role="alert" className="mt-3 rounded-md bg-fail-soft px-3 py-2 text-sm text-fail">
                  {formError ?? state.error}
                </p>
              )}
            </div>
          </form>

          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-5 lg:col-span-8">
            <Pipeline stages={state.stages} />
            {state.alert && (
              <div role="status" className="log-line flex gap-3 rounded-md border border-contain/30 bg-contain-soft px-4 py-3 text-sm">
                <span className="mt-0.5 font-mono text-contain">⚠</span>
                <div className="min-w-0">
                  <p className="font-medium text-contain">Prompt injection spotted in the data</p>
                  <p className="text-ink/80">{state.alert.message}</p>
                  {state.alert.cells[0] && (
                    <p className="mt-1 truncate font-mono text-xs text-muted" title={state.alert.cells[0].excerpt}>
                      row {state.alert.cells[0].row}, {state.alert.cells[0].column}: “{state.alert.cells[0].excerpt}”
                    </p>
                  )}
                </div>
              </div>
            )}
            <div className="grid gap-5 xl:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
              <PlanCard plan={state.plan} isRunning={isBusy} />
              <SandboxLog
                logs={state.logs}
                runs={state.runs}
                isLive={isBusy}
                idleHint="waiting for a run. Every step executes in a fresh gVisor container."
              />
            </div>
            {state.code && (
              <details className="group rounded-lg border border-line bg-paper">
                <summary className="flex cursor-pointer list-none items-center justify-between px-5 py-3.5 text-sm">
                  <span>
                    <span className="font-medium">Code the agent wrote</span>
                    <span className="text-muted"> · attempt {state.code.attempt} · ran sealed, never on the server</span>
                  </span>
                  <span className="font-mono text-muted transition-transform group-open:rotate-45">+</span>
                </summary>
                <pre className="max-h-[420px] overflow-auto border-t border-line px-5 py-4 font-mono text-[12.5px] leading-relaxed">
                  <code>{state.code.code}</code>
                </pre>
              </details>
            )}
            {state.retries.length > 0 && (
              <ul className="grid gap-1 text-sm text-muted">
                {state.retries.map((r) => (
                  <li key={`${r.stage}-${r.attempt}`}>
                    <span className="font-mono text-contain">retry</span> {r.stage} attempt {r.attempt}: {r.reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {state.receipt && (
          <div className="mt-14 border-t border-line pt-12">
            <ReceiptCard receipt={state.receipt} />
          </div>
        )}
      </div>
    </section>
  );
}
