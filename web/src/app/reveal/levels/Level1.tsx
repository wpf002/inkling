"use client";

import { motion } from "framer-motion";
import { LevelShell } from "@/components/reveal/LevelShell";
import { InferenceData } from "@/lib/schemas";
import { SELF_REPORT_LABEL } from "../lib/formatInference";

type Pair = {
  item_id: string;
  construct: string;
  divergence: number;
  self_norm: number;
  game_norm: number;
  self_response?: number;
};

export function Level1({
  inference,
  onContinue,
}: {
  inference: InferenceData | null;
  onContinue: () => void;
}) {
  if (!inference) {
    return (
      <LevelShell
        level={1}
        title="What you said vs how you played"
        eyebrow="Level 1 of 8"
        onContinue={onContinue}
      >
        <p className="text-sm leading-relaxed text-muted">
          You need to finish at least one round before this works. Head
          back and play through.
        </p>
      </LevelShell>
    );
  }

  const value = inference.value as { pairs?: Pair[]; top?: Pair[] };
  const top = (value.top ?? []) as Pair[];
  const pairs = (value.pairs ?? []) as Pair[];
  const byId: Record<string, Pair> = {};
  for (const p of pairs) byId[p.item_id] = p;

  return (
    <LevelShell
      level={1}
      title="What you said vs how you played"
      eyebrow="Level 1 of 8"
      onContinue={onContinue}
    >
      <p className="text-sm leading-relaxed text-muted">
        Before you played, you answered ten quick questions about
        yourself. Then you played for fifteen minutes. Here are the three
        biggest places those two stories disagree.
      </p>

      <ol className="space-y-4">
        {top.map((t, i) => {
          const full = byId[t.item_id] ?? t;
          // Put both on the original 1-5 scale so the numbers mean
          // something to a normal reader.
          const saidLikert = full.self_response ?? Math.round((full.self_norm ?? 0) * 4 + 1);
          const playedLikert = Math.round((full.game_norm ?? 0) * 4 + 1);
          const construct = SELF_REPORT_LABEL[t.construct] ?? t.construct;
          return (
            <motion.li
              key={t.item_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
              className="space-y-3 rounded-lg border border-white/10 px-5 py-5"
            >
              <p className="text-xs uppercase tracking-[0.18em] text-accent">
                #{i + 1}: {construct}
              </p>
              <p className="text-base leading-relaxed">
                You rated yourself{" "}
                <span className="text-foreground">{saidLikert}/5</span>. Your
                play landed closer to{" "}
                <span className="text-foreground">{playedLikert}/5</span>.
              </p>
              <Bars said={Math.round((full.self_norm ?? 0) * 100)} played={Math.round((full.game_norm ?? 0) * 100)} />
            </motion.li>
          );
        })}
      </ol>
    </LevelShell>
  );
}

function Bars({ said, played }: { said: number; played: number }) {
  return (
    <div className="space-y-2 text-[11px] uppercase tracking-[0.18em] text-muted">
      <div className="space-y-1">
        <span>What you said</span>
        <div className="h-1 w-full rounded-full bg-white/10">
          <div className="h-full rounded-full bg-foreground/60" style={{ width: `${said}%` }} />
        </div>
      </div>
      <div className="space-y-1">
        <span>How you played</span>
        <div className="h-1 w-full rounded-full bg-white/10">
          <div className="h-full rounded-full bg-accent" style={{ width: `${played}%` }} />
        </div>
      </div>
    </div>
  );
}
