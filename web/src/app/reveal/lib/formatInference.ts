import { InferenceData } from "@/lib/schemas";

export const CONSTRUCT_LABEL: Record<string, string> = {
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

export const SELF_REPORT_LABEL: Record<string, string> = {
  risk_tolerance: "Risk tolerance",
  loss_aversion: "Loss aversion",
  trust: "Trust",
  fairness: "Fairness",
  attribution: "Attribution",
  deliberation: "Deliberation",
  moral_utilitarian: "Utilitarian leaning",
  stress_response: "Stress response",
  attention: "Attention",
  novelty: "Novelty",
};

export function tierLabel(tier: string): string {
  if (tier === "high") return "Strong evidence";
  if (tier === "medium") return "Some evidence";
  return "Overreach";
}

export function tierExplain(tier: string): string {
  if (tier === "high")
    return "Decades of research back this kind of measurement.";
  if (tier === "medium")
    return "Some research supports it. Not a settled finding.";
  return "A confident guess that is not really backed by the data. We are showing it on purpose so you can see what overconfident analysis looks like.";
}

export function formatValue(inf: InferenceData): { headline: string; sub?: string } {
  const v = inf.value as Record<string, unknown>;
  switch (inf.construct) {
    case "loss_aversion": {
      const lambda = Number(v.lambda ?? 0);
      const equivalentWin = Math.max(1, Math.round(lambda * 10));
      const equivalentWinDisplay = equivalentWin === 10 ? "$10" : `$${equivalentWin}`;
      if (lambda < 0.5) {
        return {
          headline: "A $10 loss barely registers",
          sub: "Losses don't sting much for you — you took bets where the upside was smaller than the downside. Most people feel losses about twice as hard as same-size wins.",
        };
      }
      if (lambda < 1.2) {
        return {
          headline: `A $10 loss feels like a ${equivalentWinDisplay} win`,
          sub: "Losses and same-size wins feel about even to you. Most people feel losses about twice as hard.",
        };
      }
      if (lambda < 2.5) {
        return {
          headline: `A $10 loss feels like a ${equivalentWinDisplay} win`,
          sub: "Most people land near 2x — a $10 loss feels about like a $20 win. You're right around there.",
        };
      }
      return {
        headline: `A $10 loss feels like a ${equivalentWinDisplay} win`,
        sub: "Well above the typical 2x — losses hit you noticeably harder than they hit most people.",
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
          headline: "Time pressure didn't change you",
          sub: "Same take rate with the clock running or not.",
        };
      }
      const pct = Math.abs(Math.round(td * 100));
      return {
        headline:
          td > 0
            ? "You got bolder under the clock"
            : "You got more careful under the clock",
        sub:
          td > 0
            ? `You took the bet ${pct}% more often when the clock was running.`
            : `You took the bet ${pct}% less often when the clock was running.`,
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
      const fa = Math.round(Number(v.false_alarm_rate ?? 0) * decoyTrials);
      return {
        headline:
          decoyPct === 0 ? "Never clicked a decoy" : `Clicked ${decoyPct}% of decoys`,
        sub: `Out of 6 decoy targets, you clicked ${fa}. You hit ${hitPct}% of valid targets in time.`,
      };
    }
    case "initial_trust_propensity": {
      const amt = Number(v.initial_trust_amount ?? 0);
      let mood: string;
      if (amt >= 7) mood = "You lead with trust before you know anyone.";
      else if (amt >= 4) mood = "You start somewhere in the middle — neither all in nor closed off.";
      else mood = "You hold back until someone earns it.";
      return {
        headline: `You handed over $${amt.toFixed(1)} of $10 to a stranger`,
        sub: `Averaged across the first round with each of four people you'd never met. ${mood}`,
      };
    }
    case "adaptation_rate": {
      const r = Number(v.adaptation_correlation ?? 0);
      let headline: string;
      let sub: string;
      if (r >= 0.6) {
        headline = "You read the room and adjusted";
        sub = "When a partner gave more back, you sent more next time. When they shorted you, you pulled back. You were paying attention.";
      } else if (r >= 0.2) {
        headline = "You adjusted, but only a little";
        sub = "How partners behaved nudged your next move, but it wasn't the main thing driving you.";
      } else if (r > -0.2) {
        headline = "You stuck to your own plan";
        sub = "What partners did barely changed what you sent next. You had your number and you held to it.";
      } else {
        headline = "You moved against your partners";
        sub = "When they were generous you held back, and when they shorted you, you sent more. Unusual pattern — could be testing, could be contrarian.";
      }
      return { headline, sub };
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
      if (span >= 7) context = "Above the typical adult range of 5-6.";
      else if (span >= 5) context = "Right in the typical adult range of 5-6.";
      else context = "Below the typical adult range of 5-6.";
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
        sub: `Across 8 ambiguous social moments: ${hPct}% of your picks read intent as bad, ${iPct}% placed the cause on you.`,
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
        sub: `${leaning}. Split: ${impersonal}% when the action was hands-off, ${personal}% when hands-on.`,
      };
    }
    case "personal_impersonal_sensitivity": {
      const d = Number(v.sensitivity_delta ?? 0);
      const pts = Math.round(Math.abs(d) * 100);
      if (d >= 0.2)
        return {
          headline: "Saved more lives mostly when hands-off",
          sub: `You were about ${pts} points more likely to save more lives when the action did not require physically doing something to someone.`,
        };
      if (d <= -0.2)
        return {
          headline: "Saved more lives mostly when hands-on",
          sub: `You were about ${pts} points more likely to save more lives when you had to physically do it yourself.`,
        };
      return {
        headline: "Hands-on or hands-off did not change your answer",
        sub: "Your save-more-lives rate was similar whether the action was physical or remote.",
      };
    }
    default:
      return { headline: JSON.stringify(inf.value) };
  }
}

