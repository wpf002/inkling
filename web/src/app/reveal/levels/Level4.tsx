"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useState } from "react";
import { LevelShell } from "@/components/reveal/LevelShell";
import { api } from "@/lib/api";
import { InferenceData } from "@/lib/schemas";

type BigFiveTrait = { score: number; blurb: string };
type OverreachValue = {
  big_five: { O: BigFiveTrait; C: BigFiveTrait; E: BigFiveTrait; A: BigFiveTrait; N: BigFiveTrait };
  political_values: string;
  life_history: string;
  consumer_profile: string;
};

type Dismantle = {
  big_five: { title: string; summary: string; citations: string[] };
  political_values: { title: string; summary: string; citations: string[] };
  life_history: { title: string; summary: string; citations: string[] };
  consumer_profile: { title: string; summary: string; citations: string[] };
  closing: string;
};

const TRAIT_NAME: Record<string, string> = {
  O: "Openness",
  C: "Conscientiousness",
  E: "Extraversion",
  A: "Agreeableness",
  N: "Neuroticism",
};

export function Level4({
  inference,
  isLoading,
  error,
  onContinue,
}: {
  inference: InferenceData | null;
  isLoading: boolean;
  error: string | null;
  onContinue: () => void;
}) {
  const [phase, setPhase] = useState<"fluent" | "dismantle">("fluent");
  const dismantleQuery = useQuery({
    queryKey: ["reveal-dismantle"],
    queryFn: () => api.getRevealDismantle() as Promise<Dismantle>,
    staleTime: Infinity,
  });

  if (isLoading) {
    return (
      <LevelShell level={4} title="Reading the room…" eyebrow="Level 4 of 8">
        <p className="text-sm text-muted">Working on this one — it takes about 10 to 20 seconds.</p>
      </LevelShell>
    );
  }

  if (error || !inference) {
    return (
      <LevelShell
        level={4}
        title="This one's offline right now"
        eyebrow="Level 4 of 8"
        onContinue={onContinue}
        continueLabel="Skip ahead"
      >
        <p className="text-sm leading-relaxed text-muted">
          {error ??
            "The big confident guess we'd normally make here isn't available for you right now. The rest still works — keep going."}
        </p>
      </LevelShell>
    );
  }

  const value = inference.value as OverreachValue;
  const dismantle = dismantleQuery.data;

  if (phase === "fluent") {
    return (
      <LevelShell
        level={4}
        title="What an LLM said about you"
        eyebrow="Level 4 of 8 · The big guess"
        onContinue={() => setPhase("dismantle")}
        continueLabel="Now show me how it really got there"
      >
        <p className="text-sm leading-relaxed text-muted">
          What follows is written in the voice a data broker would use to
          sell you to advertisers. No badges, no confidence bars. This is
          what confident profiling sounds like when nobody's asking how
          it got there.
        </p>

        <FluentBlock title="Big Five">
          <div className="grid gap-3 sm:grid-cols-2">
            {(["O", "C", "E", "A", "N"] as const).map((k) => (
              <div
                key={k}
                className="space-y-2 rounded-lg border border-cyan-400/40 bg-cyan-400/5 px-4 py-4"
              >
                <div className="flex items-baseline justify-between">
                  <span className="text-xs uppercase tracking-[0.18em] text-cyan-300">
                    {TRAIT_NAME[k]}
                  </span>
                  <span
                    className="text-2xl font-semibold tabular-nums text-cyan-200"
                    style={{ textShadow: "0 0 14px rgba(34, 211, 238, 0.45)" }}
                  >
                    {value.big_five[k].score}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-foreground">
                  {value.big_five[k].blurb}
                </p>
              </div>
            ))}
          </div>
        </FluentBlock>

        <FluentBlock title="Politics">
          <p className="text-base leading-relaxed text-foreground">
            {value.political_values}
          </p>
        </FluentBlock>

        <FluentBlock title="Your life">
          <p className="text-base leading-relaxed text-foreground">
            {value.life_history}
          </p>
        </FluentBlock>

        <FluentBlock title="What you'd buy">
          <p className="text-base leading-relaxed text-foreground">
            {value.consumer_profile}
          </p>
        </FluentBlock>
      </LevelShell>
    );
  }

  return (
    <LevelShell
      level={4}
      title="Now look at what's actually behind it"
      eyebrow="Level 4 of 8 · The catch"
      onContinue={onContinue}
    >
      <p className="text-sm leading-relaxed text-muted">
        Same four claims, with the actual research behind each one. The
        scores are greyed out on purpose — that's about how much weight
        they should carry.
      </p>

      <DismantleBlock label="Big Five" data={dismantle?.big_five}>
        <div className="grid gap-2 sm:grid-cols-2">
          {(["O", "C", "E", "A", "N"] as const).map((k) => (
            <div
              key={k}
              className="flex items-baseline justify-between rounded-md border border-white/10 px-3 py-2"
            >
              <span className="text-xs uppercase tracking-[0.18em] text-muted">
                {TRAIT_NAME[k]}
              </span>
              <span className="text-sm tabular-nums text-foreground/40">
                {value.big_five[k].score}
              </span>
            </div>
          ))}
        </div>
      </DismantleBlock>

      <DismantleBlock label="Politics" data={dismantle?.political_values}>
        <p className="text-sm leading-relaxed text-foreground/40">
          {value.political_values}
        </p>
      </DismantleBlock>

      <DismantleBlock label="Your life" data={dismantle?.life_history}>
        <p className="text-sm leading-relaxed text-foreground/40">
          {value.life_history}
        </p>
      </DismantleBlock>

      <DismantleBlock label="What you'd buy" data={dismantle?.consumer_profile}>
        <p className="text-sm leading-relaxed text-foreground/40">
          {value.consumer_profile}
        </p>
        <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-cyan-300">
          ← this is the part data brokers actually sell
        </p>
      </DismantleBlock>

      {dismantle && (
        <p className="rounded-lg border border-accent/40 bg-accent/5 px-5 py-4 text-sm leading-relaxed text-foreground">
          {dismantle.closing}
        </p>
      )}
    </LevelShell>
  );
}

function FluentBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-3"
    >
      <h3 className="text-xs uppercase tracking-[0.18em] text-cyan-300">{title}</h3>
      {children}
    </motion.section>
  );
}

function DismantleBlock({
  label,
  data,
  children,
}: {
  label: string;
  data: { title: string; summary: string; citations: string[] } | undefined;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3 rounded-lg border border-white/10 px-5 py-4">
      <h3 className="text-xs uppercase tracking-[0.18em] text-muted">{label}</h3>
      {children}
      {data && (
        <div className="space-y-2 border-t border-white/5 pt-3">
          <p className="text-sm text-cyan-300">{data.summary}</p>
          {data.citations.length > 0 && (
            <ul className="space-y-1 text-[11px] text-muted">
              {data.citations.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
