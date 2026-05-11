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

### Reaction time distribution
- TODO

### Working memory capacity
- TODO

### Trust propensity
- TODO

---

## Tier 2: Medium confidence

### Cognitive style (intuitive vs deliberative)
- TODO

### Frustration tolerance
- TODO

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
