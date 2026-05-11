# Inkling

A consent-first behavioral profiling game. Players opt in, play six short rounds, and watch the game show them — tier by tier — what it inferred from how they played. Then it walks them through how that same data would be weaponized by a covert version of itself: data broker product cards, targeted ad simulations, scam vulnerability profiles, and recruiter pitches.

The educational payoff is the gap between fluent inference and thin evidence.

## What this is
- A privacy-awareness demonstration that makes the threat **viscerally personal**.
- A red-team simulation of how covert behavioral profiling works, run on the player themselves with their permission.
- A research/coaching tool for understanding within-subject behavioral signal.

## What this is not
- Not a covert data-mining game. The covert version is what we critique, not what we build.
- Not a personality test. The game makes inferences across three tiers and is **honest about which ones are real**.
- Not sold to advertisers, never. The point would collapse.

## The game (~15 minutes)
1. **Choice** — gambles, hurried + unhurried (loss aversion, risk tolerance, stress response)
2. **Pursuit** — timed visual task (attention, reaction time, frustration tolerance)
3. **Trust** — cooperation game vs NPCs (trust propensity, retaliation)
4. **Memory** — n-back / pattern recall (working memory, processing speed)
5. **Read** — ambiguous social scenarios (attribution style)
6. **Dilemma** — trolley variants (moral utilitarian vs deontological, fairness)

Before play: 60-second self-report (10 Likert items). This is the baseline for the divergence reveal.

## The reveal (~12 minutes, this is the product)
1. **Stated vs Revealed** — gap between self-report and gameplay
2. **High-confidence inferences** — with evidence and math
3. **Medium-confidence inferences** — with explicit confidence bands
4. **Overreach** — LLM-generated personality/politics/biography guesses, shown confidently first, then dismantled
5. **Profile-as-product** — your data formatted as a broker card with a price
6. **Targeting simulation** — 3 personalized ads, 3 scams, 1 recruiter pitch
7. **Defense** — opt-outs, tools, links
8. **Share card** — auto-generated image for screenshot virality

## Stack
| Layer | Choice |
|---|---|
| Web | Next.js 15 (App Router), TypeScript, Tailwind, Framer Motion |
| API | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Engine | Python 3.11, numpy, scipy (rule-based) + Anthropic SDK (overreach layer) |
| DB | Postgres 16 |
| Pkg mgmt | pnpm (web), uv (Python) |
| Deploy | Railway |

No object storage, no auth required for play, no third-party trackers. Anonymous-by-default sessions.

## Quickstart

```bash
git clone git@github.com:<you>/inkling.git
cd inkling
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
make dev
```

Web on http://localhost:3000, API on http://localhost:8000.

## Project structure
```
inkling/
├── web/           Next.js frontend
├── api/           FastAPI service
├── engine/        Python inference package
│   └── src/inkling_engine/
│       ├── rules/      rule-based scoring (numpy/scipy)
│       ├── llm/        LLM overreach layer
│       ├── scoring/    construct → score pipelines
│       └── reveal/     reveal-layer assembly
├── content/       authored game content (JSON/YAML)
│   ├── self_report/    Likert items
│   ├── rounds/         round definitions
│   ├── dilemmas/       moral dilemma library
│   ├── ads/            ad templates for targeting sim
│   ├── scams/          scam templates
│   └── recruiter/      recruiter pitch templates
├── infra/         docker-compose
├── docs/          consent, inferences, reveal sequence
├── scripts/       bootstrap and dev scripts
└── Makefile       common tasks
```

## Common tasks
| Command | Action |
|---|---|
| `make up` | Start Postgres |
| `make api` | Run FastAPI on :8000 |
| `make web` | Run Next.js on :3000 |
| `make dev` | Start infra + web + api |
| `make migrate` | Run alembic migrations |
| `make fmt` | Format all code |
| `make lint` | Type-check + lint everything |
| `make test` | Run pytest across api + engine |
| `make psql` | Drop into the dev DB |

## Roadmap

### Phase 0 — Foundation (week 1)
- [ ] Complete `docs/consent.md`, `docs/inferences.md`, `docs/reveal-sequence.md`
- [ ] DB schema + alembic migrations
- [ ] Consent flow UI
- [ ] Self-report UI

### Phase 1 — First round end-to-end (weeks 2–3)
- [ ] Round 1 (Choice) UI
- [ ] Behavioral event capture (timing, hesitation, abandons)
- [ ] Rule-based engine: loss aversion scorer
- [ ] Minimal reveal showing just Round 1 output

### Phase 2 — Remaining rounds (weeks 4–5)
- [ ] Pursuit, Trust, Memory, Read, Dilemma — each follows Round 1's pattern

### Phase 3 — The reveal (weeks 6–7)
- [ ] Stated vs Revealed layer
- [ ] All inference tiers
- [ ] LLM overreach layer
- [ ] Targeting simulation
- [ ] Share card generation

### Phase 4 — Launch (week 8)
- [ ] Railway deploy (web + api + postgres)
- [ ] Rate limiting
- [ ] Analytics (Plausible, no PII)
- [ ] Soft launch

## Ethical guardrails
1. **Consent is itemized, not blanket.** Each data category gets its own checkbox.
2. **No PII collected by default.** No name, no email, no fingerprint, no cross-site.
3. **Sessions auto-delete after 7 days.** Aggregate research requires separate post-reveal consent.
4. **No third-party trackers.** No ad pixels on the site. The irony would be fatal.
5. **The overreach tier is labeled overreach.** Never sold as truth.
6. **No real targeting.** Ads/scams/recruiter pitches in the simulation are generated locally for the player only and never delivered or stored as real targeting data.

## License
Commercial, all rights reserved.
