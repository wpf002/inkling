"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Stage } from "@/components/round/Stage";
import { api } from "@/lib/api";
import { useEventCapture } from "@/lib/eventCapture";
import { readSessionToken } from "@/lib/session";

const ROUND_ID = "read";

type Option = {
  id: string;
  text: string;
  tags: string[];
};

type Scenario = {
  id: string;
  scenario: string;
  options: Option[];
};

type ReadContent = {
  round_id: string;
  scenarios: Scenario[];
};

function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export default function ReadRoundPage() {
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
    queryFn: () => api.getRoundContent<ReadContent>(ROUND_ID),
    enabled: token !== null,
    staleTime: Infinity,
  });

  const scenarios = useMemo<Scenario[] | null>(() => {
    if (!contentQuery.data) return null;
    return contentQuery.data.scenarios.map((s) => ({
      ...s,
      options: shuffle(s.options),
    }));
  }, [contentQuery.data]);

  const { emit, flush } = useEventCapture(ROUND_ID, token);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current || !scenarios || !token) return;
    startedRef.current = true;
    emit("round_start", { scenarios_count: scenarios.length });
  }, [scenarios, token, emit]);

  useEffect(() => {
    if (!scenarios) return;
    const s = scenarios[trialIndex];
    if (!s) return;
    setShownAt(performance.now());
    emit("scenario_shown", {
      scenario_id: s.id,
      index: trialIndex,
    });
  }, [trialIndex, scenarios, emit]);

  const advance = useCallback(async () => {
    if (!scenarios) return;
    if (trialIndex < scenarios.length - 1) {
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
  }, [scenarios, trialIndex, flush, token, router]);

  const onSelect = useCallback(
    (s: Scenario, opt: Option) => {
      const rt = Math.max(0, Math.round(performance.now() - shownAt));
      emit("option_selected", {
        scenario_id: s.id,
        index: trialIndex,
        option_id: opt.id,
        tags: opt.tags,
        rt_ms: rt,
      });
      void advance();
    },
    [shownAt, emit, advance, trialIndex],
  );

  const onHover = useCallback(
    (s: Scenario, opt: Option, phase: "enter" | "leave") => {
      emit(`option_hover_${phase}`, {
        scenario_id: s.id,
        option_id: opt.id,
      });
    },
    [emit],
  );

  if (token === null) return null;
  if (contentQuery.isLoading || !scenarios) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading round…</p>
      </main>
    );
  }
  const s = scenarios[trialIndex];

  return (
    <Stage
      title="Round 5 · Read"
      trialIndex={trialIndex}
      totalTrials={scenarios.length}
      trialKey={s.id}
    >
      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          What's the most likely read?
        </p>
        <p className="text-lg leading-relaxed">{s.scenario}</p>
      </div>

      <div className="flex flex-col gap-3">
        {s.options.map((opt) => (
          <button
            type="button"
            key={opt.id}
            onClick={() => onSelect(s, opt)}
            onMouseEnter={() => onHover(s, opt, "enter")}
            onMouseLeave={() => onHover(s, opt, "leave")}
            className="rounded-lg border border-white/15 px-4 py-3 text-left text-sm leading-relaxed transition hover:border-accent/60 hover:bg-accent/5"
          >
            {opt.text}
          </button>
        ))}
      </div>
    </Stage>
  );
}
