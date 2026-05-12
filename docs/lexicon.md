# Lexicon

The language we use in the product is part of the product. This document
is the binding contract for every player-facing string (round content,
inferences reveal copy, microcopy, hero text, error messages) and for the
descriptive prose inside scorers, schemas, and route handlers.

The `check-lexicon` make target enforces this lexicon against the
codebase. The grep is exact and case-insensitive — any new round content,
inference framing, or comment that re-introduces a forbidden term will
break the build.

---

## Why we have a lexicon

Inkling makes inferences from a tiny window of behavior. The reveal does
two things at once: it states what the game saw, and it teaches the
player what kind of evidence does and does not justify a personality
claim. If we slip into clinical or pop-psych language, we undercut both:

- Clinical labels imply a diagnostic frame Inkling cannot deliver and
  must not pretend to.
- Pop-psych labels ("toxic person", "narcissist", "your inner child")
  package judgments as truths. They feel intuitive precisely because they
  short-circuit evidence.

The lexicon is the line between "here is what your gameplay implied" and
"here is what kind of person you are." We stay on the first side.

---

## Forbidden terms

The exact terms the build refuses:

| Term | Why it is out |
| ---- | ------------- |
| `psychopath`, `sociopath`, `narcissist` | Clinical personality-disorder vocabulary, frequently misapplied. Not inferable from gameplay. |
| `gaslight`, `gaslighting` | Pop-psych shorthand for a specific abuse pattern. Inkling cannot identify abuse from interaction logs. |
| `toxic person` | Reduces a relationship dynamic to a person-type label. Inkling does not classify people as toxic. |
| `inner child` | Therapeutic-modality language. Inkling is not therapy. |
| `healing journey` | Wellness-industry framing. Imports outcomes Inkling does not measure. |
| `MBTI`, `enneagram` | Typology systems with weak construct validity. Inkling reports continuous scores, not types. |
| `empath`, `love language` | Pop-typology categories. Inkling cannot type-assign and does not pretend to. |
| `triggered` | Outside trauma-clinical usage, a sarcasm marker. Outside its clinical usage it trivializes the source meaning. |
| `trauma`, `traumatic`, `traumatized` | Clinical category. Inkling does not assess for trauma history or response. |
| `disorder`, `diagnosis`, `pathological`, `comorbid` | Diagnostic vocabulary. Inkling is not a diagnostic instrument. |

The terms are not bad words — most have a legitimate clinical or research
use. They are forbidden in *this product* because Inkling is not the
instrument that earns the right to use them.

---

## Allowed framings

Where it would be tempting to reach for a forbidden term, use one of
these instead. Each is paired with the construct it tends to come up in.

### Instead of clinical or pop-psych personality labels

| Tempting | Use |
| -------- | --- |
| "You're a narcissist" | "Self-focused on this task." |
| "You sound like an empath" | "Sensitive to social cues in the scenarios you read." |
| "You're triggered easily" | "Your reaction times shift sharply after a setback." |
| "You're toxic in negotiations" | "After a partner takes more than expected, you reduce what you send back." |

### Instead of diagnostic categories

| Tempting | Use |
| -------- | --- |
| "Symptoms of [disorder]" | "Patterns in how you responded to [round]." |
| "Diagnosis: …" | "Inference: …" |
| "Pathological [trait]" | "[Trait] at the high end of the range we saw." |

### Instead of trauma framing

| Tempting | Use |
| -------- | --- |
| "Your trauma response is …" | "Your response to time pressure is …" |
| "This was a triggering scenario" | "This was a high-pressure scenario." |
| "Old wounds came up" | (drop the framing — describe behavior, not history) |

### Instead of pop-typology

| Tempting | Use |
| -------- | --- |
| "You're an INTJ" | "On the deliberation-vs-intuition axis, your choices tilt toward deliberation." |
| "Your love language is …" | (drop — Inkling does not measure this) |
| "You're a 4 on the enneagram" | (drop — Inkling does not type-assign) |

---

## Round-content drafting rules

When authoring scenarios (Read), dilemmas (Dilemma), NPC descriptions
(Trust), or any other player-facing prose:

1. **Plain English.** A scenario should read like something one friend
   tells another. No clinical vocabulary, no diagnostic framing.
2. **Neutral references.** Refer to people by role ("a coworker", "your
   neighbor", "the driver") rather than by name when possible. Where a
   name is needed, use a short, culturally-unmarked first name (Alex,
   Sam, Jordan, Taylor). Never use real public figures.
3. **No stereotyped behaviors.** Do not lean on marginalized identities
   (race, class, disability, immigration status, mental health) for the
   "sacrifice" or "wrong choice" in any scenario.
4. **No political proxies.** Scenarios must not read as analogs for
   abortion, immigration, war, or election questions.
5. **No real-event references.** No "based on a true story" — scenarios
   are deliberately hypothetical.
6. **Short.** 1–3 sentences for Read scenarios; 2–4 sentences for
   Dilemmas.

---

## Reveal-copy drafting rules

When writing inference reveal copy (the player-facing summary of each
score):

1. **Lead with the observation, then the framing.** "You picked the
   utilitarian option 4 of 6 times" before "your style leans
   utilitarian", never the other way around.
2. **Bound the claim to the evidence.** "On this round, …" or "From these
   six choices, …". Avoid claims that exceed the data window.
3. **Use confidence words honestly.** "Suggests" or "is consistent with"
   for medium-confidence. Reserve "shows" / "is" for high-confidence
   inferences where the evidence really does support the verb.
4. **Cite the construct, not a personality.** "Loss aversion λ = 2.3"
   over "you are loss-averse as a person".
5. **No clinical, no pop-psych, no typology.** The forbidden table is
   the floor, not the ceiling — when in doubt, write more plainly.

---

## Citations are part of the contract

Every scorer's `Inference.value` and `Inference.evidence` are paired with
a citation in [`docs/inferences.md`](inferences.md). The citation is part
of the contract: a scorer without a published construct definition is
not allowed to ship. If a future round changes its scoring formula, the
citation must be updated in the same change.
