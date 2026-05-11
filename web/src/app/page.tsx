"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";

type AgeChoice = "yes" | "no" | null;

export default function LandingPage() {
  const router = useRouter();
  const [age, setAge] = useState<AgeChoice>(null);

  const canBegin = age === "yes";

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center gap-12 px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="space-y-4"
      >
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Inkling
        </h1>
        <p className="text-base leading-relaxed text-foreground/90 sm:text-lg">
          Inkling is a 15-minute game that tries to guess who you are from how
          you play. Then it shows you everything it inferred, and how that same
          data would be used to target you covertly.
        </p>
      </motion.div>

      <motion.fieldset
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="space-y-3"
      >
        <legend className="text-sm font-medium text-muted">
          Before you start
        </legend>
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/10 px-4 py-3 transition hover:border-accent/60">
          <input
            type="radio"
            name="age"
            value="yes"
            checked={age === "yes"}
            onChange={() => setAge("yes")}
            className="accent-accent"
          />
          <span>I am 18 or older.</span>
        </label>
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/10 px-4 py-3 transition hover:border-accent/60">
          <input
            type="radio"
            name="age"
            value="no"
            checked={age === "no"}
            onChange={() => setAge("no")}
            className="accent-accent"
          />
          <span>I am not.</span>
        </label>
        {age === "no" && (
          <p className="pt-1 text-sm text-muted">
            Inkling is restricted to adults. Come back when you&apos;re 18.
          </p>
        )}
      </motion.fieldset>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <button
          type="button"
          disabled={!canBegin}
          onClick={() => router.push("/consent")}
          className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-black transition disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-muted"
        >
          Begin
        </button>
      </motion.div>
    </main>
  );
}
