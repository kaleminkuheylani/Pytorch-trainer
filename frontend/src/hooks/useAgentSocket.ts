"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ClientMessage,
  EpochMetrics,
  LintIssue,
  PendingFunction,
  StreamEvent,
  ArchitectureInfo,
  TrainingSummary,
} from "@/types/events";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/ws/analyze";

export interface AgentState {
  connected: boolean;
  lintIssues: LintIssue[];
  pendingFunctions: PendingFunction[];
  architecture: ArchitectureInfo | null;
  epochs: EpochMetrics[];
  summary: TrainingSummary | null;
  events: StreamEvent[];
  analyzing: boolean;
  error: string | null;
}

const initialState: AgentState = {
  connected: false,
  lintIssues: [],
  pendingFunctions: [],
  architecture: null,
  epochs: [],
  summary: null,
  events: [],
  analyzing: false,
  error: null,
};

export function useAgentSocket() {
  const [state, setState] = useState<AgentState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;

    function connect() {
      if (disposed) return;
      if (wsRef.current?.readyState === WebSocket.OPEN) return;

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setState((s) => ({ ...s, connected: true, error: null }));
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false, analyzing: false }));
        if (!disposed) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        setState((s) => ({ ...s, error: "WebSocket connection error" }));
      };

      ws.onmessage = (evt) => {
        try {
          const event: StreamEvent = JSON.parse(evt.data);
          setState((prev) => handleEvent(prev, event));
        } catch {
          // Ignore malformed messages
        }
      };
    }

    connect();

    return () => {
      disposed = true;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  const send = useCallback((msg: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const sendUpdate = useCallback(
    (code: string) => send({ action: "update", code }),
    [send]
  );

  const sendReturn = useCallback(
    (code: string, streamInterval = 30) => {
      setState((s) => ({
        ...s,
        analyzing: true,
        epochs: [],
        summary: null,
        architecture: null,
        error: null,
      }));
      send({ action: "return", code, stream_interval: streamInterval });
    },
    [send]
  );

  const sendCancel = useCallback(() => {
    send({ action: "cancel" });
    setState((s) => ({ ...s, analyzing: false }));
  }, [send]);

  const resetState = useCallback(() => {
    setState((s) => ({
      ...s,
      lintIssues: [],
      pendingFunctions: [],
      architecture: null,
      epochs: [],
      summary: null,
      events: [],
      analyzing: false,
      error: null,
    }));
  }, []);

  return { state, sendUpdate, sendReturn, sendCancel, resetState };
}

function handleEvent(prev: AgentState, event: StreamEvent): AgentState {
  const next = {
    ...prev,
    events: [...prev.events, event],
  };

  switch (event.event_type) {
    case "connected":
      return { ...next, connected: true };

    case "func_pending": {
      const func = event.data as unknown as PendingFunction;
      const existing = next.pendingFunctions.findIndex(
        (f) => f.name === func.name
      );
      const funcs = [...next.pendingFunctions];
      if (existing >= 0) {
        funcs[existing] = func;
      } else {
        funcs.push(func);
      }
      return { ...next, pendingFunctions: funcs };
    }

    case "lint_feedback":
      return {
        ...next,
        lintIssues: (event.data.issues as LintIssue[]) || [],
      };

    case "analysis_start":
      return { ...next, analyzing: true };

    case "architecture_detected":
      return {
        ...next,
        architecture: event.data as unknown as ArchitectureInfo,
      };

    case "epoch_prediction": {
      const metrics = event.data as unknown as EpochMetrics;
      return { ...next, epochs: [...next.epochs, metrics] };
    }

    case "training_summary":
      return {
        ...next,
        summary: event.data as unknown as TrainingSummary,
        analyzing: false,
      };

    case "error":
      return {
        ...next,
        error: (event.data.detail as string) || event.message,
        analyzing: false,
      };

    case "heartbeat":
      return next;

    default:
      return next;
  }
}
