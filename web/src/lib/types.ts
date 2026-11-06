export type StageName = "profile" | "plan" | "execute" | "verify" | "explain" | "console";
export type StageStatus = "pending" | "running" | "done" | "error";
export type SandboxStatus = "ok" | "error" | "timeout" | "killed";

export interface Dataset {
  id: string;
  title: string;
  domain: string;
  rows: number;
  question: string;
  blurb: string;
  hostile?: boolean;
}

export interface Plan {
  hypothesis: string;
  test: "welch_t" | "mann_whitney" | "chi_square" | "ols";
  outcome: string;
  predictor: string;
  alpha: number;
  decision_rule: string;
  rationale: string;
}

export interface Check {
  name: string;
  passed: boolean;
  detail: string;
}

export interface Verification {
  passed: boolean;
  checks: Check[];
  recomputed: Record<string, unknown> | null;
}

export interface SuspiciousCell {
  row: number;
  column: string;
  excerpt: string;
}

export interface ColumnProfile {
  name: string;
  kind: "numeric" | "categorical";
  missing: number;
  unique: number;
}

export interface SandboxPolicy {
  runtime: string;
  image: string;
  network: string;
  memory: string;
  cpus: string;
  pids: number;
  timeout_s: number;
  filesystem: string;
  environment: string;
  user: string;
  lifecycle: string;
  command: string;
}

export interface Receipt {
  question: string;
  plan: Plan;
  test_label: string;
  fingerprint: string;
  frozen_at: string;
  code: string;
  code_attempts: number;
  result: Record<string, unknown>;
  chart: string | null;
  verification: Verification;
  explanation: string;
  versions: Record<string, string>;
  models: { primary: string; fallback: string };
  sandbox: SandboxPolicy;
  suspicious_cells: number;
  duration_s: number;
  completed_at: string;
}

export interface LogLine {
  key: number;
  stage: StageName;
  line: string;
}

export interface SandboxRun {
  attempt?: number;
  status: SandboxStatus;
  exit_code: number;
  duration_s: number;
  result_error?: string | null;
}

export interface PlanEvent {
  plan: Plan;
  test_label: string;
  model: string;
  fingerprint: string;
  frozen_at: string;
  attempt: number;
}

export interface RunState {
  phase: "idle" | "starting" | "running" | "done" | "error";
  stages: Partial<Record<StageName, StageStatus>>;
  logs: LogLine[];
  profile: { rows: number; columns: ColumnProfile[]; suspicious: SuspiciousCell[] } | null;
  alert: { message: string; cells: SuspiciousCell[] } | null;
  plan: PlanEvent | null;
  code: { code: string; attempt: number } | null;
  runs: SandboxRun[];
  retries: { stage: StageName; attempt: number; reason: string }[];
  verification: Verification | null;
  explanation: string | null;
  receipt: Receipt | null;
  error: string | null;
}

export interface ServerEvent {
  id: number;
  type: string;
  t: number;
  data: Record<string, unknown>;
}
