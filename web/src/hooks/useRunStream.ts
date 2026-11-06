"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

import { eventsUrl } from "@/lib/api";
import { INITIAL_RUN, runReducer } from "@/lib/run-reducer";
import type { RunState, ServerEvent } from "@/lib/types";

/** Starts a run with `launch`, then follows its server-sent events until the server says it ended. */
export function useRunStream(): {
  state: RunState;
  run: (launch: () => Promise<string>) => Promise<void>;
} {
  const [state, dispatch] = useReducer(runReducer, INITIAL_RUN);
  const sourceRef = useRef<EventSource | null>(null);
  // Bumped on every new run and on unmount, so a launch that resolves late cannot open a stale stream.
  const generation = useRef(0);

  const close = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  useEffect(
    () => () => {
      generation.current += 1;
      close();
    },
    [close],
  );

  const run = useCallback(
    async (launch: () => Promise<string>) => {
      close();
      const mine = ++generation.current;
      dispatch({ type: "start" });
      let runId: string;
      try {
        runId = await launch();
      } catch (error: unknown) {
        if (mine === generation.current) {
          dispatch({ type: "fail", message: error instanceof Error ? error.message : "Could not start the run." });
        }
        return;
      }
      if (mine !== generation.current) return;
      const source = new EventSource(eventsUrl(runId));
      sourceRef.current = source;
      source.onmessage = (msg) => {
        try {
          dispatch({ type: "event", event: JSON.parse(msg.data) as ServerEvent });
        } catch {
          // a malformed event is skipped; the stream continues
        }
      };
      source.addEventListener("end", () => {
        close();
        dispatch({ type: "closed" });
      });
      source.onerror = () => {
        if (source.readyState === EventSource.CLOSED) {
          close();
          dispatch({ type: "fail", message: "Lost the connection to the run. Refresh to try again." });
        }
      };
    },
    [close],
  );

  return { state, run };
}
