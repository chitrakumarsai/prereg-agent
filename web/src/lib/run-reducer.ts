import type {
  Check,
  PlanEvent,
  Receipt,
  RunState,
  SandboxRun,
  ServerEvent,
  StageName,
  StageStatus,
  SuspiciousCell,
  Verification,
} from "./types";

export const MAX_LOG_LINES = 600;

export const INITIAL_RUN: RunState = {
  phase: "idle",
  stages: {},
  logs: [],
  profile: null,
  alert: null,
  plan: null,
  code: null,
  runs: [],
  retries: [],
  verification: null,
  explanation: null,
  receipt: null,
  error: null,
};

export type RunAction =
  | { type: "start" }
  | { type: "fail"; message: string }
  | { type: "event"; event: ServerEvent }
  | { type: "closed" };

function withStage(state: RunState, stage: StageName, status: StageStatus): RunState {
  return { ...state, stages: { ...state.stages, [stage]: status } };
}

function markRunningAsError(stages: RunState["stages"]): RunState["stages"] {
  return Object.fromEntries(
    Object.entries(stages).map(([k, v]) => [k, v === "running" ? "error" : v]),
  ) as RunState["stages"];
}

function applyEvent(state: RunState, { type, data, id }: ServerEvent): RunState {
  const running = state.phase === "starting" ? { ...state, phase: "running" as const } : state;
  switch (type) {
    case "stage":
      return withStage(running, data.stage as StageName, data.status as StageStatus);
    case "log": {
      const line = { key: id, stage: data.stage as StageName, line: String(data.line) };
      return { ...running, logs: [...running.logs, line].slice(-MAX_LOG_LINES) };
    }
    case "profile":
      return { ...running, profile: data as unknown as RunState["profile"] };
    case "alert":
      return { ...running, alert: { message: String(data.message), cells: data.cells as SuspiciousCell[] } };
    case "plan":
      return { ...running, plan: data as unknown as PlanEvent };
    case "code":
      return { ...running, code: { code: String(data.code), attempt: Number(data.attempt) } };
    case "run":
      return { ...running, runs: [...running.runs, data as unknown as SandboxRun] };
    case "retry":
      return {
        ...running,
        retries: [...running.retries, { stage: data.stage as StageName, attempt: Number(data.attempt), reason: String(data.reason) }],
      };
    case "verify":
      return { ...running, verification: { ...(data as unknown as Verification), checks: data.checks as Check[] } };
    case "explain":
      return { ...running, explanation: String(data.text) };
    case "receipt":
      return { ...running, receipt: data as unknown as Receipt };
    case "error":
      return { ...running, phase: "error", error: String(data.message), stages: markRunningAsError(running.stages) };
    default:
      return running;
  }
}

export function runReducer(state: RunState, action: RunAction): RunState {
  switch (action.type) {
    case "start":
      return { ...INITIAL_RUN, phase: "starting" };
    case "fail":
      return { ...state, phase: "error", error: action.message, stages: markRunningAsError(state.stages) };
    case "event":
      return applyEvent(state, action.event);
    case "closed":
      return state.phase === "error" ? state : { ...state, phase: "done" };
  }
}
