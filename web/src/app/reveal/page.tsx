"use client";

import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { AnimatePresence } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LevelShell } from "@/components/reveal/LevelShell";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { InferenceData } from "@/lib/schemas";
import { readSessionToken } from "@/lib/session";
import { Level1 } from "./levels/Level1";
import { Level2 } from "./levels/Level2";
import { Level3 } from "./levels/Level3";
import { Level4 } from "./levels/Level4";
import { Level5 } from "./levels/Level5";
import { Level6 } from "./levels/Level6";
import { Level7 } from "./levels/Level7";

const ROUNDS = ["choice", "pursuit", "trust", "memory", "read", "dilemma"];
const TOTAL_LEVELS = 7;
const VISITED_KEY = "inkling.reveal.visited";

export default function RevealPage() {
  return (
    <Suspense fallback={null}>
      <RevealInner />
    </Suspense>
  );
}

function RevealInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [token, setToken] = useState<string | null>(null);
  const startRef = useRef<number>(Date.now());

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  // Gate: the reveal is locked until you've finished all 6 rounds. If
  // next_round is anything other than null, send you back to /play so
  // you can't manually navigate to ?level=4 and stare at half-rendered
  // cards. The session endpoint is the source of truth here.
  const sessionStateQuery = useQuery({
    queryKey: ["session", token],
    queryFn: () => api.getSession(token!),
    enabled: token !== null,
  });
  const gameComplete = sessionStateQuery.data?.next_round === null;
  useEffect(() => {
    if (!sessionStateQuery.data) return;
    if (sessionStateQuery.data.next_round !== null) {
      router.replace("/play");
    }
  }, [sessionStateQuery.data, router]);

  const levelParam = parseInt(params.get("level") ?? "1", 10);
  const level = Math.min(Math.max(1, isNaN(levelParam) ? 1 : levelParam), TOTAL_LEVELS);

  const setLevel = useCallback(
    (n: number) => {
      const next = Math.min(Math.max(1, n), TOTAL_LEVELS);
      router.push(`/reveal?level=${next}`);
    },
    [router],
  );

  useEffect(() => {
    if (!token) return;
    try {
      const raw = localStorage.getItem(VISITED_KEY);
      const visited: number[] = raw ? JSON.parse(raw) : [];
      if (!visited.includes(level)) {
        visited.push(level);
        localStorage.setItem(VISITED_KEY, JSON.stringify(visited));
      }
    } catch {
      // localStorage unavailable; non-fatal.
    }
  }, [level, token]);

  // Round inferences (all 17). Drives Levels 1-3, 5, 6, 7.
  const inferenceQueries = useQueries({
    queries: ROUNDS.map((r) => ({
      queryKey: ["inferences", token, r],
      queryFn: () => api.getInferences(token!, r),
      enabled: token !== null && gameComplete,
    })),
  });

  const allInferences: InferenceData[] = useMemo(() => {
    const acc: InferenceData[] = [];
    for (const q of inferenceQueries) {
      if (q.data?.inferences) acc.push(...q.data.inferences);
    }
    return acc;
  }, [inferenceQueries]);

  // Level 1: stated vs revealed.
  const statedVsRevealedQuery = useQuery({
    queryKey: ["stated-vs-revealed", token],
    queryFn: () => api.postStatedVsRevealed(token!),
    enabled: token !== null && gameComplete,
    staleTime: Infinity,
  });

  // Level 4: overreach. Fires once the player reaches Level 4 — until
  // then we don't burn the cost. Idempotency makes re-entry safe.
  const [overreachStarted, setOverreachStarted] = useState(false);
  useEffect(() => {
    if (level >= 4) setOverreachStarted(true);
  }, [level]);

  const overreachQuery = useQuery({
    queryKey: ["overreach", token],
    queryFn: () => api.postOverreach(token!),
    enabled: token !== null && overreachStarted && gameComplete,
    retry: false,
    staleTime: Infinity,
  });

  // Level 5: broker pricing.
  const brokerPricingQuery = useQuery({
    queryKey: ["broker-pricing", token, overreachQuery.data?.cached],
    queryFn: () => api.postBrokerPricing(token!),
    enabled: token !== null && level >= 5 && gameComplete,
    staleTime: Infinity,
  });

  // Level 6: targeting.
  const targetingQuery = useQuery({
    queryKey: ["targeting", token],
    queryFn: () => api.getTargeting(token!),
    enabled: token !== null && level >= 6 && gameComplete,
    staleTime: Infinity,
  });

  // Log level-entry events.
  const eventMutation = useMutation({
    mutationFn: (n: number) =>
      api.postRevealEvent(token!, {
        event_type: "reveal_level_entered",
        payload: { level: n },
        t_ms: Math.max(0, Date.now() - startRef.current),
      }),
  });
  useEffect(() => {
    if (!token || !gameComplete) return;
    eventMutation.mutate(level);
    // Fire only when level changes; eventMutation is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level, token, gameComplete]);

  if (token === null) return null;

  // While the session check is in flight, render nothing — avoids a
  // flash of the reveal before the redirect to /play.
  if (sessionStateQuery.isLoading || !gameComplete) return null;

  const next = () => setLevel(level + 1);

  return (
    <AnimatePresence mode="wait">
      {level === 1 && (
        <Level1
          key="L1"
          inference={statedVsRevealedQuery.data?.inference ?? null}
          onContinue={next}
        />
      )}
      {level === 2 && (
        <Level2 key="L2" inferences={allInferences} onContinue={next} />
      )}
      {level === 3 && (
        <Level3 key="L3" inferences={allInferences} onContinue={next} />
      )}
      {level === 4 && (
        <Level4
          key="L4"
          inference={overreachQuery.data?.inference ?? null}
          isLoading={overreachQuery.isLoading}
          error={
            overreachQuery.error
              ? overreachErrorMessage(overreachQuery.error)
              : null
          }
          onContinue={next}
        />
      )}
      {level === 5 && (
        <Level5
          key="L5"
          inference={brokerPricingQuery.data?.inference ?? null}
          sessionToken={token}
          onContinue={next}
        />
      )}
      {level === 6 && (
        <Level6
          key="L6"
          data={targetingQuery.data ?? null}
          isLoading={targetingQuery.isLoading}
          onContinue={next}
        />
      )}
      {level === 7 && (
        <Level7
          key="L7"
          inferences={allInferences}
          overreach={overreachQuery.data?.inference ?? null}
          onContinue={() => router.push("/")}
        />
      )}
    </AnimatePresence>
  );
}

function overreachErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) {
      return "Too many requests right now. Try again in a few minutes.";
    }
    if (err.status === 503) {
      const detail = (err.detail as { detail?: string })?.detail
        ?? "This part is offline right now.";
      return detail;
    }
  }
  return "Couldn't load this one. Try again in a minute.";
}
