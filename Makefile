.PHONY: up down web api engine dev fmt lint check-round-agnostic fix-venv-pth test logs psql migrate revision

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

lint: check-round-agnostic fix-venv-pth
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

# macOS quirk: uv-built venvs sometimes get the UF_HIDDEN flag on .pth
# files, which makes Python 3.14's site.py silently skip them — and the
# editable inkling-engine install becomes invisible. Strip the flag.
fix-venv-pth:
	@command -v chflags >/dev/null && \
	  chflags -R nohidden api/.venv engine/.venv 2>/dev/null || true

test: fix-venv-pth
	cd api && uv run pytest -q
	cd engine && uv run pytest -q

logs:
	docker compose -f infra/docker-compose.yml logs -f

psql:
	docker exec -it ink_postgres psql -U inkling -d inkling

migrate:
	cd api && uv run alembic upgrade head

revision:
	cd api && uv run alembic revision --autogenerate -m "$(m)"
