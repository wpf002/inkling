"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { readSessionToken } from "@/lib/session";

const SCALE = [1, 2, 3, 4, 5] as const;
const SCALE_LABELS = ["Strongly disagree", "", "Neutral", "", "Strongly agree"];

export default function SelfReportPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  const itemsQuery = useQuery({
    queryKey: ["self-report-items"],
    queryFn: api.getSelfReportItems,
    enabled: token !== null,
  });

  const submit = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("no session");
      return api.submitSelfReport(token, {
        responses: Object.entries(responses).map(([item_id, response]) => ({
          item_id,
          response,
        })),
      });
    },
    onSuccess: () => router.push("/play"),
    onError: (e) => setError(e instanceof Error ? e.message : "request failed"),
  });

  const items = itemsQuery.data?.items ?? [];
  const answered = Object.keys(responses).length;
  const total = items.length;
  const allAnswered = total > 0 && answered === total;

  const progress = useMemo(
    () => (total === 0 ? 0 : Math.round((answered / total) * 100)),
    [answered, total],
  );

  if (token === null) return null;

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col gap-10 px-6 py-16">
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Ten questions first.
        </h1>
        <p className="text-sm leading-relaxed text-muted">
          What you say here is the baseline. Later, the game will compare it
          to what you actually do.
        </p>
        <div className="flex items-center gap-3 text-xs text-muted">
          <div className="h-1 flex-1 rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="tabular-nums">
            {answered} / {total}
          </span>
        </div>
      </div>

      {itemsQuery.isLoading && <p className="text-sm text-muted">Loading…</p>}
      {itemsQuery.error && (
        <p className="text-sm text-red-300">
          Failed to load items: {String(itemsQuery.error)}
        </p>
      )}

      <ol className="space-y-6">
        {items.map((item, i) => (
          <motion.li
            key={item.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.04 * i }}
            className="space-y-3 rounded-lg border border-white/10 px-4 py-4"
          >
            <p className="text-sm leading-relaxed">{item.prompt}</p>
            <div
              role="radiogroup"
              aria-label={item.prompt}
              className="flex items-center justify-between gap-2"
            >
              {SCALE.map((n, idx) => {
                const selected = responses[item.id] === n;
                return (
                  <button
                    type="button"
                    key={n}
                    role="radio"
                    aria-checked={selected}
                    aria-label={SCALE_LABELS[idx] || `${n}`}
                    onClick={() =>
                      setResponses((r) => ({ ...r, [item.id]: n }))
                    }
                    className={`flex-1 rounded-md border px-2 py-2 text-sm transition ${
                      selected
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-white/10 text-foreground/70 hover:border-accent/40"
                    }`}
                  >
                    {n}
                  </button>
                );
              })}
            </div>
            <div className="flex justify-between text-[11px] text-muted">
              <span>{SCALE_LABELS[0]}</span>
              <span>{SCALE_LABELS[4]}</span>
            </div>
          </motion.li>
        ))}
      </ol>

      {error && (
        <p className="rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <button
        type="button"
        disabled={!allAnswered || submit.isPending}
        onClick={() => submit.mutate()}
        className="self-start rounded-full bg-accent px-6 py-3 text-sm font-medium text-black transition disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-muted"
      >
        {submit.isPending ? "Saving…" : "Submit"}
      </button>
    </main>
  );
}
