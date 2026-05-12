"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { InferenceData } from "@/lib/schemas";
import { readSessionToken } from "@/lib/session";

const ROUNDS: { id: string; title: string }[] = [
  { id: "choice",  title: "Choice"  },
  { id: "pursuit", title: "Pursuit" },
  { id: "trust",   title: "Trust"   },
  { id: "memory",  title: "Memory"  },
  { id: "read",    title: "Read"    },
  { id: "dilemma", title: "Dilemma" },
];

const CONSTRUCT_LABEL: Record<string, string> = {
  loss_aversion: "Loss aversion",
  risk_tolerance: "Risk tolerance",
  stress_response: "Stress response",
  reaction_time_profile: "Reaction time",
  sustained_attention: "Sustained attention",
  frustration_tolerance: "Frustration tolerance",
  response_inhibition: "Impulse control",
  initial_trust_propensity: "First-meeting trust",
  adaptation_rate: "Adapting to partners",
  retaliation_tendency: "Getting even",
  working_memory_span: "Memory span",
  processing_speed: "Processing speed",
  performance_under_load: "Memory under load",
  attribution_style: "Reading intent",
  deliberation: "How long you took",
  utilitarian_leaning: "More-lives leaning",
  personal_impersonal_sensitivity: "Hands-on vs hands-off",
};

function tierLabel(tier: string): string {
  if (tier === "high") return "Strong evidence";
  if (tier === "medium") return "Some evidence";
  return "Overreach";
}

function tierExplain(tier: string): string {
  if (tier === "high")
    return "Decades of research back this kind of measurement.";
  if (tier === "medium")
    return "Some research supports it. Not a settled finding.";
  return "A confident guess that isn't really backed by the data. We're showing it on purpose so you can see what overconfident analysis looks like.";
}

