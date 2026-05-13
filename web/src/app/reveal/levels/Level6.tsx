"use client";

import { LevelShell } from "@/components/reveal/LevelShell";
import { TargetingResponse } from "@/lib/schemas";

export function Level6({
  data,
  isLoading,
  onContinue,
}: {
  data: TargetingResponse | null;
  isLoading: boolean;
  onContinue: () => void;
}) {
  if (isLoading || !data) {
    return (
      <LevelShell
        level={6}
        title="Lining up what you'd see…"
        eyebrow="Level 6 of 8"
        onContinue={onContinue}
      >
        <p className="text-sm text-muted">One sec.</p>
      </LevelShell>
    );
  }
  return (
    <LevelShell
      level={6}
      title="What this gets you sent"
      eyebrow="Level 6 of 8 · Pretend, not real"
      onContinue={onContinue}
    >
      <p className="text-sm leading-relaxed text-muted">
        None of these were sent. They're examples of what someone holding
        your profile would aim at you. Each card says PRETEND so there's
        no confusion.
      </p>

      <section className="space-y-3">
        <h2 className="text-xs uppercase tracking-[0.18em] text-foreground/70">
          Ads you'd start seeing
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {data.ads.map((ad, i) => {
            const a = ad as { headline_template?: string; body_template?: string; category?: string };
            return (
              <div
                key={i}
                className="relative space-y-2 rounded-lg border border-white/10 px-4 py-4"
              >
                <SimBadge />
                <p className="text-[10px] uppercase tracking-[0.18em] text-muted">
                  {a.category}
                </p>
                <p className="text-sm font-medium text-foreground">{a.headline_template}</p>
                <p className="text-xs leading-relaxed text-muted">{a.body_template}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xs uppercase tracking-[0.18em] text-foreground/70">
          Scams that would land best on you
        </h2>
        <ul className="space-y-2">
          {data.scams.map((s, i) => {
            const sc = s as { type?: string; scenario_template?: string };
            return (
              <li
                key={i}
                className="relative space-y-1 rounded-lg border border-white/10 px-4 py-3"
              >
                <SimBadge />
                <p className="text-[10px] uppercase tracking-[0.18em] text-muted">
                  {sc.type}
                </p>
                <p className="text-sm leading-relaxed text-foreground">
                  {sc.scenario_template}
                </p>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xs uppercase tracking-[0.18em] text-foreground/70">
          A recruiter slides into your inbox
        </h2>
        {data.recruiter.map((r, i) => {
          const rc = r as { role?: string; pitch_template?: string };
          return (
            <article
              key={i}
              className="relative space-y-2 rounded-lg border border-white/10 px-5 py-4"
            >
              <SimBadge />
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted">
                {rc.role}
              </p>
              <p className="text-sm leading-relaxed text-foreground">
                {rc.pitch_template}
              </p>
            </article>
          );
        })}
      </section>
    </LevelShell>
  );
}

function SimBadge() {
  return (
    <span className="absolute right-3 top-3 rounded-full border border-cyan-400/40 bg-cyan-400/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-cyan-300">
      Pretend
    </span>
  );
}
