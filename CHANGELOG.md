# Changelog

## Phase 1 — Round 1 (Choice) end-to-end (2026-05-11)

### Phase 1 added

- **Content**: `content/rounds/choice/gambles.json` — the only round-1-specific
  authoring artifact. Four gambles spanning the loss-aversion indifference
  range (g/l ratios 0.67 → 4.0), each played in both `unhurried` and
  `hurried` (4 s clock) conditions for 8 trials total.
- **Engine** (`engine/src/inkling_engine`):
  - Round-agnostic registry: `register_scorer(round_id, fn)` /
    `score_round(round_id, events)`.
  - Pydantic v2 `Inference` and `RoundEventDTO`. `Inference.value` is
    structured JSON; the reveal layer formats it.
  - `rules/choice.py` emits three inferences:
    - **loss_aversion** (high) — λ from MLE on
      EU = 0.5·win^α − 0.5·λ·lose^α with α fixed at 0.88, β fit jointly,
      confidence = 1 − (residual / null) deviance, evidence flags
      `unidentified` and `underpowered`.
    - **risk_tolerance** (high) — overall and per-condition take rate.
    - **stress_response** (medium) — within-subject hurried−unhurried
      delta, confidence from directional consistency across the 4 gamble
      pairs.
  - The engine package self-registers each round inside `rules/__init__.py`
    so `engine/__init__.py` and `scoring/runner.py` stay round-agnostic.
- **API** (`api/app`):
  - `POST /sessions/{token}/round-events` — batch ingest (≤200 events),
    validates round against `content/rounds/manifest.json`.
  - `POST /sessions/{token}/round-complete` — synchronous in-process
    scoring, idempotent (repeat calls return existing inferences without
    duplicating rows).
  - `GET /sessions/{token}/inferences?round=...` — reveal fetch.
  - `GET /content/round-gambles?round=...` — public round content endpoint.
  - `services/events.py` and `services/scoring.py` keep routers thin.
  - `inkling-engine` wired as a uv path source (`editable = true`).
- **Web** (`web/src`):
  - Reusable round infrastructure (round-agnostic):
    - `lib/eventCapture.ts` — `useEventCapture(round, token)` queues events,
      auto-flushes every 2 s or every 20 events, stamps `t_ms` since mount.
    - `components/round/CountdownRing.tsx` — SVG ring with `onExpire`.
    - `components/round/Stage.tsx` — generic round shell (title, progress,
      framer-motion crossfade between trials).
  - Round-1-specific: `app/round/choice/page.tsx` shuffles condition-block
    order and gamble order, captures `gamble_shown`, `choice`, `abandon`,
    `mouse_sample` (10 Hz), and `hover_enter`/`hover_leave` events. On the
    last trial it flushes, posts `/round-complete`, and navigates to
    the reveal stub.
  - `app/reveal-stub/page.tsx` formats each inference per
    `docs/inferences.md` framing rules with a confidence band.
- **Tests**:
  - 9 engine cases covering low/population/high λ players, all-take and
    all-decline degenerate fits, an underpowered (4-abandon) player,
    risk-tolerance per-condition, and consistent vs noisy stress-response
    deltas.
  - 12 new API cases covering round-event batch ingest, header auth,
    payload validation, age-attestation gating, unknown-round 400s,
    round-complete writing exactly three inference rows of tiers
    high/high/medium, idempotency, and the reveal-fetch endpoint.
- **Lint guard**: `make check-round-agnostic` greps the reusable layers
  for any of the six round ids in the manifest and fails the build on
  match. Wired into `make lint`.
- **macOS quirk fix**: `make fix-venv-pth` strips the `UF_HIDDEN` flag
  from `.pth` files in the api and engine venvs. Python 3.14's `site.py`
  silently skips hidden `.pth` files, which made the editable
  inkling-engine install invisible until cleared. Now runs as a
  prerequisite of `lint` and `test`.

### Phase 1 changed

- `make test` now runs both api and engine pytest suites.
- `web/src/app/self-report/page.tsx` navigates to `/round/choice`
  on success (replacing the old `/phase-1-stub` redirect).

### Phase 1 removed

- `web/src/app/phase-1-stub` — superseded by the real Round 1 page.

## Phase 0 — Consent + self-report (2026-05-11)

### Phase 0 added

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

### Phase 0 notes

- `make dev` now runs `make migrate` before starting the API.
- `make test` runs the API suite only (engine has no tests yet).
