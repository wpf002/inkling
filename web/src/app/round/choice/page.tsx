"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CountdownRing } from "@/components/round/CountdownRing";
import { Stage } from "@/components/round/Stage";
import { api } from "@/lib/api";
import { useEventCapture } from "@/lib/eventCapture";
import { RoundGamble } from "@/lib/schemas";
import { readSessionToken } from "@/lib/session";

const ROUND_ID = "choice";
const MOUSE_SAMPLE_INTERVAL_MS = 100; // 10 Hz

type Trial = {
  index: number;
  trial: string; // "{condition}:{gamble_id}"
  gamble: RoundGamble;
  condition: string;
};

function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function buildTrials(gambles: RoundGamble[], conditions: string[]): Trial[] {
  const blockOrder =
    Math.random() < 0.5
      ? [conditions[0], conditions[1]]
      : [conditions[1], conditions[0]];

  let i = 0;
  const trials: Trial[] = [];
  for (const cond of blockOrder) {
    for (const g of shuffle(gambles)) {
      trials.push({
        index: i,
        trial: `${cond}:${g.id}`,
        gamble: g,
        condition: cond,
      });
      i++;
    }
  }
  return trials;
}

export default function ChoiceRoundPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [trialIndex, setTrialIndex] = useState(0);
  const [shownAt, setShownAt] = useState<number>(0);

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  const gamblesQuery = useQuery({
    queryKey: ["round-gambles", ROUND_ID],
    queryFn: () => api.getRoundGambles(ROUND_ID),
    enabled: token !== null,
    staleTime: Infinity,
  });

  const trials = useMemo<Trial[] | null>(() => {
    if (!gamblesQuery.data) return null;
    return buildTrials(gamblesQuery.data.gambles, gamblesQuery.data.conditions);
  }, [gamblesQuery.data]);

  const { emit, flush } = useEventCapture(ROUND_ID, token);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current || !trials || !token) return;
    startedRef.current = true;
    emit("round_start", {
      condition_order: [trials[0].condition, trials[trials.length - 1].condition].filter(
        (c, i, a) => a.indexOf(c) === i,
      ),
      gambles_count: trials.length,
    });
  }, [trials, token, emit]);

  // Mark a trial shown.
  useEffect(() => {
    if (!trials) return;
    const t = trials[trialIndex];
    if (!t) return;
    const now = performance.now();
    setShownAt(now);
    emit("gamble_shown", {
      trial: t.trial,
      gamble_id: t.gamble.id,
      condition: t.condition,
      win: t.gamble.win,
      lose: t.gamble.lose,
    });
  }, [trialIndex, trials, emit]);

  // Throttled mouse capture.
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
        trial: t.trial,
        x: Math.round(e.clientX),
        y: Math.round(e.clientY),
      });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [trialIndex, trials, emit]);

  const advance = useCallback(
    async (cause: "choice" | "abandon") => {
      if (!trials) return;
      if (trialIndex < trials.length - 1) {
        setTrialIndex((i) => i + 1);
        return;
      }
      // Last trial — finish.
      await flush();
      if (!token) return;
      try {
        await api.postRoundComplete(token, ROUND_ID);
      } catch {
        // Reveal page will retry via getInferences.
      }
      router.push(`/reveal-stub?round=${ROUND_ID}&cause=${cause}`);
    },
    [trials, trialIndex, flush, token, router],
  );

  const onChoose = useCallback(
    (value: "take" | "decline") => {
      if (!trials) return;
      const t = trials[trialIndex];
      if (!t) return;
      const rt_ms = Math.max(0, Math.round(performance.now() - shownAt));
      emit("choice", {
        trial: t.trial,
        gamble_id: t.gamble.id,
        condition: t.condition,
        value,
        rt_ms,
      });
      void advance("choice");
    },
    [trials, trialIndex, shownAt, emit, advance],
  );

  const onAbandon = useCallback(() => {
    if (!trials) return;
    const t = trials[trialIndex];
    if (!t) return;
    const rt_ms = Math.max(0, Math.round(performance.now() - shownAt));
    emit("abandon", {
      trial: t.trial,
      gamble_id: t.gamble.id,
      condition: t.condition,
      rt_ms,
    });
    void advance("abandon");
  }, [trials, trialIndex, shownAt, emit, advance]);

  const onHover = useCallback(
    (button: "take" | "decline", phase: "enter" | "leave") => {
      if (!trials) return;
      const t = trials[trialIndex];
      if (!t) return;
      emit(`hover_${phase}`, {
        trial: t.trial,
        button,
      });
    },
    [trials, trialIndex, emit],
  );

  if (token === null) return null;
  if (gamblesQuery.isLoading || !trials) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading round…</p>
      </main>
    );
  }
  if (gamblesQuery.error) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-red-300">
          Failed to load round: {String(gamblesQuery.error)}
        </p>
      </main>
    );
  }

  const trial = trials[trialIndex];
  const hurried = trial.condition === "hurried";
  const hurryMs = gamblesQuery.data?.hurry_ms ?? 4000;

  return (
    <Stage
      title="Round 1 · Choice"
      trialIndex={trialIndex}
      totalTrials={trials.length}
      trialKey={trial.trial}
      meta={
        hurried ? (
          <CountdownRing
            key={trial.trial}
            durationMs={hurryMs}
            onExpire={onAbandon}
            size={48}
          />
        ) : null
      }
    >
      <div className="space-y-2 text-center">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          {hurried ? "Hurried — answer before the ring fills" : "Take your time"}
        </p>
        <p className="text-base text-foreground/80">A coin flip:</p>
        <p className="text-3xl font-semibold sm:text-4xl">
          win{" "}
          <span className="text-accent">${trial.gamble.win}</span> · lose{" "}
          <span className="text-red-300">${trial.gamble.lose}</span>
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <button
          type="button"
          onClick={() => onChoose("take")}
          onMouseEnter={() => onHover("take", "enter")}
          onMouseLeave={() => onHover("take", "leave")}
          className="flex-1 rounded-full border border-accent/60 bg-accent/10 px-6 py-4 text-base font-medium text-accent transition hover:bg-accent/20"
        >
          Take the bet
        </button>
        <button
          type="button"
          onClick={() => onChoose("decline")}
          onMouseEnter={() => onHover("decline", "enter")}
          onMouseLeave={() => onHover("decline", "leave")}
          className="flex-1 rounded-full border border-white/15 px-6 py-4 text-base font-medium text-foreground/80 transition hover:border-accent/40 hover:text-foreground"
        >
          Decline
        </button>
      </div>
    </Stage>
  );
}
