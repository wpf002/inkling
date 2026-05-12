"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Stage } from "@/components/round/Stage";
import { api } from "@/lib/api";
import { useEventCapture } from "@/lib/eventCapture";
import { readSessionToken } from "@/lib/session";

const ROUND_ID = "trust";

type TrustNpc = {
  id: string;
  display_name: string;
  hint: string;
  return_rate_mean: number;
  return_rate_jitter: number;
  persona: string;
};

type TrustTrial = {
  trial_id: string;
  npc_id: string;
  first: boolean;
};

type TrustContent = {
  round_id: string;
  endowment: number;
  multiplier: number;
  npcs: TrustNpc[];
  trials: TrustTrial[];
};

function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function counterbalance(trials: TrustTrial[], npcOrder: string[]): TrustTrial[] {
  // Re-emit two passes of [firsts in npcOrder, then seconds in npcOrder].
  const firsts = npcOrder.map((id) => trials.find((t) => t.npc_id === id && t.first)!);
  const seconds = npcOrder.map((id) => trials.find((t) => t.npc_id === id && !t.first)!);
  return [...firsts, ...seconds];
}

function simulateReturn(npc: TrustNpc, sent: number, multiplier: number): number {
  if (sent <= 0) return 0;
  const tripled = sent * multiplier;
  const noise = (Math.random() * 2 - 1) * npc.return_rate_jitter;
  const rate = Math.max(0, Math.min(1, npc.return_rate_mean + noise));
  return Math.round(tripled * rate);
}

export default function TrustRoundPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [trialIndex, setTrialIndex] = useState(0);
  const [send, setSend] = useState(5);
  const [outcome, setOutcome] = useState<{ received: number } | null>(null);

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
    queryFn: () => api.getRoundContent<TrustContent>(ROUND_ID),
    enabled: token !== null,
    staleTime: Infinity,
  });

  const content = contentQuery.data ?? null;
  const npcsById = useMemo(() => {
    const out: Record<string, TrustNpc> = {};
    if (!content) return out;
    for (const n of content.npcs) out[n.id] = n;
    return out;
  }, [content]);

  const trials = useMemo<TrustTrial[] | null>(() => {
    if (!content) return null;
    const order = shuffle(content.npcs.map((n) => n.id));
    return counterbalance(content.trials, order);
  }, [content]);

  const { emit, flush } = useEventCapture(ROUND_ID, token);

  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current || !content || !trials || !token) return;
    startedRef.current = true;
    emit("round_start", {
      npc_order: trials.filter((t) => t.first).map((t) => t.npc_id),
    });
  }, [content, trials, token, emit]);

  useEffect(() => {
    if (!trials || !content) return;
    const trial = trials[trialIndex];
    if (!trial) return;
    setSend(5);
    setOutcome(null);
    const npc = npcsById[trial.npc_id];
    if (trial.first) {
      emit("npc_introduced", {
        trial_id: trial.trial_id,
        npc_id: trial.npc_id,
        persona: npc.persona,
      });
    }
    emit("trial_shown", {
      trial_id: trial.trial_id,
      npc_id: trial.npc_id,
      first: trial.first,
    });
  }, [trialIndex, trials, content, npcsById, emit]);

  const onSend = useCallback(() => {
    if (!trials || !content) return;
    const trial = trials[trialIndex];
    if (!trial) return;
    const npc = npcsById[trial.npc_id];
    emit("send_amount", {
      trial_id: trial.trial_id,
      npc_id: trial.npc_id,
      amount: send,
    });
    const received = simulateReturn(npc, send, content.multiplier);
    setOutcome({ received });
    emit("outcome_revealed", {
      trial_id: trial.trial_id,
      npc_id: trial.npc_id,
      received,
      sent: send,
    });
  }, [trials, content, trialIndex, npcsById, send, emit]);

  const onContinue = useCallback(async () => {
    if (!trials) return;
    if (trialIndex < trials.length - 1) {
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
  }, [trials, trialIndex, flush, token, router]);

  if (token === null) return null;
  if (contentQuery.isLoading || !trials || !content) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading round…</p>
      </main>
    );
  }

  const trial = trials[trialIndex];
  const npc = npcsById[trial.npc_id];

  return (
    <Stage
      title="Round 3 · Trust"
      trialIndex={trialIndex}
      totalTrials={trials.length}
      trialKey={trial.trial_id}
    >
      <div className="space-y-2 text-center">
        <p className="text-xs uppercase tracking-[0.18em] text-muted">
          You have ${content.endowment}. Send any amount.
          Whatever you send is tripled. The other player keeps or shares.
        </p>
      </div>

      <div className="space-y-1 rounded-lg border border-white/10 px-5 py-4 text-center">
        <p className="text-2xl font-semibold tracking-tight">{npc.display_name}</p>
        {trial.first && (
          <p className="text-xs italic text-muted">{npc.hint}</p>
        )}
      </div>

      {outcome === null ? (
        <div className="space-y-5">
          <div className="space-y-2">
            <label className="flex items-center justify-between text-sm text-muted">
              <span>Send</span>
              <span className="text-foreground/80 tabular-nums">${send}</span>
            </label>
            <input
              type="range"
              min={0}
              max={content.endowment}
              value={send}
              onChange={(e) => setSend(Number(e.target.value))}
              className="w-full accent-cyan-400"
            />
          </div>
          <button
            type="button"
            onClick={onSend}
            className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-black transition hover:opacity-90"
          >
            Send ${send}
          </button>
        </div>
      ) : (
        <div className="space-y-5 text-center">
          <p className="text-sm text-muted">
            You sent ${send}. They received ${send * content.multiplier} and returned…
          </p>
          <p className="text-4xl font-semibold tracking-tight text-accent">
            ${outcome.received}
          </p>
          <button
            type="button"
            onClick={onContinue}
            className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-black transition hover:opacity-90"
          >
            Continue
          </button>
        </div>
      )}
    </Stage>
  );
}
