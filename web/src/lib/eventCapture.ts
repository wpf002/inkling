"use client";

import { useCallback, useEffect, useRef } from "react";
import { api } from "./api";

const FLUSH_INTERVAL_MS = 2000;
const FLUSH_BATCH_SIZE = 20;

export type RoundEvent = {
  event_type: string;
  payload: Record<string, unknown>;
  t_ms: number;
};

export type EventCapture = {
  emit: (event_type: string, payload?: Record<string, unknown>) => void;
  flush: () => Promise<void>;
};

/**
 * Round-agnostic event capture. Queues client-side; auto-flushes every
 * FLUSH_INTERVAL_MS or every FLUSH_BATCH_SIZE events. Stamps each event
 * with t_ms = ms since hook mount.
 */
export function useEventCapture(round: string, sessionToken: string | null): EventCapture {
  const queueRef = useRef<RoundEvent[]>([]);
  const inFlightRef = useRef<Promise<void> | null>(null);
  const startRef = useRef<number>(typeof performance !== "undefined" ? performance.now() : 0);
  const tokenRef = useRef<string | null>(sessionToken);
  const roundRef = useRef<string>(round);

  useEffect(() => {
    tokenRef.current = sessionToken;
  }, [sessionToken]);

  useEffect(() => {
    roundRef.current = round;
  }, [round]);

  const sendBatch = useCallback(async () => {
    const token = tokenRef.current;
    if (!token) return;
    const queue = queueRef.current;
    if (queue.length === 0) return;
    const batch = queue.splice(0, queue.length);
    try {
      await api.postRoundEvents(token, roundRef.current, batch);
    } catch {
      // Re-queue at the front so a transient failure doesn't drop events.
      queueRef.current.unshift(...batch);
    }
  }, []);

  const flush = useCallback(async (): Promise<void> => {
    if (inFlightRef.current) {
      await inFlightRef.current;
    }
    const p = sendBatch();
    inFlightRef.current = p;
    try {
      await p;
    } finally {
      inFlightRef.current = null;
    }
  }, [sendBatch]);

  const emit = useCallback(
    (event_type: string, payload: Record<string, unknown> = {}) => {
      const now = typeof performance !== "undefined" ? performance.now() : Date.now();
      const t_ms = Math.max(0, Math.round(now - startRef.current));
      queueRef.current.push({ event_type, payload, t_ms });
      if (queueRef.current.length >= FLUSH_BATCH_SIZE) {
        void flush();
      }
    },
    [flush],
  );

  useEffect(() => {
    const interval = window.setInterval(() => {
      void flush();
    }, FLUSH_INTERVAL_MS);
    return () => {
      window.clearInterval(interval);
      void flush();
    };
  }, [flush]);

  return { emit, flush };
}