export type Evidence = { label: string; detail?: string };

export function evidenceFor(inf: InferenceData): Evidence[] {
  const v = inf.value as Record<string, unknown>;
  const ev = inf.evidence as Record<string, unknown>;
  switch (inf.construct) {
    case "loss_aversion": {
      const perTrial = (ev.per_trial as Array<Record<string, unknown>>) ?? [];
      return perTrial.slice(0, 3).map((t) => ({
        label: `Win $${Number(t.win)} / lose $${Number(t.lose)}`,
        detail:
          String(t.choice) === "take" ? "You took it." : "You declined.",
      }));
    }
    case "risk_tolerance": {
      const u = Number(v.unhurried ?? 0);
      const h = Number(v.hurried ?? 0);
      return [
        { label: "Unhurried", detail: `${Math.round(u * 100)}% take rate` },
        { label: "Hurried", detail: `${Math.round(h * 100)}% take rate` },
      ];
    }
    case "stress_response": {
      const pairs = (ev.per_gamble_deltas as Array<Record<string, unknown>>) ?? [];
      return pairs.slice(0, 3).map((p) => {
        const td = Number(p.take_delta);
        const rtRaw = p.rt_delta_ms;
        const rt = rtRaw == null ? null : Math.round(Number(rtRaw));
        const id = String(p.gamble_id ?? "").toUpperCase();
        let detail: string;
        if (td > 0) {
          detail = "You took it with the clock running, declined it without.";
        } else if (td < 0) {
          detail = "You took it without the clock, declined it under one.";
        } else if (rt != null && rt > 50) {
          detail = `Same call, but you took ${rt} ms longer under the clock.`;
        } else if (rt != null && rt < -50) {
          detail = `Same call, but you decided ${Math.abs(rt)} ms faster under the clock.`;
        } else {
          detail = "Same call either way.";
        }
        return { label: `Gamble ${id}`, detail };
      });
    }
    default:
      // No curated evidence formatter for this construct — the headline
      // and sub already say everything. Don't dump raw field names.
      return [];
  }
}