function formatValue(inf: InferenceData): { headline: string; sub?: string } {
  const v = inf.value as Record<string, unknown>;
  switch (inf.construct) {
    case "loss_aversion": {
      const lambda = Number(v.lambda ?? 0);
      const equivalentWin = Math.round(lambda * 10);
      const equivalentWinDisplay = equivalentWin === 10 ? "$10" : `$${equivalentWin}`;
      return {
        headline: `A $10 loss feels like a ${equivalentWinDisplay} win`,
        sub:
          lambda < 1.2
            ? "Losses and wins of the same size feel about even to you. Most people feel losses about twice as hard — closer to a $10 loss feeling like a $20 win."
            : lambda < 2.5
              ? "Most people land near 2× — a $10 loss feeling like a $20 win. You're in that range."
              : "Well above the typical 2× — losses hit you noticeably harder than they hit most people.",
      };
    }
    case "risk_tolerance": {
      const overall = Number(v.overall_take_rate ?? 0);
      const u = Number(v.unhurried ?? 0);
      const h = Number(v.hurried ?? 0);
      const same = Math.round(u * 100) === Math.round(h * 100);
      return {
        headline: `Took the bet ${Math.round(overall * 100)}% of the time`,
        sub: same
          ? `Same rate whether unhurried or hurried (${Math.round(u * 100)}% in both).`
          : `Unhurried ${Math.round(u * 100)}% · Hurried ${Math.round(h * 100)}%.`,
      };
    }
    case "stress_response": {
      const td = Number(v.take_rate_delta ?? 0);
      if (td === 0) {
        return {
          headline: "No change under time pressure",
          sub: "Your take-rate held steady whether the clock was on or off.",
        };
      }
      const sign = td > 0 ? "+" : "";
      return {
        headline: `${sign}${(td * 100).toFixed(0)} pp under time pressure`,
        sub:
          td > 0
            ? "You took the bet more often when rushed."
            : "You took the bet less often when rushed.",
      };
    }
    case "reaction_time_profile": {
      const cv = Number(v.coefficient_of_variation ?? 0);
      return {
        headline: `${Math.round(Number(v.median_rt_ms ?? 0))} ms median`,
        sub:
          cv > 0.3
            ? "Wide spread between your fastest and slowest taps."
            : "Pretty steady from one tap to the next.",
      };
    }
    case "sustained_attention": {
      const slope = Number(v.rt_slope_ms_per_trial ?? 0);
      const first = Math.round(Number(v.first_half_median ?? 0));
      const second = Math.round(Number(v.second_half_median ?? 0));
      const totalDrift = Math.round(slope * 30);
      if (slope < -3)
        return {
          headline: "Sped up across the round",
          sub: `Your reactions got about ${Math.abs(totalDrift)} ms faster from start to finish (first half ${first} ms, second half ${second} ms).`,
        };
      if (slope > 3)
        return {
          headline: "Slowed down across the round",
          sub: `Your reactions got about ${totalDrift} ms slower from start to finish (first half ${first} ms, second half ${second} ms).`,
        };
      return {
        headline: "Steady focus across the round",
        sub: `Your reactions held within a narrow band from start to finish (first half ${first} ms, second half ${second} ms).`,
      };
    }
    case "frustration_tolerance": {
      const rt = Math.round(Number(v.post_spike_rt_delta_ms ?? 0));
      if (rt > 50)
        return {
          headline: "Slower after a sudden hard trial",
          sub: `After a difficulty spike, your next reactions were about ${rt} ms slower than usual.`,
        };
      if (rt < -50)
        return {
          headline: "Faster after a sudden hard trial",
          sub: `After a difficulty spike, your next reactions were about ${Math.abs(rt)} ms faster than usual.`,
        };
      return {
        headline: "Composure under difficulty spikes",
        sub: "Your reactions barely changed after the difficulty jumps.",
      };
    }
    case "response_inhibition": {
      const decoyPct = Math.round(Number(v.false_alarm_rate ?? 0) * 100);
      const hitPct = Math.round(Number(v.hit_rate ?? 0) * 100);
      const decoyTrials = Number(v.evidence_distractor_trials ?? 6);
      const fa = Math.round((Number(v.false_alarm_rate ?? 0) * decoyTrials));
      return {
        headline:
          decoyPct === 0
            ? "Never clicked a decoy"
            : `Clicked ${decoyPct}% of decoys`,
        sub: `Out of 6 decoy targets, you clicked ${fa}. You hit ${hitPct}% of valid targets in time.`,
      };
    }
    case "initial_trust_propensity": {
      const amt = Number(v.initial_trust_amount ?? 0);
      let mood: string;
      if (amt >= 7) mood = "trusting upfront";
      else if (amt >= 4) mood = "middle of the road";
      else mood = "cautious upfront";
      return {
        headline: `$${amt.toFixed(1)} of $10 sent on first contact`,
        sub: `Averaged across all four partners' first turns — before you knew anything about them. Your ${mood} ($0 = total caution, $10 = full trust).`,
      };
    }
    case "adaptation_rate": {
      const r = Number(v.adaptation_correlation ?? 0);
      let headline: string;
      if (r >= 0.6) headline = "Closely tracked partner behavior";
      else if (r >= 0.2) headline = "Loosely tracked partner behavior";
      else if (r > -0.2) headline = "Ignored partner history";
      else headline = "Moved opposite to partner history";
      return {
        headline,
        sub: `When a partner sent more back, did you send more next time? Correlation = ${r.toFixed(2)}. Near 0 = you ignored history; near 1 = you matched it almost exactly.`,
      };
    }
    case "retaliation_tendency": {
      const d = Number(v.retaliation_delta ?? 0);
      const mag = Math.abs(d).toFixed(2);
      if (d <= -2)
        return {
          headline: "Strong retaliation",
          sub: `After a partner kept almost everything you sent, your next send dropped by about $${mag} below your usual.`,
        };
      if (d <= -0.5)
        return {
          headline: "Some retaliation",
          sub: `After a partner kept almost everything you sent, your next send dropped by about $${mag} below your usual.`,
        };
      return {
        headline: "No retaliation",
        sub: "After a partner kept almost everything you sent, your next send was roughly the same as your usual.",
      };
    }
    case "working_memory_span": {
      const span = Number(v.span ?? 0);
      const correct = Number(v.total_correct ?? 0);
      const attempted = Number(v.total_attempted ?? 0);
      let context: string;
      if (span >= 7) context = "Above the typical adult range of 5–6.";
      else if (span >= 5) context = "Right in the typical adult range of 5–6.";
      else context = "Below the typical adult range of 5–6.";
      return {
        headline: `Correctly repeated a ${span}-block sequence`,
        sub: `${correct} of ${attempted} sequences correct. ${context}`,
      };
    }
    case "processing_speed": {
      const ms = Math.round(Number(v.mean_tap_rt_ms ?? 0));
      return {
        headline: `${ms} ms between taps`,
        sub: "Your average pause from one tap to the next, replaying a sequence.",
      };
    }
    case "performance_under_load": {
      const drop = Number(v.drop ?? 0);
      const low = Math.round(Number(v.accuracy_at_low_span ?? 0) * 100);
      const high = Math.round(Number(v.accuracy_at_high_span ?? 0) * 100);
      if (drop >= 0.4)
        return {
          headline: "Big accuracy drop with longer sequences",
          sub: `Short sequences: ${low}% correct. Longer sequences: ${high}% correct.`,
        };
      if (drop >= 0.1)
        return {
          headline: "Noticeable drop with longer sequences",
          sub: `Short sequences: ${low}% correct. Longer sequences: ${high}% correct.`,
        };
      return {
        headline: "Held accuracy as sequences got longer",
        sub: `Short sequences: ${low}% correct. Longer sequences: ${high}% correct.`,
      };
    }
    case "attribution_style": {
      const h = Number(v.hostile_score ?? 0);
      const i = Number(v.internal_score ?? 0);
      const hPct = Math.round(h * 100);
      const iPct = Math.round(i * 100);
      const hostileWord =
        h >= 0.6 ? "leaned suspicious" : h >= 0.4 ? "mixed" : "leaned charitable";
      const internalWord =
        i >= 0.6 ? "blamed yourself" : i >= 0.4 ? "split the blame" : "blamed circumstance";
      return {
        headline: `You ${hostileWord} and ${internalWord}`,
        sub: `Across 8 ambiguous social moments: ${hPct}% of your picks read intent as bad, ${iPct}% placed the cause on you. Below 50% on either axis = the more charitable read.`,
      };
    }
    case "deliberation": {
      const idx = Number(v.deliberation_index ?? 0);
      const pct = Math.round(Math.abs(idx) * 100);
      if (idx >= 0.2)
        return {
          headline: "Slowed down on later scenarios",
          sub: `You took about ${pct}% longer per choice in the second half than in the first.`,
        };
      if (idx <= -0.2)
        return {
          headline: "Sped up on later scenarios",
          sub: `You took about ${pct}% less time per choice in the second half than in the first.`,
        };
      return {
        headline: "Steady pace across the round",
        sub: "Your time-per-choice barely changed from the first half to the second.",
      };
    }
    case "utilitarian_leaning": {
      const overall = Number(v.utilitarian_rate ?? 0);
      const personal = Math.round(Number(v.personal_rate ?? 0) * 100);
      const impersonal = Math.round(Number(v.impersonal_rate ?? 0) * 100);
      const overallCount = Math.round(overall * 6);
      let leaning: string;
      if (overall >= 0.7) leaning = "Strongly leaned toward saving more lives";
      else if (overall >= 0.4) leaning = "Mixed on saving more lives";
      else leaning = "Rarely picked the save-more-lives option";
      return {
        headline: `Picked the save-more-lives option ${overallCount} of 6 times`,
        sub: `${leaning}. Split: ${impersonal}% when the action was hands-off (e.g., lever), ${personal}% when hands-on (e.g., pushing someone).`,
      };
    }
    case "personal_impersonal_sensitivity": {
      const d = Number(v.sensitivity_delta ?? 0);
      const pts = Math.round(Math.abs(d) * 100);
      if (d >= 0.2)
        return {
          headline: "Saved more lives mostly when hands-off",
          sub: `You were about ${pts} points more likely to save more lives when the action didn't require physically doing something to someone.`,
        };
      if (d <= -0.2)
        return {
          headline: "Saved more lives mostly when hands-on",
          sub: `You were about ${pts} points more likely to save more lives when you had to physically do it yourself.`,
        };
      return {
        headline: "Hands-on or hands-off didn't change your answer",
        sub: "Your save-more-lives rate was similar whether the action was physical or remote.",
      };
    }
    default:
      return { headline: JSON.stringify(inf.value) };
  }
}

