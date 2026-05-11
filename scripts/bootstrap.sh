#!/usr/bin/env bash
# Inkling — infrastructure bootstrap
# Creates folder structure, initializes Next.js + FastAPI + engine package,
# wires docker-compose for Postgres, and writes env scaffolding.
#
# Run from inside the empty inkling/ directory:
#   chmod +x scripts/bootstrap.sh
#   ./scripts/bootstrap.sh

set -euo pipefail

PROJECT_NAME="inkling"

echo "==> Checking prerequisites..."
command -v node    >/dev/null 2>&1 || { echo "FAIL: node 20+ required"; exit 1; }
command -v pnpm    >/dev/null 2>&1 || { echo "FAIL: pnpm required (npm i -g pnpm)"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python 3.11+ required"; exit 1; }
command -v uv      >/dev/null 2>&1 || { echo "FAIL: uv required (curl -LsSf https://astral.sh/uv/install.sh | sh)"; exit 1; }
command -v docker  >/dev/null 2>&1 || { echo "FAIL: docker required"; exit 1; }

echo "==> Creating folder structure..."
mkdir -p web api engine content infra/migrations docs scripts
mkdir -p api/app/{routers,services,models,schemas,core}
mkdir -p engine/src/inkling_engine/{rules,llm,scoring,reveal}
mkdir -p engine/tests
mkdir -p content/{rounds,dilemmas,ads,scams,recruiter,self_report}

# ---------- Web (Next.js) ----------
echo "==> Initializing Next.js (web)..."
if [ ! -f web/package.json ]; then
  cd web
  pnpm create next-app@latest . \
    --ts --tailwind --app --src-dir \
    --import-alias "@/*" --no-eslint --use-pnpm --yes
  pnpm add zod @tanstack/react-query lucide-react framer-motion html2canvas
  pnpm add -D @types/node prettier
  cd ..
fi

# ---------- API (FastAPI) ----------
echo "==> Initializing FastAPI (api)..."
if [ ! -f api/pyproject.toml ]; then
  cd api
  uv init --no-readme --no-workspace
  uv add "fastapi[standard]" "uvicorn[standard]" \
         "sqlalchemy[asyncio]" asyncpg alembic \
         pydantic pydantic-settings python-multipart \
         anthropic httpx python-jose[cryptography]
  uv add --dev pytest pytest-asyncio ruff mypy
  cd ..
fi

# ---------- Engine (inference package) ----------
echo "==> Initializing engine package..."
if [ ! -f engine/pyproject.toml ]; then
  cd engine
  uv init --no-readme --no-workspace --package
  uv add numpy scipy pydantic anthropic
  uv add --dev pytest ruff
  cd ..
fi

# ---------- Infra ----------
echo "==> Writing docker-compose..."
cat > infra/docker-compose.yml <<'YAML'
services:
  postgres:
    image: postgres:16-alpine
    container_name: ink_postgres
    environment:
      POSTGRES_USER: inkling
      POSTGRES_PASSWORD: inkling
      POSTGRES_DB: inkling
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U inkling"]
      interval: 5s
      retries: 10

volumes:
  postgres_data:
YAML

# ---------- Makefile ----------
echo "==> Writing Makefile..."
cat > Makefile <<'MAKE'
.PHONY: up down web api engine dev fmt lint test logs psql migrate

up:
	docker compose -f infra/docker-compose.yml up -d
	@echo "postgres :5432"

down:
	docker compose -f infra/docker-compose.yml down

web:
	cd web && pnpm dev

api:
	cd api && uv run uvicorn app.main:app --reload --port 8000

engine:
	cd engine && uv run python -m inkling_engine

dev: up
	@$(MAKE) -j2 web api

fmt:
	cd web && pnpm prettier --write .
	cd api && uv run ruff format .
	cd engine && uv run ruff format .

lint:
	cd web && pnpm tsc --noEmit
	cd api && uv run ruff check . && uv run mypy app
	cd engine && uv run ruff check .

test:
	cd api && uv run pytest -q
	cd engine && uv run pytest -q

logs:
	docker compose -f infra/docker-compose.yml logs -f

psql:
	docker exec -it ink_postgres psql -U inkling -d inkling

migrate:
	cd api && uv run alembic upgrade head
MAKE

# ---------- Env ----------
echo "==> Writing .env.example..."
cat > .env.example <<'ENV'
# === Database ===
DATABASE_URL=postgresql+asyncpg://inkling:inkling@localhost:5432/inkling

# === API ===
API_BASE_URL=http://localhost:8000
API_SECRET_KEY=replace-with-output-of-openssl-rand-hex-32

# === Web ===
NEXT_PUBLIC_API_URL=http://localhost:8000

# === LLM (overreach layer) ===
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

# === Session / Privacy ===
SESSION_TTL_DAYS=7
AGE_GATE_MIN=18
ENV
[ ! -f .env ] && cp .env.example .env

# ---------- Minimal API entry ----------
echo "==> Writing minimal FastAPI entry..."
cat > api/app/main.py <<'PY'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Inkling API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
PY
touch api/app/__init__.py
for d in routers services models schemas core; do touch "api/app/$d/__init__.py"; done

# ---------- Content seed files ----------
echo "==> Seeding content/ scaffolds..."
cat > content/self_report/items.json <<'JSON'
{
  "items": [
    {"id": "sr01", "construct": "risk_tolerance",     "prompt": "I'm comfortable making decisions with incomplete information.", "scale": "likert_5"},
    {"id": "sr02", "construct": "loss_aversion",      "prompt": "Losing $100 feels worse than gaining $100 feels good.",         "scale": "likert_5"},
    {"id": "sr03", "construct": "trust",              "prompt": "Most people can be trusted in a one-time interaction.",         "scale": "likert_5"},
    {"id": "sr04", "construct": "fairness",           "prompt": "I'd punish unfair behavior even at a cost to myself.",          "scale": "likert_5"},
    {"id": "sr05", "construct": "attribution",        "prompt": "When someone is short with me, they usually mean it personally.","scale": "likert_5"},
    {"id": "sr06", "construct": "deliberation",       "prompt": "I prefer to think things through rather than go with my gut.",  "scale": "likert_5"},
    {"id": "sr07", "construct": "moral_utilitarian",  "prompt": "Outcomes matter more than rules.",                              "scale": "likert_5"},
    {"id": "sr08", "construct": "stress_response",    "prompt": "Tight deadlines bring out my best work.",                       "scale": "likert_5"},
    {"id": "sr09", "construct": "attention",          "prompt": "I notice small details others miss.",                           "scale": "likert_5"},
    {"id": "sr10", "construct": "novelty",            "prompt": "I'd rather try something new than stick with what I know works.","scale": "likert_5"}
  ]
}
JSON

cat > content/rounds/manifest.json <<'JSON'
{
  "rounds": [
    {"id": "choice",  "title": "Choice",  "duration_s": 180, "constructs": ["loss_aversion", "risk_tolerance", "stress_response"]},
    {"id": "pursuit", "title": "Pursuit", "duration_s": 120, "constructs": ["attention", "reaction_time", "frustration"]},
    {"id": "trust",   "title": "Trust",   "duration_s": 180, "constructs": ["trust", "retaliation"]},
    {"id": "memory",  "title": "Memory",  "duration_s": 120, "constructs": ["working_memory", "processing_speed"]},
    {"id": "read",    "title": "Read",    "duration_s": 180, "constructs": ["attribution"]},
    {"id": "dilemma", "title": "Dilemma", "duration_s": 180, "constructs": ["moral_utilitarian", "fairness"]}
  ]
}
JSON

# ---------- Docs scaffolds ----------
echo "==> Writing docs scaffolds..."
cat > docs/consent.md <<'MD'
# Consent Flow

The single most important UX in Inkling. If consent is sloppy, the entire educational frame collapses and the product becomes the thing it critiques.

## Principles
1. **Itemized, not blanket.** Each data category gets its own checkbox.
2. **Opt-out by default for anything non-essential.** Research aggregate requires explicit second consent post-reveal.
3. **No dark patterns.** No pre-checked boxes, no buried fine print, no "are you sure?" friction on opt-outs.
4. **Plain English.** No legalese. The consent screen is also part of the lesson.
5. **Reversible.** Players can delete their session at any point, including after the reveal.

## Data categories (each gets its own checkbox)
- [ ] Gameplay choices and timing
- [ ] Cursor and interaction patterns (hover, hesitation, abandons)
- [ ] Self-report responses
- [ ] Inferred profile retained for 7 days for re-viewing (default: yes; can opt out → session destroyed at session end)
- [ ] Anonymous aggregate research use (default: NO; post-reveal opt-in only)

## What we never collect
- Name, email (unless they opt into an account post-reveal)
- IP address beyond rate-limit purposes
- Browser fingerprint
- Anything cross-site

## Age gate
- 18+ self-attestation. Hard gate, not a checkbox among others.
MD

cat > docs/inferences.md <<'MD'
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
MD

cat > docs/reveal-sequence.md <<'MD'
# Reveal Sequence

The actual product is the reveal. Gameplay is the data-gathering preamble.

## Pacing principle
Each layer is 30s–3m. Auto-advance with a "continue" gate the player taps so they're in control. Music shifts subtly between high-confidence and overreach sections.

## Layer 1 — Stated vs Revealed (30s)
- Show the player's self-report responses next to their gameplay-derived equivalents.
- Highlight the largest divergences.
- This is the punch — it sets up everything that follows.

## Layer 2 — High-confidence inferences (2m)
- Show ~4 inferences from the high-confidence tier.
- Each one displays the evidence: which game choices produced the score, the math.
- Example: "Loss aversion λ = 2.3 — derived from these 8 choices →"

## Layer 3 — Medium-confidence inferences (2m)
- Same format, weaker certainty bands.
- Explicit confidence scores.

## Layer 4 — Overreach (3m)
- LLM-generated personality / politics / biography inferences.
- Shown with deliberately confident framing FIRST.
- Then the evidence breakdown showing how thin the actual signal is.
- This is the educational core.

## Layer 5 — Profile-as-product (1m)
- The player's profile formatted as a data-broker product card.
- Includes a fictional but realistic price tag.

## Layer 6 — Targeting simulation (2m)
- 3 personalized ads generated for them.
- 3 scams they'd be most vulnerable to.
- 1 recruiter pitch tailored to their inferred ambitions.
- All clearly labeled SIMULATION.

## Layer 7 — Defense (1m)
- Opt-outs (data broker registry, ad personalization, etc.)
- Tools
- Links

## Layer 8 — Share card (30s)
- Auto-generated image
- "Inkling guessed I'm X — and got Y% of it right."
- Designed for screenshot virality. No tracking in the share.
MD

echo ""
echo "==> Done. Next steps:"
echo "  1. make up        # start postgres"
echo "  2. make api       # FastAPI on :8000"
echo "  3. make web       # Next.js on :3000 (separate terminal)"
echo "  4. Open docs/consent.md, docs/inferences.md, docs/reveal-sequence.md"
echo "     and complete them before building any UI."
