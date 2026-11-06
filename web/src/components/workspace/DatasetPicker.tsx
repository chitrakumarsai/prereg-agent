"use client";

import { useRef } from "react";

import type { Dataset } from "@/lib/types";

export type Source = { kind: "demo"; id: string } | { kind: "file"; file: File };

const MAX_UPLOAD_MB = 5;

type Props = {
  datasets: Dataset[];
  source: Source | null;
  isDisabled: boolean;
  onPick: (source: Source, suggestedQuestion?: string) => void;
  onError: (message: string) => void;
};

export function DatasetPicker({ datasets, source, isDisabled, onPick, onError }: Props) {
  const fileInput = useRef<HTMLInputElement>(null);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) return onError("Please choose a .csv file.");
    if (file.size > MAX_UPLOAD_MB * 1_000_000) return onError(`That file is over ${MAX_UPLOAD_MB} MB.`);
    onPick({ kind: "file", file });
  };

  return (
    <fieldset disabled={isDisabled} className="grid gap-2.5">
      <legend className="eyebrow mb-3">1 · Choose data</legend>
      {datasets.map((d) => {
        const isActive = source?.kind === "demo" && source.id === d.id;
        return (
          <button
            key={d.id}
            type="button"
            aria-pressed={isActive}
            onClick={() => onPick({ kind: "demo", id: d.id }, d.question)}
            className={`card-lift group w-full rounded-md border bg-paper p-4 text-left disabled:pointer-events-none ${isActive ? "border-accent shadow-[inset_0_0_0_1px_var(--p-accent)]" : "border-line hover:border-ink/40"}`}
          >
            <span className="flex items-center justify-between gap-2">
              <span className="font-medium">{d.title}</span>
              {d.hostile ? (
                <span className="rounded-sm bg-contain-soft px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-contain">
                  hostile cell
                </span>
              ) : (
                <span className="font-mono text-[11px] text-muted">{d.rows} rows</span>
              )}
            </span>
            <span className="mt-1 block text-sm leading-snug text-muted">{d.blurb}</span>
          </button>
        );
      })}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFile(e.dataTransfer.files[0]);
        }}
        className={`flex items-center justify-between gap-3 rounded-md border border-dashed p-4 ${source?.kind === "file" ? "border-accent bg-accent-soft/40" : "border-line"}`}
      >
        <span className="min-w-0 text-sm">
          {source?.kind === "file" ? (
            <span className="block truncate font-mono">{source.file.name}</span>
          ) : (
            <span className="text-muted">Or drop your own CSV (up to {MAX_UPLOAD_MB} MB)</span>
          )}
        </span>
        <button type="button" className="btn btn-secondary h-9 shrink-0 px-3 text-sm" onClick={() => fileInput.current?.click()}>
          Upload CSV
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          aria-label="Upload a CSV file"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
    </fieldset>
  );
}
