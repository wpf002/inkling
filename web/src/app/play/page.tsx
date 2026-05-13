"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { readSessionToken } from "@/lib/session";

const ROUND_TITLES: Record<string, string> = {
  choice: "Choice",
  pursuit: "Pursuit",
  trust: "Trust",
  memory: "Memory",
  read: "Read",
  dilemma: "Dilemma",
};

const TOTAL_ROUNDS = 6;

export default function PlayPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  const sessionQuery = useQuery({
    queryKey: ["session", token],
    queryFn: () => api.getSession(token!),
    enabled: token !== null,
  });

  useEffect(() => {
    if (!sessionQuery.data) return;
    if (sessionQuery.data.next_round === null) {
      router.replace("/reveal");
    }
  }, [sessionQuery.data, router]);

  if (token === null || sessionQuery.isLoading || !sessionQuery.data) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-2xl items-center justify-center px-6 py-16">
        <p className="text-sm text-muted">Loading…</p>
      </main>
    );
  }

  const { next_round, completed_rounds } = sessionQuery.data;
  if (next_round === null) return null;

  const roundIndex = completed_rounds.length + 1;

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col items-center justify-center gap-10 px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-3 text-center"
      >
        <p className="text-xs uppercase tracking-[0.18em] text-accent">
          Round {roundIndex} of {TOTAL_ROUNDS}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {ROUND_TITLES[next_round] ?? next_round}
        </h1>
        <p className="text-sm leading-relaxed text-muted">
          {completed_rounds.length === 0
            ? "Six short rounds. They don't add up to one score."
            : "Up next."}
        </p>
      </motion.div>

      <button
        type="button"
        onClick={() => router.push(`/round/${next_round}`)}
        className="rounded-full bg-accent px-8 py-3 text-sm font-medium text-black transition hover:opacity-90"
      >
        Begin
      </button>

      <div className="flex items-center gap-2 text-[11px] text-muted">
        {Array.from({ length: TOTAL_ROUNDS }).map((_, i) => {
          const filled = i < completed_rounds.length;
          const current = i === completed_rounds.length;
          return (
            <span
              key={i}
              className={`h-1.5 w-8 rounded-full ${
                filled
                  ? "bg-accent"
                  : current
                    ? "bg-accent/50"
                    : "bg-white/10"
              }`}
            />
          );
        })}
      </div>
    </main>
  );
}
