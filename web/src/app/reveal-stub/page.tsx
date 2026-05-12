"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { InferenceData } from "@/lib/schemas";
import { readSessionToken } from "@/lib/session";

const DEFAULT_ROUND = "choice";

const CONSTRUCT_LABEL: Record<string, string> = {
  loss_aversion: "Loss aversion",
  risk_tolerance: "Risk tolerance",
  stress_response: "Stress response",
};

function tierLabel(tier: string): string {
  if (tier === "high") return "High confidence";
  if (tier === "medium") return "Medium confidence";
  return "Overreach";
}

function formatValue(inf: InferenceData): { headline: string; sub?: string } {
  if (inf.construct === "loss_aversion") {
    const lambda = Number(inf.value.lambda ?? 0);
    return {
      headline: `λ = ${lambda.toFixed(2)}`,
      sub: "Losses feel about this many times worse than gains of the same size.",
    };
  }
  if (inf.construct === "risk_tolerance") {
    const overall = Number(inf.value.overall_take_rate ?? 0);
    const u = Number(inf.value.unhurried ?? 0);
    const h = Number(inf.value.hurried ?? 0);
    return {
      headline: `${Math.round(overall * 100)}% take rate`,
      sub: `Unhurried ${Math.round(u * 100)}% · Hurried ${Math.round(h * 100)}%.`,
    };
  }
  if (inf.construct === "stress_response") {
    const td = Number(inf.value.take_rate_delta ?? 0);
    const sign = td > 0 ? "+" : "";
    return {
      headline: `${sign}${(td * 100).toFixed(0)} pp under time pressure`,
      sub: "Change in your take-rate when the clock is on.",
    };
  }
  return { headline: JSON.stringify(inf.value) };
}

function ConfidenceBand({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="space-y-1">
      <div className="h-1 w-full rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[11px] tabular-nums text-muted">
        confidence {pct.toFixed(0)}%
      </p>
    </div>
  );
}

export default function RevealStubPage() {
  const router = useRouter();
  const params = useSearchParams();
  const round = params.get("round") ?? DEFAULT_ROUND;
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  const inferences = useQuery({
    queryKey: ["inferences", token, round],
    queryFn: () => api.getInferences(token!, round),
    enabled: token !== null,
  });

  if (token === null) return null;

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col gap-10 px-6 py-16">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.18em] text-accent">
          Reveal · Round {round}
        </p>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Here&apos;s what the game inferred.
        </h1>
        <p className="text-sm leading-relaxed text-muted">
          Three reads from one round. Phase 2 starts here. More rounds coming.
        </p>
      </header>

      {inferences.isLoading && (
        <p className="text-sm text-muted">Scoring…</p>
      )}
      {inferences.error && (
        <p className="text-sm text-red-300">
          Failed to load inferences: {String(inferences.error)}
        </p>
      )}

      <ol className="space-y-4">
        {inferences.data?.inferences.map((inf, i) => {
          const fmt = formatValue(inf);
          return (
            <motion.li
              key={inf.construct}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.06 * i }}
              className="space-y-3 rounded-lg border border-white/10 px-5 py-5"
            >
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="text-base font-medium">
                  {CONSTRUCT_LABEL[inf.construct] ?? inf.construct}
                </h2>
                <span className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-muted">
                  {tierLabel(inf.tier)}
                </span>
              </div>
              <p className="text-2xl font-semibold tracking-tight text-foreground">
                {fmt.headline}
              </p>
              {fmt.sub && (
                <p className="text-sm leading-relaxed text-muted">{fmt.sub}</p>
              )}
              <ConfidenceBand value={inf.confidence} />
            </motion.li>
          );
        })}
      </ol>

      {inferences.data && inferences.data.inferences.length === 0 && (
        <p className="text-sm text-muted">
          No inferences yet — round events may still be in flight.
        </p>
      )}
    </main>
  );
}
