import type { Dataset, SandboxPolicy } from "./types";

/** Empty in production (same origin behind Caddy); http://localhost:8000 in local dev. */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function parseError(resp: Response): Promise<string> {
  try {
    const body: unknown = await resp.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    }
  } catch {
    // fall through to the status text
  }
  return `Request failed (${resp.status} ${resp.statusText})`;
}

async function postForRunId(path: string, init: RequestInit): Promise<string> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, { method: "POST", ...init });
  } catch {
    throw new Error("Could not reach the Prereg server. Check your connection and try again.");
  }
  if (!resp.ok) throw new Error(await parseError(resp));
  const body = (await resp.json()) as { run_id?: unknown };
  if (typeof body.run_id !== "string") throw new Error("The server returned an unexpected response.");
  return body.run_id;
}

export function startAnalysis(question: string, source: { dataset: string } | { file: File }): Promise<string> {
  const form = new FormData();
  form.set("question", question);
  if ("dataset" in source) form.set("dataset", source.dataset);
  else form.set("file", source.file);
  return postForRunId("/api/runs", { body: form });
}

export function startConsole(code: string, dataset: string | null): Promise<string> {
  return postForRunId("/api/console", {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, dataset }),
  });
}

export function eventsUrl(runId: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/events`;
}

export function datasetUrl(id: string): string {
  return `${API_BASE}/api/datasets/${encodeURIComponent(id)}.csv`;
}

export async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const resp = await fetch(`${API_BASE}${path}`);
    return resp.ok ? ((await resp.json()) as T) : null;
  } catch {
    return null;
  }
}

export const fetchDatasets = (): Promise<Dataset[] | null> => fetchJson<Dataset[]>("/api/datasets");
export const fetchPolicy = (): Promise<SandboxPolicy | null> => fetchJson<SandboxPolicy>("/api/policy");
