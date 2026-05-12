# Inference Constructs

Every construct Inkling claims to measure must be defined here before it ships.
Constructs are tiered by empirical confidence.

## Format
- **Name**
- **Tier** (high / medium / overreach)
- **Definition**
- **Operationalization** — exact game data → score
- **Validity notes** — what's known
- **Reveal framing** — how it's shown to the player

---

## Tier 1: High confidence

### Loss aversion
- **Tier**: high
- **Definition**: Subjective weight of losses vs equal-magnitude gains
- **Operationalization**: Fit λ from Choice-round gambles where utility = gain^α − λ·loss^β. Use ~8 mixed gambles spanning a 4× range.
- **Validity**: Kahneman/Tversky prospect theory; replicated extensively. Typical population λ ≈ 2.0–2.5.
- **Framing**: "Losses feel about Nx as bad as equivalent gains to you. Population average: ~2x."

### Reaction time profile
- **Tier**: high
- **Definition**: Distribution of correct-hit RTs on a timed visual-search task (Pursuit).
- **Operationalization**: Median, coefficient of variation (sd/mean), p10, and p90 across all valid hits in Round 2.
- **Validity**: Standard psychophysics. RT distributions are stable within-subject across short tasks.
- **Citations**: standard psychophysics RT literature.
- **Framing**: "Your median reaction time was ~N ms; the gap between your fastest and slowest tenth is M ms."

### Sustained attention
- **Tier**: high
- **Definition**: Vigilance decrement — whether RTs slow as the round wears on.
- **Operationalization**: Linear regression of correct-hit RT against trial index in Round 2. Slope (ms/trial) and R² are reported; first- and second-half medians are exposed for the reveal.
- **Validity**: Mackworth (1948) vigilance task; replicated repeatedly. Single short rounds give noisy slope estimates.
- **Citations**: Mackworth, N. H. (1948). The breakdown of vigilance during prolonged visual search.
- **Framing**: "Across the round your reaction time changed by ~N ms per trial."

### Working memory span
- **Tier**: high
- **Definition**: Largest sequence the player can correctly reproduce on a Corsi block-tapping task.
- **Operationalization**: Round 4 starts at span 3, two trials per span, increments on success; max span with ≥1 correct trial is reported.
- **Validity**: Corsi (1972); Kessels et al. (2000) for population norms. Robust short-form measure.
- **Citations**: Corsi, P. M. (1972); Kessels et al. (2000), Assessment, 7, 252–258.
- **Framing**: "You held a sequence of N positions in working memory."

### Processing speed
- **Tier**: high
- **Definition**: Mean per-tap reaction time in the Corsi response, normalized by the span being reproduced.
- **Operationalization**: Mean of all `response.tap_rts_ms` values across Round 4 trials; normalized speed scales by median span observed.
- **Validity**: Standard psychophysics. Span-normalization keeps comparisons fair when players differ in max span reached.
- **Citations**: standard psychophysics RT literature.
- **Framing**: "Your mean tap interval was ~N ms."

### Attribution style
- **Tier**: high
- **Definition**: Hostile-vs-benign and internal-vs-external attribution biases for ambiguous social events.
- **Operationalization**: Round 5 options are tagged on two axes. Aggregate proportion of hostile-tagged choices (`hostile_score`) and internal-tagged choices (`internal_score`).
- **Validity**: Weiner (1985) attribution model; Crick & Dodge (1994) hostile attribution bias in social information processing. Short forms are noisy but the axes themselves are well-validated.
- **Citations**: Weiner (1985), Psychological Review, 92, 548–573; Crick & Dodge (1994), Psychological Bulletin, 115, 74–101.
- **Framing**: "On the eight social scenarios, your readings leaned [hostile/benign] and [internal/external]."

---

## Tier 2: Medium confidence

### Stress response
- **Tier**: medium
- **Definition**: Change in choice behavior under time pressure.
- **Operationalization**: Round 1 hurried-vs-unhurried within-subject deltas in take rate and reaction time, with directional consistency across gamble pairs.
- **Citations**: time-pressure decision literature (e.g., Edland & Svenson, 1993).
- **Framing**: "Under the clock, your take rate shifted by N percentage points."

### Frustration tolerance
- **Tier**: medium
- **Definition**: Performance change immediately after a difficulty spike.
- **Operationalization**: Round 2 includes five trials whose window drops sharply. Post-spike vs pre-spike RT delta and miss-rate delta, averaged across the five spikes; confidence reflects directional consistency.
- **Validity**: Frustration-aggression literature (Rosenzweig 1944); modern variants in attention-control research. Confounded with task difficulty.
- **Citations**: Rosenzweig, S. (1944). An outline of frustration theory.
- **Framing**: "After a sharp difficulty jump, your RT shifted by N ms on average."

### Response inhibition
- **Tier**: medium
- **Definition**: Ability to withhold a planned response when the stimulus signals "do not act."
- **Operationalization**: Round 2 includes distractor frames. False-alarm rate on distractors and hit rate on valid targets.
- **Validity**: Logan & Cowan (1984) stop-signal paradigm. Six distractor frames is a thin slice; reported as a behavioral summary, not a clinical measure.
- **Citations**: Logan, G. D., & Cowan, W. B. (1984). On the ability to inhibit thought and action.
- **Framing**: "You clicked on N% of decoy frames."

