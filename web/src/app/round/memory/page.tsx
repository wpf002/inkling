"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Stage } from "@/components/round/Stage";
import { api } from "@/lib/api";
import { useEventCapture } from "@/lib/eventCapture";
import { readSessionToken } from "@/lib/session";

const ROUND_ID = "memory";

type MemoryConfig = {
  round_id: string;
  grid_size: number;
  grid_rows: number;
  grid_cols: number;
  start_span: number;
  trials_per_span: number;
  fail_threshold: number;
  stimulus_ms_per_block: number;
  interval_ms: number;
  max_span: number;
};

type TrialState = {
  trial_id: string;
  span: number;
  sequence: number[];
};

function randomSequence(span: number, gridSize: number): number[] {
  const cells: number[] = [];
  while (cells.length < span) {
    const c = Math.floor(Math.random() * gridSize);
    if (cells.length === 0 || cells[cells.length - 1] !== c) cells.push(c);
  }
  return cells;
}

type Phase = "showing" | "responding" | "done";

export default function MemoryRoundPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  const [trialNumber, setTrialNumber] = useState(0);
  const [span, setSpan] = useState(3);
  const [trialsAtSpan, setTrialsAtSpan] = useState(0);
  const [failsAtSpan, setFailsAtSpan] = useState(0);
  const [trial, setTrial] = useState<TrialState | null>(null);
  const [phase, setPhase] = useState<Phase>("showing");
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [response, setResponse] = useState<number[]>([]);
  const tapStartRef = useRef<number>(0);
  const tapRtsRef = useRef<number[]>([]);

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  const contentQuery = useQuery({
    queryKey: ["round-content", ROUND_ID],
    queryFn: () => api.getRoundContent<MemoryConfig>(ROUND_ID),
    enabled: token !== null,
    staleTime: Infinity,
  });

  const config = contentQuery.data ?? null;
  const grid = useMemo<number[]>(() => {
    if (!config) return [];
    return Array.from({ length: config.grid_size }, (_, i) => i);
  }, [config]);

  const { emit, flush } = useEventCapture(ROUND_ID, token);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current || !config || !token) return;
    startedRef.current = true;
    emit("round_start", {
      start_span: config.start_span,
      grid_size: config.grid_size,
    });
    setSpan(config.start_span);
  }, [config, token, emit]);

  // Create a new trial whenever span/trialNumber changes.
  useEffect(() => {
    if (!config) return;
    const tid = `m${trialNumber + 1}_s${span}_t${trialsAtSpan + 1}`;
    const seq = randomSequence(span, config.grid_size);
    setTrial({ trial_id: tid, span, sequence: seq });
    setPhase("showing");
    setResponse([]);
    tapRtsRef.current = [];
    emit("sequence_shown", {
      trial_id: tid,
      span,
      sequence: seq,
    });
  }, [trialNumber, span, trialsAtSpan, config, emit]);

  // Drive the show animation.
  useEffect(() => {
    if (!trial || !config || phase !== "showing") return;
    const seq = trial.sequence;
    const stimulusMs = config.stimulus_ms_per_block;
    const intervalMs = config.interval_ms;
    let i = 0;
    let cancelled = false;

    function step() {
      if (cancelled) return;
      if (i >= seq.length) {
        setActiveIndex(null);
        setPhase("responding");
        tapStartRef.current = performance.now();
        return;
      }
      setActiveIndex(seq[i]);
      window.setTimeout(() => {
        if (cancelled) return;
        setActiveIndex(null);
        window.setTimeout(() => {
          i += 1;
          step();
        }, intervalMs);
      }, stimulusMs);
    }
    step();
    return () => {
      cancelled = true;
    };
  }, [trial, config, phase]);

  const submitTrial = useCallback(
    async (correct: boolean) => {
      if (!trial || !config) return;
      emit("response", {
        trial_id: trial.trial_id,
        span: trial.span,
        response: response,
        correct,
        tap_rts_ms: tapRtsRef.current,
      });

      const newTrialsAtSpan = trialsAtSpan + 1;
      const newFailsAtSpan = correct ? 0 : failsAtSpan + 1;

      const failed = newFailsAtSpan >= config.fail_threshold;
      const spanDone = newTrialsAtSpan >= config.trials_per_span;

      if (failed || (spanDone && !correct && failsAtSpan + 1 >= config.fail_threshold)) {
        // Stop the round.
        setPhase("done");
        await flush();
        if (!token) return;
        try {
          await api.postRoundComplete(token, ROUND_ID);
        } catch {
          /* /play retries */
        }
        router.push("/play");
        return;
      }

      if (spanDone) {
        // Move up a span; reset counters.
        setSpan((s) => Math.min(s + 1, config.max_span));
        setTrialsAtSpan(0);
        setFailsAtSpan(0);
        setTrialNumber((n) => n + 1);
      } else {
        setTrialsAtSpan(newTrialsAtSpan);
        setFailsAtSpan(newFailsAtSpan);
        setTrialNumber((n) => n + 1);
      }
    },
    [
      trial,
      config,
      response,
      trialsAtSpan,
      failsAtSpan,
      flush,
      token,
      router,
      emit,
    ],
  );

  const onCellTap = useCallback(
    (cell: number) => {
      if (!trial || phase !== "responding") return;
      const rt = Math.max(0, Math.round(performance.now() - tapStartRef.current));
      tapStartRef.current = performance.now();
      tapRtsRef.current = [...tapRtsRef.current, rt];
      const next = [...response, cell];
      setResponse(next);
      if (next.length >= trial.sequence.length) {
        const correct = next.every((v, i) => v === trial.sequence[i]);
        void submitTrial(correct);
      }
    },
    [trial, phase, response, submitTrial],
  );

  if (token === null) return null;
  if (contentQuery.isLoading || !config || !trial) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading round…</p>
      </main>
    );
  }

  return (
    <Stage
      title="Round 4 · Memory"
      trialIndex={trialNumber}
      totalTrials={Math.max(trialNumber + 1, 6)}
      trialKey={trial.trial_id}
    >
      <div className="space-y-2 text-center">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          {phase === "showing"
            ? "Watch the order."
            : phase === "responding"
              ? `Now tap the same order. (${response.length}/${trial.sequence.length})`
              : "Done."}
        </p>
        <p className="text-sm text-muted">Span {trial.span}</p>
      </div>

      <div
        className="mx-auto grid gap-3"
        style={{
          gridTemplateColumns: `repeat(${config.grid_cols}, 5rem)`,
          gridTemplateRows: `repeat(${config.grid_rows}, 5rem)`,
        }}
      >
        {grid.map((cell) => {
          const isActive = activeIndex === cell;
          const wasPressed = response.includes(cell);
          return (
            <button
              key={cell}
              type="button"
              onClick={() => onCellTap(cell)}
              disabled={phase !== "responding"}
              aria-label={`cell ${cell}`}
              className={`rounded-md border transition ${
                isActive
                  ? "border-accent bg-accent/40"
                  : phase === "responding"
                    ? wasPressed
                      ? "border-accent/60 bg-accent/10"
                      : "border-white/15 hover:border-accent/40"
                    : "border-white/10"
              }`}
              style={{ width: "5rem", height: "5rem" }}
            />
          );
        })}
      </div>
    </Stage>
  );
}
