# Changelog

## Phase 0 — Consent + self-report (2026-05-11)

### Added
- **Database**: Alembic + async SQLAlchemy. Initial migration creates
  `sessions`, `self_reports`, `round_events`, `inferences`, `share_cards`,
  `research_optins` with `ON DELETE CASCADE` from `sessions` and
  `session_id` indexes on every child table.
- **API**:
  - `POST /sessions` — create anonymous session with itemized consent
    payload and 18+ attestation.
  - `GET /sessions/{token}` — return sanitized session state.
  - `DELETE /sessions/{token}` — soft delete + background hard delete
    that cascades to all child rows.
  - `POST /sessions/{token}/self-report` — validate item IDs against
    `content/self_report/items.json`; rejected when
    `age_attested = false` or self-report already submitted.
  - `GET /content/self-report-items` — public endpoint serving the
    authored Likert items.
  - All session-scoped endpoints require an `X-Inkling-Session` header
    that must match the path token.
  - Lifespan-on-startup health check probes the DB so misconfigs are
    loud.
- **Web (Next.js 16 App Router, Tailwind v4)**:
  - `/` — pitch + 18+ gate.
  - `/consent` — itemized consent screen, plain-English explanations,
    research opt-in unchecked by default.
  - `/self-report` — 10 Likert items rendered from the API content
    endpoint, never hardcoded.
  - `/phase-1-stub` — terminal stub for Phase 0.
  - Anonymous token generated client-side with `crypto.randomUUID()`,
    persisted in `localStorage` under `inkling.session_token`.
  - `react-query` for fetching, `zod` schemas mirror the API,
    Framer Motion for page/item fade-ins.
- **Tests**: pytest suite covering session creation, consent
  persistence, header enforcement, self-report happy path, age
  rejection, unknown item rejection, and soft+hard delete cascade.
- **Tooling**: `.vscode/` workspace settings pointing Python and Ruff
  at `api/.venv`; isort extension disabled in favor of ruff's `I`
  rules.

### Notes
- `make dev` now runs `make migrate` before starting the API.
- `make test` runs the API suite only (engine has no tests yet).
