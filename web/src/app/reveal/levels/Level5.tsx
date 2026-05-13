"use client";

import { LevelShell } from "@/components/reveal/LevelShell";
import { InferenceData } from "@/lib/schemas";

type PricingComponent = { label: string; construct: string; price: number };
type PricingValue = {
  components: PricingComponent[];
  raw_subtotal: number;
  package_premium: number;
  total: number;
  framing: string;
};

function shortHash(token: string): string {
  // Cheap, deterministic, never the raw token. Six base36 chars.
  let h = 0;
  for (let i = 0; i < token.length; i++) {
    h = (h * 31 + token.charCodeAt(i)) | 0;
  }
  return Math.abs(h).toString(36).slice(0, 6).toUpperCase();
}

export function Level5({
  inference,
  sessionToken,
  onContinue,
}: {
  inference: InferenceData | null;
  sessionToken: string;
  onContinue: () => void;
}) {
  if (!inference) {
    return (
      <LevelShell
        level={5}
        title="Pricing you up…"
        eyebrow="Level 5 of 8"
        onContinue={onContinue}
      >
        <p className="text-sm text-muted">One sec.</p>
      </LevelShell>
    );
  }
  const v = inference.value as PricingValue;
  return (
    <LevelShell
      level={5}
      title="Here's what you're worth"
      eyebrow="Level 5 of 8 · Your price tag"
      onContinue={onContinue}
    >
      <p className="text-sm leading-relaxed text-muted">
        This is roughly what a data broker would charge an advertiser for
        your file. The numbers are in the ballpark of what brokers like
        Acxiom and Experian actually charge — they're not a real quote,
        but they're not made up either. Inkling does not sell any of this.
      </p>

      <article className="space-y-4 rounded-xl border border-cyan-400/40 bg-cyan-400/5 px-6 py-6">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-[0.18em] text-cyan-300">
            Profile #{shortHash(sessionToken)}
          </p>
          <h2 className="text-xl font-semibold text-foreground">
            One person, packaged for sale
          </h2>
        </header>

        <ul className="divide-y divide-white/5">
          {v.components.map((c, i) => (
            <li key={i} className="flex items-baseline justify-between gap-4 py-2 text-sm">
              <div className="space-y-0.5">
                <p className="text-foreground">{c.label}</p>
                <p className="text-[11px] text-muted">{c.construct}</p>
              </div>
              <p className="tabular-nums text-foreground/80">
                ${c.price.toFixed(3)}
              </p>
            </li>
          ))}
        </ul>

        <div className="space-y-1 border-t border-white/10 pt-3 text-sm">
          <div className="flex justify-between text-muted">
            <span>Add it up</span>
            <span className="tabular-nums">${v.raw_subtotal.toFixed(3)}</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Bundle markup ({v.package_premium}x)</span>
            <span className="tabular-nums">
              x{v.package_premium.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between border-t border-white/10 pt-2 text-base font-semibold text-foreground">
            <span>What an advertiser pays</span>
            <span className="tabular-nums">${v.total.toFixed(3)}</span>
          </div>
        </div>

        <p className="border-t border-white/10 pt-3 text-[11px] text-muted">
          That's per record. Brokers sell millions at a time.
        </p>
      </article>

      <p className="text-[11px] text-muted">{v.framing}</p>
    </LevelShell>
  );
}
