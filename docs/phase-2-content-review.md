# Phase 2 — content review

Self-audit of Round 5 (Read) scenarios and Round 6 (Dilemma) dilemmas
against the seven criteria from the Phase 2 brief:

- (a) No names or descriptors that imply race, gender, class, or
  nationality. Neutral role-based references preferred; first names only
  when they are short, gender-neutral, and culturally unmarked.
- (b) No stereotyped behaviors. Marginalized groups never serve as the
  "wrong-choice" or "sacrifice" in any scenario.
- (c) No real-world political proxies (no abortion, immigration, war, or
  election analogs).
- (d) Round 5 only: at least two of the four options are defensible
  interpretations to a reasonable reader.
- (e) Round 6 only: stay within the classic moral-philosophy canon
  (trolley/lever, footbridge, lifeboat, hospital/organ harvest, drowning
  child, ticking bomb).
- (f) Plain English, conversational, 1–3 short sentences for scenarios
  or 2–4 for dilemmas.
- (g) Passes `make check-lexicon`.

This is a Phase 2 audit artifact; future phases do not need to extend
it.

---

## Round 5 — Read

| ID | Audit |
| --- | --- |
| read_01 — "Coworker walked past in hallway." | (a) coworker, role-only ✓ · (b) no stereotypes ✓ · (c) no political proxy ✓ · (d) options a/b/d all defensible (intentional snub vs not-noticed vs general short-with-everyone) ✓ · (f) 2 sentences ✓ · (g) passes ✓ |
| read_02 — "Friend hasn't replied to a long text." | (a) friend, no name ✓ · (b) ✓ · (c) ✓ · (d) b/c/d defensible (busy vs message-too-long vs friendship-thin) ✓ · (f) 2 sentences ✓ · (g) ✓ |
| read_03 — "Manager scheduled a one-on-one with no agenda." | (a) manager, role-only ✓ · (b) ✓ · (c) ✓ · (d) a/b/d defensible (bad news vs casual catch-up vs early update) ✓ · (f) 2 sentences ✓ · (g) ✓ |
| read_04 — "Driver cut you off without signaling." | (a) driver, role-only ✓ · (b) no stereotypes ✓ · (c) ✓ · (d) a/b/c defensible (aggression vs distraction vs blind spot) ✓ · (f) 1 sentence ✓ · (g) ✓ |
| read_05 — "Idea floated in meeting, room went quiet." | (a) generic meeting ✓ · (b) ✓ · (c) ✓ · (d) b/c/d all defensible (still-thinking vs unclear-pitch vs group-norm) ✓ · (f) 2 sentences ✓ · (g) ✓ |
| read_06 — "Neighbor has been short for days, nothing obvious." | (a) neighbor, role-only ✓ · (b) ✓ · (c) ✓ · (d) b/c/d defensible (their stuff vs forgot offense vs general short) ✓ · (f) 2 sentences ✓ · (g) ✓ |
| read_07 — "Two people at a party glance over a few times." | (a) "two people," no names ✓ · (b) ✓ · (c) ✓ · (d) b/d defensible (door-line-of-sight vs face-recognition); a/c reasonable for hostile/internal readers ✓ · (f) 2 sentences ✓ · (g) ✓ |
| read_08 — "Applied for a role, no reply in two weeks." | (a) role-only ✓ · (b) ✓ · (c) not a political proxy (hiring delay is generic) ✓ · (d) a/b/c/d all reasonable readings ✓ · (f) 1 sentence ✓ · (g) ✓ |

Tag coverage: across the 8 scenarios, the option set spans every
(hostile/benign × internal/external) cell at least once. No tag
combination is forced into a single "right answer."

## Round 6 — Dilemma

| ID | Audit |
| --- | --- |
| dil_lever — Trolley/lever, impersonal, unhurried | (a) "five workers"/"one worker" — role-only ✓ · (b) workers, not a marginalized group ✓ · (c) classic trolley, not a political proxy ✓ · (e) canonical (trolley lever) ✓ · (f) 3 sentences ✓ · (g) ✓ |
| dil_footbridge — Footbridge push, personal, unhurried | (a) "heavy stranger" — body-type descriptor is *load-bearing* in the canonical formulation (Greene 2001) so we keep it; no race/gender/nationality ✓ · (b) ✓ · (c) ✓ · (e) canonical (footbridge) ✓ · (f) 3 sentences ✓ · (g) ✓ |
| dil_lifeboat — Lifeboat overcrowding, personal, unhurried | (a) "injured passenger"/"unconscious passenger" — neutral ✓ · (b) "injured" describes a state, not a group identity; the choice isn't "kill the injured because injured" ✓ · (c) ✓ · (e) canonical (lifeboat / Holmes-style) ✓ · (f) 3 sentences ✓ · (g) ✓ |
| dil_hospital — Organ harvest, personal, unhurried | (a) "five patients"/"healthy visitor" — role-only ✓ · (b) ✓ · (c) ✓ · (e) canonical (hospital/organ harvest) ✓ · (f) 2 sentences ✓ · (g) ✓ |
| dil_drowning_child — Drowning child, impersonal, hurried | (a) "small child" — role-only, no demographic detail ✓ · (b) child is the *rescued* party, not the sacrificed one ✓ · (c) ✓ · (e) canonical (Singer's drowning child) ✓ · (f) 2 sentences ✓ · (g) ✓ |
| dil_switch_remote — Remote routing, impersonal, hurried | (a) "commuter train"/"one worker" — role-only ✓ · (b) ✓ · (c) ✓ · (e) variant of trolley/lever, canonical ✓ · (f) 2 sentences ✓ · (g) ✓ |

Composition: 2 impersonal + 4 personal across 6 dilemmas; 2 of those are
on a 6000 ms clock (`hurried: true` on dil_drowning_child and
dil_switch_remote). No dilemma uses a marginalized identity as the
sacrificed party.

---

## Overall

- `make check-lexicon` is green against `content/rounds/read/scenarios.json`
  and `content/rounds/dilemma/dilemmas.json`.
- All scenarios and dilemmas pass criteria (a)–(g).
- The "heavy stranger" body-type descriptor in the footbridge dilemma is
  retained because it is load-bearing to the canonical contrast between
  pulling a lever and pushing a body; it is the only physical descriptor
  in the entire set and is not paired with any other identity marker.
- No deviations from Phase 2 brief.
