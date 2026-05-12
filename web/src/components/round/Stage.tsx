"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ReactNode } from "react";

type Props = {
  title: string;
  trialIndex: number;
  totalTrials: number;
  trialKey: string;
  meta?: ReactNode;
  children: ReactNode;
};

/**
 * Round-agnostic stage shell. Header, progress meter, optional meta slot
 * (e.g., a countdown), and a Framer Motion crossfade between trials keyed
 * by `trialKey`.
 */
export function Stage({ title, trialIndex, totalTrials, trialKey, meta, children }: Props) {
  const progress = totalTrials === 0 ? 0 : Math.round((trialIndex / totalTrials) * 100);

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col gap-10 px-6 py-16">
      <header className="space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
          {meta}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted">
          <div className="h-1 flex-1 rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="tabular-nums">
            {Math.min(trialIndex + 1, totalTrials)} / {totalTrials}
          </span>
        </div>
      </header>

      <AnimatePresence mode="wait">
        <motion.section
          key={trialKey}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
          className="flex flex-1 flex-col gap-8"
        >
          {children}
        </motion.section>
      </AnimatePresence>
    </main>
  );
}