### Initial trust propensity
- **Tier**: high
- **Definition**: First-encounter trust offer to an unknown partner.
- **Operationalization**: Round 3 mean amount sent on each NPC's first interaction (4 NPCs), with the SD across partners.
- **Validity**: Berg, Dickhaut & McCabe (1995) trust game. Strong baseline; small sample (4 partners) limits between-subject precision.
- **Citations**: Berg, Dickhaut & McCabe (1995), Games and Economic Behavior, 10, 122–142.
- **Framing**: "On first contact with an unknown partner you sent $N of $10 on average."

### Adaptation rate
- **Tier**: medium
- **Definition**: How strongly the previous return shapes the next send to the same partner.
- **Operationalization**: Round 3 correlation between received-on-N and sent-on-N+1, across the 4 same-partner pairs.
- **Validity**: King-Casas et al. (2005) iterated trust dynamics. With only 4 pairs the correlation is noisy.
- **Citations**: King-Casas et al. (2005), Science, 308, 78–83.
- **Framing**: "Your next send tracked what you just received with correlation r=N."

### Retaliation tendency
- **Tier**: medium
- **Definition**: Send-amount drop on the trial after a partner returned little.
- **Operationalization**: Round 3 mean (sent on N+1 − baseline send) on events where the previous return was below 20% of the tripled amount.
- **Validity**: Fehr & Gächter (2000) costly punishment. Single-shot reciprocal retaliation; not generalizable to extended cooperation.
- **Citations**: Fehr & Gächter (2000), American Economic Review, 90, 980–994.
- **Framing**: "After a partner kept most of what you sent, your next send dropped by $N."

### Performance under load
- **Tier**: medium
- **Definition**: Drop in accuracy as Corsi span exceeds the start span by 3.
- **Operationalization**: Round 4 accuracy at start_span minus accuracy at start_span + 3.
- **Validity**: Baddeley & Hitch (1974) working memory model — load past span produces sharp drop. Drop-magnitude is informative; the exact threshold is not.
- **Citations**: Baddeley & Hitch (1974), Psychology of Learning and Motivation, 8, 47–89.
- **Framing**: "From a 3-block sequence to a 6-block sequence, your accuracy dropped by N points."

### Deliberation on ambiguous input
- **Tier**: medium
- **Definition**: Within-subject change in response time across an ambiguous-attribution task.
- **Operationalization**: Round 5 mean RT; deliberation index = (second-half mean − first-half mean) / first-half mean.
- **Validity**: Krajbich et al. (2010) drift-diffusion model of evidence accumulation. Within-subject baselines are noisy; we floor confidence at 0.7.
- **Citations**: Krajbich, Armel & Rangel (2010), Nature Neuroscience, 13, 1292–1298.
- **Framing**: "Your second-half scenarios took N% [longer/shorter] than your first-half ones."

### Utilitarian leaning
- **Tier**: medium
- **Definition**: Proportion of utilitarian-coded responses across moral dilemmas.
- **Operationalization**: Round 6 utilitarian_rate, with personal and impersonal sub-rates.
- **Validity**: Greene et al. (2001) personal/impersonal moral dilemma framework. Kahane et al. (2018) note the utilitarian/deontological dichotomy conflates multiple constructs (oddly-named "utilitarianism" vs concern-for-the-greater-good vs cognitive style); we report behavior, not moral type.
- **Citations**: Greene et al. (2001), Science, 293, 2105–2108; Kahane et al. (2018), Psychological Review, 125, 131–164.
- **Framing**: "You chose the more-lives option on N of 6 dilemmas." With a note that this is a behavioral summary, not a moral classification.

### Personal-vs-impersonal sensitivity
- **Tier**: medium
- **Definition**: Difference in utilitarian-choice rate between impersonal and personal dilemmas.
- **Operationalization**: Round 6 sensitivity_delta = util_impersonal_rate − util_personal_rate.
- **Validity**: Greene et al. (2004) personal/impersonal contrast. Robust effect at the population level; weaker within-subject across only 6 dilemmas.
- **Citations**: Greene et al. (2004), Neuron, 44, 389–400.
- **Framing**: "When the action was hands-off, you picked the more-lives option N points more often than when it was hands-on."

---

## Tier 3: Overreach (the lesson)

### Big Five personality
- **Tier**: overreach
- **Definition**: Standard Big Five traits inferred from gameplay alone
- **Operationalization**: LLM passes the full gameplay log + scores the player on OCEAN
- **Validity**: Inferring Big Five from gameplay alone has weak empirical support. The point of this construct is to demonstrate confident inference on thin evidence.
- **Framing**: First show the LLM's confident Big Five readout. Then show the evidence breakdown. Then show how data brokers sell exactly this inference at scale.

### Political affiliation
- TODO

### Past life events / autobiographical guesses
- TODO

---

## DO NOT IMPLEMENT
- Mental health diagnostic claims
- Sexual orientation inference
- Truthfulness / honesty detection
- Specific PII reconstruction
