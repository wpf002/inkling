"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Stage } from "@/components/round/Stage";
import { api } from "@/lib/api";
import { useEventCapture } from "@/lib/eventCapture";
import { readSessionToken } from "@/lib/session";

const ROUND_ID = "pursuit";
const MOUSE_SAMPLE_INTERVAL_MS = 100;
const STAGE_W = 560;
const STAGE_H = 380;

type PursuitTrial = {
  id: string;
  target_type: "valid" | "distractor";
  position: { x: number; y: number };
  window_ms: number;
};

type PursuitContent = {
  round_id: string;
  trials: PursuitTrial[];
  spike_indices: number[];
  inter_trial_ms: number;
  target_diameter_px: number;
};

export default function PursuitRoundPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [trialIndex, setTrialIndex] = useState(0);
  const [shownAt, setShownAt] = useState<number>(0);
  const [phase, setPhase] = useState<"showing" | "gap">("showing");

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
    queryFn: () => api.getRoundContent<PursuitContent>(ROUND_ID),
    enabled: token !== null,
    staleTime: Infinity,
  });

  const content = contentQuery.data ?? null;
  const trials = useMemo<PursuitTrial[] | null>(
    () => content?.trials ?? null,
    [content],
  );

  const { emit, flush } = useEventCapture(ROUND_ID, token);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current || !content || !token) return;
    startedRef.current = true;
    emit("round_start", {
      trials_count: content.trials.length,
      spike_indices: content.spike_indices,
    });
  }, [content, token, emit]);

  // Mark trial shown.
  useEffect(() => {
    if (!trials) return;
    const t = trials[trialIndex];
    if (!t) return;
    setPhase("showing");
    const now = performance.now();
    setShownAt(now);
    emit("trial_shown", {
      trial: t.id,
      index: trialIndex,
      target_type: t.target_type,
      window_ms: t.window_ms,
    });
  }, [trialIndex, trials, emit]);

  // Window timeout → miss.
  useEffect(() => {
    if (!trials) return;
    const t = trials[trialIndex];
    if (!t || phase !== "showing") return;
    const timer = window.setTimeout(() => {
      emit("miss", {
        trial: t.id,
        index: trialIndex,
        target_type: t.target_type,
        rt_ms: t.window_ms,
      });
      setPhase("gap");
    }, t.window_ms);
    return () => window.clearTimeout(timer);
  }, [trialIndex, phase, trials, emit]);

  // Inter-trial gap → advance.
  useEffect(() => {
    if (!trials || !content) return;
    if (phase !== "gap") return;
    const t = trials[trialIndex];
    if (!t) return;
    const interMs = content.inter_trial_ms;
    const timer = window.setTimeout(async () => {
      if (trialIndex < trials.length - 1) {
        setTrialIndex((i) => i + 1);
        return;
      }
      await flush();
      if (!token) return;
      try {
        await api.postRoundComplete(token, ROUND_ID);
      } catch {
        /* /play retries on next mount */
      }
      router.push("/play");
    }, interMs);
    return () => window.clearTimeout(timer);
  }, [phase, trials, trialIndex, content, flush, token, router]);

  // Mouse sample at 10Hz.
  useEffect(() => {
    if (!trials) return;
    const t = trials[trialIndex];
    if (!t) return;
    let last = 0;
    const onMove = (e: MouseEvent) => {
      const now = performance.now();
      if (now - last < MOUSE_SAMPLE_INTERVAL_MS) return;
      last = now;
      emit("mouse_sample", {
        trial: t.id,
        x: Math.round(e.clientX),
        y: Math.round(e.clientY),
      });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [trialIndex, trials, emit]);

  const onTargetClick = useCallback(() => {
    if (!trials) return;
    const t = trials[trialIndex];
    if (!t || phase !== "showing") return;
    const rt = Math.max(0, Math.round(performance.now() - shownAt));
    emit("click", {
      trial: t.id,
      index: trialIndex,
      target_type: t.target_type,
      rt_ms: rt,
    });
    setPhase("gap");
  }, [trials, trialIndex, phase, shownAt, emit]);

  if (token === null) return null;
  if (contentQuery.isLoading || !trials || !content) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading round…</p>
      </main>
    );
  }

  const trial = trials[trialIndex];
  const isValid = trial.target_type === "valid";
  const diameter = content.target_diameter_px;
  const left = trial.position.x * (STAGE_W - diameter);
  const top = trial.position.y * (STAGE_H - diameter);

  return (
    <Stage
      title="Round 2 · Pursuit"
      trialIndex={trialIndex}
      totalTrials={trials.length}
      trialKey={trial.id}
    >
      <div className="space-y-2 text-center">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          Tap the cyan dot. Ignore the gray ones.
        </p>
      </div>

      <div
        role="region"
        aria-label="pursuit target area"
        className="relative mx-auto rounded-lg border border-white/10 bg-white/[0.02]"
        style={{ width: STAGE_W, height: STAGE_H }}
      >
        {phase === "showing" && (
          <button
            type="button"
            onClick={onTargetClick}
            aria-label={isValid ? "valid target" : "decoy"}
            className="absolute rounded-full transition"
            style={{
              left,
              top,
              width: diameter,
              height: diameter,
              backgroundColor: isValid
                ? "var(--color-accent)"
                : "rgba(255,255,255,0.18)",
              boxShadow: isValid
                ? "0 0 20px rgba(34,211,238,0.45)"
                : "none",
            }}
          />
        )}
      </div>
    </Stage>
  );
}