function ConfidenceBand({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="space-y-1">
      <div className="h-1 w-full rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[11px] tabular-nums text-muted">
        From your gameplay: {pct.toFixed(0)}%
      </p>
    </div>
  );
}

export default function RevealStubPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = readSessionToken();
    if (!t) {
      router.replace("/");
      return;
    }
    setToken(t);
  }, [router]);

  const sessionQuery = useQuery({
    queryKey: ["session", token],
    queryFn: () => api.getSession(token!),
    enabled: token !== null,
  });

  const queries = useQueries({
    queries: ROUNDS.map((r) => ({
      queryKey: ["inferences", token, r.id],
      queryFn: () => api.getInferences(token!, r.id),
      enabled: token !== null,
    })),
  });

  const grouped = useMemo(() => {
    return ROUNDS.map((r, idx) => ({
      round: r,
      inferences: queries[idx].data?.inferences ?? [],
      isLoading: queries[idx].isLoading,
      error: queries[idx].error,
    }));
  }, [queries]);

  const nextRound = sessionQuery.data?.next_round ?? null;
  const completedRounds = sessionQuery.data?.completed_rounds ?? [];
  const nextRoundTitle =
    nextRound !== null
      ? ROUNDS.find((r) => r.id === nextRound)?.title ?? nextRound
      : null;
  const nextRoundOrdinal = completedRounds.length + 1;

  if (token === null) return null;

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col gap-12 px-6 py-16">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.18em] text-accent">Reveal</p>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          What the game saw.
        </h1>
      </header>

      <aside className="space-y-3 rounded-lg border border-white/10 bg-white/[0.02] px-5 py-4 text-sm leading-relaxed text-muted">
        <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/70">
          How to read this page
        </p>
        <p>
          Every card has two scores. They mean different things.
        </p>
        <ul className="space-y-2 pl-4">
          <li>
            <span className="text-foreground">The label on the right</span> is
            about the measurement, not you. "Strong evidence" means decades of
            research back this kind of read. "Some evidence" means it's a real
            idea but the research is mixed. "Overreach" means we're showing
            you a confident-sounding guess on purpose, so you can see what
            overconfident analysis looks like.
          </li>
          <li>
            <span className="text-foreground">The bar at the bottom</span> is
            about you. How clearly did your own gameplay land in one
            direction? Short rounds and quick decisions leave less to read,
            so the bar gets shorter — that's the rounds being short, not you
            being wrong.
          </li>
        </ul>
      </aside>

      {nextRound !== null && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col gap-3 rounded-lg border border-accent/40 bg-accent/5 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-[0.18em] text-accent">
              Round {nextRoundOrdinal} of 6
            </p>
            <p className="text-sm text-foreground">
              You still have {ROUNDS.length - completedRounds.length} rounds to play.
              Pick up where you left off: {nextRoundTitle}.
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.push("/play")}
            className="self-start rounded-full bg-accent px-5 py-2 text-sm font-medium text-black transition hover:opacity-90 sm:self-auto"
          >
            Keep going
          </button>
        </motion.div>
      )}

      {grouped.map(({ round, inferences, isLoading, error }) => (
        <section key={round.id} className="space-y-4">
          <h2 className="text-xs uppercase tracking-[0.18em] text-muted">
            {round.title}
          </h2>
          {isLoading && <p className="text-sm text-muted">Scoring {round.title}…</p>}
          {error && (
            <p className="text-sm text-red-300">
              Failed to load {round.id}: {String(error)}
            </p>
          )}
          {inferences.length === 0 && !isLoading && (
            <p className="text-xs text-muted">
              No inferences yet for {round.title}.
            </p>
          )}
          <ol className="space-y-3">
            {inferences.map((inf: InferenceData, i: number) => {
              const fmt = formatValue(inf);
              return (
                <motion.li
                  key={`${round.id}:${inf.construct}`}
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
                  <ConfidenceBand value={inf.confidence} />
                </motion.li>
              );
            })}
          </ol>
        </section>
      ))}
    </main>
  );
}
