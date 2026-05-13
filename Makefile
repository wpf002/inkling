.PHONY: up down web api engine dev fmt lint check-round-agnostic check-lexicon fix-venv-pth test smoke-phase2 smoke-phase3 check-phase3 verify-db logs psql migrate revision

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

dev:
	@bash scripts/dev.sh

fmt:
	cd web && pnpm prettier --write .
	cd api && uv run ruff format .
	cd engine && uv run ruff format .

lint: check-round-agnostic check-lexicon fix-venv-pth
	cd web && pnpm tsc --noEmit
	cd api && uv run ruff check .
	cd engine && uv run ruff check .

# Reusable layers must not mention any specific round id. The grep matches
# whole-word against the six round ids in content/rounds/manifest.json — when
# you add a new round to the manifest, extend the alternation here.
check-round-agnostic:
	@echo "==> Checking reusable layers are round-agnostic..."
	@! grep -rEwn "choice|pursuit|trust|memory|read|dilemma" \
	    web/src/lib/eventCapture.ts \
	    web/src/components/round/CountdownRing.tsx \
	    web/src/components/round/Stage.tsx \
	    engine/src/inkling_engine/scoring/runner.py \
	    engine/src/inkling_engine/__init__.py \
	    api/app/routers/round_events.py \
	    api/app/routers/round_complete.py \
	    2>/dev/null || (echo "FAIL: round name in reusable layer" && exit 1)
	@echo "OK"

# Lexicon enforcement: every player-facing surface, every scorer file,
# every docstring needs to stay inside the allowed framings in
# docs/lexicon.md. The grep is intentionally case-insensitive and
# whole-word against the forbidden vocabulary; the doc itself is
# excluded so the rules can be documented without tripping the rule.
# Phase 3 adds a second exclusion: content/reveal/forbidden_lexicon.json
# is the JSON source of truth that the Overreach LLM prompt and the
# post-generation filter both load — it must enumerate the strings
# verbatim, same as docs/lexicon.md.
check-lexicon:
	@echo "==> Checking lexicon compliance..."
	@! grep -rEnw -i \
	    "psychopath|sociopath|narcissist|gaslight|toxic person|inner child|healing journey|MBTI|enneagram|empath|love language|triggered|trauma\b|traumatic|traumatized|disorder|diagnosis|pathological|comorbid" \
	    web/src content engine/src api/app docs 2>/dev/null \
	    | grep -v "docs/lexicon.md" \
	    | grep -v "content/reveal/forbidden_lexicon.json" \
	    || (echo "FAIL: forbidden lexicon term found (see docs/lexicon.md)" && exit 1)
	@echo "OK"

# macOS quirk: uv-built venvs sometimes get the UF_HIDDEN flag on .pth
# files, which makes Python 3.14's site.py silently skip them — and the
# editable inkling-engine install becomes invisible. Strip the flag.
fix-venv-pth:
	@command -v chflags >/dev/null && \
	  chflags -R nohidden api/.venv engine/.venv 2>/dev/null || true

test: fix-venv-pth
	cd api && uv run pytest -q
	cd engine && uv run pytest -q

# Phase 2 smoke test: walks the full round flow (synthetic events,
# round-complete after each round) against a running API on :8000 and
# asserts the inferences table has exactly 17 rows for the session.
smoke-phase2:
	cd api && uv run python ../scripts/smoke_phase2.py

# Phase 3 smoke test: extends smoke-phase2 with the 8-layer reveal —
# asserts stated_vs_revealed, overreach (mocked LLM), broker_pricing,
# targeting, share_card creation, and 8 reveal_layer_entered events.
smoke-phase3:
	cd api && uv run python ../scripts/smoke_phase3.py

# Phase 3 phase-completion check: run lint (round-agnostic + lexicon),
# the engine + API tests, and the Phase 3 smoke. Fails fast on the
# first non-zero step.
check-phase3: lint test smoke-phase3
	@echo "==> Phase 3 phase-completion checks OK"

# Same smoke flow, run against the live dev postgres on :5433. Asserts
# 17 inference rows for the new session and cascade-deletes the session
# at the end so the dev DB is left as we found it.
verify-db:
	cd api && INKLING_SMOKE_DB_URL=postgresql+asyncpg://inkling:inkling@localhost:5433/inkling \
	  uv run python ../scripts/smoke_phase2.py

logs:
	docker compose -f infra/docker-compose.yml logs -f

psql:
	docker exec -it ink_postgres psql -U inkling -d inkling

migrate:
	cd api && uv run alembic upgrade head

revision:
	cd api && uv run alembic revision --autogenerate -m "$(m)"
