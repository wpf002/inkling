"use client";

import { motion } from "framer-motion";
import { LevelShell } from "@/components/reveal/LevelShell";
import { InferenceData } from "@/lib/schemas";
import {
  CONSTRUCT_LABEL,
  evidenceFor,
  formatValue,
  tierExplain,
  tierLabel,
} from "../lib/formatInference";
import { ConfidenceBand } from "./shared/ConfidenceBand";

export function Level3({
  inferences,
  onContinue,
}: {
  inferences: InferenceData[];
  onContinue: () => void;
}) {
  const medium = inferences.filter((i) => i.tier === "medium");
  return (
    <LevelShell
      level={3}
      title="What the game half-saw"
      eyebrow="Level 3 of 8 · Some evidence"
      onContinue={onContinue}
    >
      <p className="text-sm leading-relaxed text-muted">
        Real things to read for — but fifteen minutes is a thin slice.
        We're showing the read anyway, with a wider margin for being
        wrong.
      </p>

      <ol className="space-y-4">
        {medium.map((inf, i) => {
          const fmt = formatValue(inf);
          const ev = evidenceFor(inf);
          return (
            <motion.li
              key={inf.construct}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: 0.04 * i }}
              className="space-y-3 rounded-lg border border-white/10 px-5 py-5"
            >
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-base font-medium">
                  {CONSTRUCT_LABEL[inf.construct] ?? inf.construct}
                </h3>
                <span
                  title={tierExplain(inf.tier)}
                  className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-muted"
                >
                  {tierLabel(inf.tier)}
                </span>
              </div>
              <p className="text-xl font-semibold tracking-tight text-foreground">
                {fmt.headline}
              </p>
              {fmt.sub && (
                <p className="text-sm leading-relaxed text-muted">{fmt.sub}</p>
              )}
              <p className="text-[11px] italic text-muted">
                Real thing in the literature. Thin slice in your case — take it with a grain of salt.
              </p>
              {ev.length > 0 && (
                <div className="space-y-1 rounded-md border border-white/5 bg-white/2 px-3 py-2 text-[11px] text-muted">
                  <p className="uppercase tracking-[0.18em] text-foreground/60">
                    Where this came from
                  </p>
                  <ul className="space-y-1">
                    {ev.map((e, idx) => (
                      <li key={idx}>
                        <span className="text-foreground">{e.label}</span>
                        {e.detail ? ` — ${e.detail}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <ConfidenceBand value={inf.confidence} />
            </motion.li>
          );
        })}
      </ol>
    </LevelShell>
  );
}
