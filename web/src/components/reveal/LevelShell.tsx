"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

const LEVEL_COUNT = 7;

export type LevelShellProps = {
  level: number;
  title: string;
  eyebrow?: string;
  children: ReactNode;
  onContinue?: () => void;
  continueLabel?: string;
  hideContinue?: boolean;
};

export function ProgressDots({ level }: { level: number }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: LEVEL_COUNT }).map((_, i) => {
        const idx = i + 1;
        const filled = idx < level;
        const current = idx === level;
        return (
          <span
            key={i}
            aria-current={current ? "step" : undefined}
            className={`h-1.5 w-8 rounded-full transition ${
              filled
                ? "bg-accent"
                : current
                  ? "bg-accent/60"
                  : "bg-white/10"
            }`}
          />
        );
      })}
    </div>
  );
}

export function LevelShell({
  level,
  title,
  eyebrow,
  children,
  onContinue,
  continueLabel = "Continue",
  hideContinue = false,
}: LevelShellProps) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col gap-10 px-6 py-12 sm:py-16">
      <header className="flex flex-col items-center gap-5 text-center">
        <ProgressDots level={level} />
        {eyebrow && (
          <p className="text-xs uppercase tracking-[0.18em] text-accent">
            {eyebrow}
          </p>
        )}
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {title}
        </h1>
      </header>

      <motion.section
        key={`level-${level}`}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="flex-1 space-y-6"
      >
        {children}
      </motion.section>

      {!hideContinue && onContinue && (
        <div className="flex justify-center pt-2">
          <button
            type="button"
            onClick={onContinue}
            className="rounded-full bg-accent px-8 py-3 text-sm font-medium text-black transition hover:opacity-90"
          >
            {continueLabel}
          </button>
        </div>
      )}
    </main>
  );
}
