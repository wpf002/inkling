"use client";

import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Consent } from "@/lib/schemas";
import { newSessionToken, writeSessionToken } from "@/lib/session";

type ConsentField = keyof Consent;

const ITEMS: { key: ConsentField; title: string; body: string }[] = [
  {
    key: "gameplay",
    title: "Gameplay choices and timing",
    body: "What you pick, when you pick it, how long you take. This is the core data the game makes inferences from.",
  },
  {
    key: "interaction_patterns",
    title: "Cursor and interaction patterns",
    body: "Where you hover, where you hesitate, when you back out of a choice. Used to infer attention and conflict.",
  },
  {
    key: "self_report",
    title: "Self-report responses",
    body: "Your answers to the 10 questions before the game. Used as a baseline to compare against what the game infers.",
  },
  {
    key: "retain_profile_7d",
    title: "Retain my inferred profile for 7 days",
    body: "So you can come back and re-read what the game said about you. Opt out and we destroy everything when you close the tab.",
  },
];

const RESEARCH_KEY: ConsentField = "research_aggregate";

export default function ConsentPage() {
  const router = useRouter();
  const [consent, setConsent] = useState<Consent>({
    gameplay: true,
    interaction_patterns: true,
    self_report: true,
    retain_profile_7d: true,
    research_aggregate: false,
  });
  const [error, setError] = useState<string | null>(null);

  const submit = useMutation({
    mutationFn: async () => {
      const token = newSessionToken();
      const res = await api.createSession({
        consent,
        age_attested: true,
        anonymous_token: token,
      });
      writeSessionToken(res.anonymous_token);
      return res;
    },
    onSuccess: () => router.push("/self-report"),
    onError: (e) => setError(e instanceof Error ? e.message : "request failed"),
  });

  const required: ConsentField[] = ["gameplay", "self_report"];
  const canSubmit = required.every((k) => consent[k]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col gap-10 px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="space-y-3"
      >
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          What you&apos;re agreeing to
        </h1>
        <p className="text-sm leading-relaxed text-muted">
          Each item is its own decision. None of them are pre-checked for things
          we don&apos;t actually need. You can delete your session any time.
        </p>
      </motion.div>

      <ul className="space-y-3">
        {ITEMS.map((item, i) => (
          <motion.li
            key={item.key}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.05 * i }}
          >
            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-white/10 px-4 py-4 transition hover:border-accent/60">
              <input
                type="checkbox"
                checked={consent[item.key]}
                onChange={(e) =>
                  setConsent((c) => ({ ...c, [item.key]: e.target.checked }))
                }
                className="mt-1 accent-accent"
              />
              <span className="flex-1 space-y-1">
                <span className="block text-sm font-medium">{item.title}</span>
                <span className="block text-sm leading-relaxed text-muted">
                  {item.body}
                </span>
              </span>
            </label>
          </motion.li>
        ))}

        <motion.li
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.05 * ITEMS.length }}
        >
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-dashed border-white/10 px-4 py-4 transition hover:border-accent/60">
            <input
              type="checkbox"
              checked={consent[RESEARCH_KEY]}
              onChange={(e) =>
                setConsent((c) => ({ ...c, [RESEARCH_KEY]: e.target.checked }))
              }
              className="mt-1 accent-accent"
            />
            <span className="flex-1 space-y-1">
              <span className="block text-sm font-medium">
                Anonymous aggregate research use
                <span className="ml-2 rounded-full bg-white/5 px-2 py-0.5 text-xs font-normal text-muted">
                  optional, will be asked again post-reveal
                </span>
              </span>
              <span className="block text-sm leading-relaxed text-muted">
                Off by default. Your individual responses stay private either
                way; this just lets us include de-identified counts in research
                summaries.
              </span>
            </span>
          </label>
        </motion.li>
      </ul>

      {error && (
        <p className="rounded-md border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <div className="flex items-center gap-4">
        <button
          type="button"
          disabled={!canSubmit || submit.isPending}
          onClick={() => submit.mutate()}
          className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-black transition disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-muted"
        >
          {submit.isPending ? "Saving…" : "I agree, continue"}
        </button>
        {!canSubmit && (
          <p className="text-xs text-muted">
            Gameplay and self-report consent are required to play.
          </p>
        )}
      </div>
    </main>
  );
}
