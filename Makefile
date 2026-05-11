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
