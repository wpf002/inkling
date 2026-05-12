"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CountdownRing } from "@/components/round/CountdownRing";
import { Stage } from "@/components/round/Stage";
import { api } from "@/lib/api";
import { useEventCapture } from "@/lib/eventCapture";
import { readSessionToken } from "@/lib/session";

const ROUND_ID = "dilemma";

type DilemmaOption = {
  id: string;
  text: string;
};

type Dilemma = {
  id: string;
  type: "personal" | "impersonal";
  hurried: boolean;
  scenario: string;
  option_util: DilemmaOption;
  option_deon: DilemmaOption;
};

type DilemmaContent = {
  round_id: string;
  hurry_ms: number;
  dilemmas: Dilemma[];
};

export default function DilemmaRoundPage() {
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

  const contentQuery = useQuery({
    queryKey: ["round-content", ROUND_ID],
    queryFn: () => api.getRoundContent<DilemmaContent>(ROUND_ID),
    enabled: token !== null,
    staleTime: Infinity,
  });

  const dilemmas = useMemo<Dilemma[] | null>(() => {
    if (!contentQuery.data) return null;
    return contentQuery.data.dilemmas;
  }, [contentQuery.data]);

  const { emit, flush } = useEventCapture(ROUND_ID, token);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current || !dilemmas || !token) return;
    startedRef.current = true;
    emit("round_start", { dilemmas_count: dilemmas.length });
  }, [dilemmas, token, emit]);

  useEffect(() => {
    if (!dilemmas) return;
    const d = dilemmas[trialIndex];
    if (!d) return;
    setShownAt(performance.now());
    emit("dilemma_shown", {
      dilemma_id: d.id,
      type: d.type,
      hurried: d.hurried,
    });
  }, [trialIndex, dilemmas, emit]);

  const advance = useCallback(async () => {
    if (!dilemmas) return;
    if (trialIndex < dilemmas.length - 1) {
      setTrialIndex((i) => i + 1);
      return;
    }
    await flush();
    if (!token) return;
    try {
      await api.postRoundComplete(token, ROUND_ID);
    } catch {
      /* /play retries */
    }
    router.push("/play");
  }, [dilemmas, trialIndex, flush, token, router]);

  const onSelect = useCallback(
    (d: Dilemma, kind: "utilitarian" | "deontological") => {
      const rt = Math.max(0, Math.round(performance.now() - shownAt));
      emit("option_selected", {
        dilemma_id: d.id,
        type: d.type,
        hurried: d.hurried,
        selected: kind,
        option_id: kind === "utilitarian" ? d.option_util.id : d.option_deon.id,
        rt_ms: rt,
      });
      void advance();
    },
    [shownAt, emit, advance],
  );

  const onHover = useCallback(
    (d: Dilemma, kind: "utilitarian" | "deontological", phase: "enter" | "leave") => {
      emit(`option_hover_${phase}`, {
        dilemma_id: d.id,
        selected: kind,
      });
    },
    [emit],
  );

  const onAbandon = useCallback(() => {
    if (!dilemmas) return;
    const d = dilemmas[trialIndex];
    if (!d) return;
    const rt = Math.max(0, Math.round(performance.now() - shownAt));
    emit("abandon", {
      dilemma_id: d.id,
      type: d.type,
      hurried: d.hurried,
      rt_ms: rt,
    });
    void advance();
  }, [dilemmas, trialIndex, shownAt, emit, advance]);

  if (token === null) return null;
  if (contentQuery.isLoading || !dilemmas || !contentQuery.data) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading round…</p>
      </main>
    );
  }

  const d = dilemmas[trialIndex];
  const hurryMs = contentQuery.data.hurry_ms;

  return (
    <Stage
      title="Round 6 · Dilemma"
      trialIndex={trialIndex}
      totalTrials={dilemmas.length}
      trialKey={d.id}
      meta={
        d.hurried ? (
          <CountdownRing
            key={d.id}
            durationMs={hurryMs}
            onExpire={onAbandon}
            size={48}
          />
        ) : null
      }
    >
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          {d.hurried ? "Decide before the ring fills" : "Take your time"}
        </p>
        <p className="text-base leading-relaxed">{d.scenario}</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <button
          type="button"
          onClick={() => onSelect(d, "utilitarian")}
          onMouseEnter={() => onHover(d, "utilitarian", "enter")}
          onMouseLeave={() => onHover(d, "utilitarian", "leave")}
          className="flex-1 rounded-lg border border-accent/60 bg-accent/10 px-4 py-4 text-sm font-medium leading-relaxed text-accent transition hover:bg-accent/20"
        >
          {d.option_util.text}
        </button>
        <button
          type="button"
          onClick={() => onSelect(d, "deontological")}
          onMouseEnter={() => onHover(d, "deontological", "enter")}
          onMouseLeave={() => onHover(d, "deontological", "leave")}
          className="flex-1 rounded-lg border border-white/15 px-4 py-4 text-sm font-medium leading-relaxed text-foreground/80 transition hover:border-accent/40 hover:text-foreground"
        >
          {d.option_deon.text}
        </button>
      </div>
    </Stage>
  );
}
