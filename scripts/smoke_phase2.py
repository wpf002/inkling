"""Phase 2 smoke test.

Walks the full six-round flow against an in-process FastAPI app:

  1. Create a session.
  2. Submit self-report.
  3. For each round in manifest order:
       - Emit a synthetic event stream that exercises every scorer.
       - POST /round-complete.
  4. Query the inferences table for the session.
  5. Assert exactly 17 rows: 3 (choice) + 4 (pursuit) + 3 (trust)
                          + 3 (memory) + 2 (read) + 2 (dilemma).

Exits 0 on success, non-zero with a message identifying the silent
scorer on failure.

Default: in-memory aiosqlite (fast, CI-friendly). To run against the
live dev postgres, set `INKLING_SMOKE_DB_URL` — see `make verify-db`.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "api"))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core import database as db_module  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.inference import Inference  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.services.content import load_round_manifest  # noqa: E402

EXPECTED_PER_ROUND = {
    "choice": 3,
    "pursuit": 4,
    "trust": 3,
    "memory": 3,
    "read": 2,
    "dilemma": 2,
}
EXPECTED_TOTAL = sum(EXPECTED_PER_ROUND.values())


def _choice_events() -> list[dict]:
    GAMBLES = {
        g["id"]: g
        for g in json.loads(
            (REPO_ROOT / "content" / "rounds" / "choice" / "gambles.json").read_text()
        )["gambles"]
    }
    trials = [
        ("g1", "unhurried", "decline", 1500),
        ("g2", "unhurried", "take", 1400),
        ("g3", "unhurried", "take", 1300),
        ("g4", "unhurried", "take", 1200),
        ("g1", "hurried", "decline", 900),
        ("g2", "hurried", "decline", 800),
        ("g3", "hurried", "take", 700),
        ("g4", "hurried", "take", 700),
    ]
    out: list[dict] = []
    t = 0
    for i, (gid, cond, choice, rt) in enumerate(trials):
        g = GAMBLES[gid]
        trial_key = f"{cond}:{gid}"
        out.append({
            "event_type": "gamble_shown",
            "payload": {
                "trial": trial_key, "gamble_id": gid, "condition": cond,
                "win": g["win"], "lose": g["lose"],
            },
            "t_ms": t,
        })
        t += rt
        out.append({
            "event_type": "choice",
            "payload": {
                "trial": trial_key, "gamble_id": gid, "condition": cond,
                "value": choice, "rt_ms": rt,
            },
            "t_ms": t,
        })
        t += 50 + i
    return out


def _pursuit_events() -> list[dict]:
    content = json.loads(
        (REPO_ROOT / "content" / "rounds" / "pursuit" / "trials.json").read_text()
    )
    trials = content["trials"]
    spike_indices = content["spike_indices"]
    out: list[dict] = [
        {"event_type": "round_start",
         "payload": {"spike_indices": spike_indices, "trials_count": len(trials)},
         "t_ms": 0},
    ]
    t = 0
    for i, trial in enumerate(trials):
        rt = 540 if (trial["target_type"] == "valid" and i not in spike_indices) else 720
        out.append({
            "event_type": "trial_shown",
            "payload": {
                "trial": trial["id"], "index": i,
                "target_type": trial["target_type"],
                "window_ms": trial["window_ms"],
            },
            "t_ms": t,
        })
        t += rt
        if trial["target_type"] == "valid":
            out.append({
                "event_type": "click",
                "payload": {
                    "trial": trial["id"], "index": i,
                    "target_type": "valid", "rt_ms": rt,
                },
                "t_ms": t,
            })
        else:
            out.append({
                "event_type": "miss",
                "payload": {
                    "trial": trial["id"], "index": i,
                    "target_type": "distractor", "rt_ms": None,
                },
                "t_ms": t,
            })
        t += 350
    return out


def _trust_events() -> list[dict]:
    content = json.loads(
        (REPO_ROOT / "content" / "rounds" / "trust" / "npcs.json").read_text()
    )
    out: list[dict] = []
    t = 0
    plays = [5, 5, 5, 5, 6, 2, 7, 5]
    receipts = [8, 1, 11, 6, 9, 0, 15, 4]
    for i, trial in enumerate(content["trials"]):
        out.append({
            "event_type": "trial_shown",
            "payload": {
                "trial_id": trial["trial_id"], "npc_id": trial["npc_id"],
                "first": trial["first"],
            },
            "t_ms": t,
        })
        t += 100
        out.append({
            "event_type": "send_amount",
            "payload": {
                "trial_id": trial["trial_id"], "npc_id": trial["npc_id"],
                "amount": plays[i],
            },
            "t_ms": t,
        })
        t += 50
        out.append({
            "event_type": "outcome_revealed",
            "payload": {
                "trial_id": trial["trial_id"], "npc_id": trial["npc_id"],
                "received": receipts[i], "sent": plays[i],
            },
            "t_ms": t,
        })
        t += 50
    return out


def _memory_events() -> list[dict]:
    out: list[dict] = [
        {"event_type": "round_start",
         "payload": {"start_span": 3, "grid_size": 9},
         "t_ms": 0},
    ]
    trials = [
        (3, True,  [600, 700, 650]),
        (3, True,  [620, 690, 660]),
        (4, True,  [700, 720, 700, 750]),
        (4, True,  [680, 710, 690, 720]),
        (5, True,  [800, 820, 800, 830, 810]),
        (5, False, [900, 910, 950, 980, 1000]),
        (6, False, [1100, 1200, 1100, 1300, 1200, 1400]),
    ]
    t = 100
    for i, (span, correct, rts) in enumerate(trials):
        tid = f"m{i + 1:02d}"
        out.append({
            "event_type": "sequence_shown",
            "payload": {"trial_id": tid, "span": span},
            "t_ms": t,
        })
        t += 1000
        out.append({
            "event_type": "response",
            "payload": {
                "trial_id": tid, "span": span, "correct": correct,
                "tap_rts_ms": rts,
            },
            "t_ms": t,
        })
        t += 300
    return out


def _read_events() -> list[dict]:
    scenarios = json.loads(
        (REPO_ROOT / "content" / "rounds" / "read" / "scenarios.json").read_text()
    )["scenarios"]
    out: list[dict] = []
    t = 0
    for i, s in enumerate(scenarios):
        out.append({
            "event_type": "scenario_shown",
            "payload": {"scenario_id": s["id"], "index": i},
            "t_ms": t,
        })
        t += 4500
        opt = s["options"][i % len(s["options"])]
        out.append({
            "event_type": "option_selected",
            "payload": {
                "scenario_id": s["id"], "index": i,
                "option_id": opt["id"], "tags": opt["tags"],
                "rt_ms": 4500,
            },
            "t_ms": t,
        })
        t += 200
    return out


def _dilemma_events() -> list[dict]:
    dilemmas = json.loads(
        (REPO_ROOT / "content" / "rounds" / "dilemma" / "dilemmas.json").read_text()
    )["dilemmas"]
    out: list[dict] = []
    t = 0
    for i, d in enumerate(dilemmas):
        out.append({
            "event_type": "dilemma_shown",
            "payload": {
                "dilemma_id": d["id"], "type": d["type"], "hurried": d["hurried"],
            },
            "t_ms": t,
        })
        t += 3500
        pick = "utilitarian" if i % 2 == 0 else "deontological"
        out.append({
            "event_type": "option_selected",
            "payload": {
                "dilemma_id": d["id"], "type": d["type"],
                "hurried": d["hurried"], "selected": pick, "rt_ms": 3500,
            },
            "t_ms": t,
        })
        t += 200
    return out


EVENT_BUILDERS = {
    "choice": _choice_events,
    "pursuit": _pursuit_events,
    "trust": _trust_events,
    "memory": _memory_events,
    "read": _read_events,
    "dilemma": _dilemma_events,
}


async def run() -> int:
    db_url = os.environ.get("INKLING_SMOKE_DB_URL")
    is_sqlite = db_url is None
    if is_sqlite:
        db_url = "sqlite+aiosqlite:///:memory:"

    eng = create_async_engine(db_url, future=True)
    if is_sqlite:
        async with eng.begin() as conn:
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=eng, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with factory() as s:
            if is_sqlite:
                await s.execute(text("PRAGMA foreign_keys=ON"))
            yield s

    db_module._engine = eng
    db_module._session_factory = factory
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    failures: list[str] = []
    created_session_id: uuid.UUID | None = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = f"smoke-{uuid.uuid4()}"
            resp = await client.post(
                "/sessions",
                json={
                    "consent": {
                        "gameplay": True, "interaction_patterns": True,
                        "self_report": True, "retain_profile_7d": True,
                        "research_aggregate": False,
                    },
                    "age_attested": True,
                    "anonymous_token": token,
                },
            )
            assert resp.status_code == 201, resp.text
            created_session_id = uuid.UUID(resp.json()["session_id"])

            # Self-report (use items.json).
            items = json.loads(
                (REPO_ROOT / "content" / "self_report" / "items.json").read_text()
            )["items"]
            resp = await client.post(
                f"/sessions/{token}/self-report",
                json={
                    "responses": [
                        {"item_id": it["id"], "response": 3} for it in items
                    ],
                },
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 201, resp.text

            manifest = load_round_manifest()
            for r in manifest["rounds"]:
                rid = r["id"]
                events = EVENT_BUILDERS[rid]()
                # Post in batches ≤ 200 to obey MAX_EVENTS_PER_BATCH.
                for chunk_start in range(0, len(events), 200):
                    chunk = events[chunk_start : chunk_start + 200]
                    resp = await client.post(
                        f"/sessions/{token}/round-events",
                        json={"round": rid, "events": chunk},
                        headers={"X-Inkling-Session": token},
                    )
                    assert resp.status_code == 201, (rid, resp.text)
                resp = await client.post(
                    f"/sessions/{token}/round-complete",
                    json={"round": rid},
                    headers={"X-Inkling-Session": token},
                )
                assert resp.status_code == 200, (rid, resp.text)

            # Count inferences for *this session only* — on a shared
            # postgres we mustn't count rows from prior runs.
            async with factory() as session:
                rows = (
                    await session.execute(
                        select(Inference).where(
                            Inference.session_id == created_session_id
                        )
                    )
                ).scalars().all()

            per_round_counts: dict[str, int] = {}
            constructs_by_round: dict[str, set[str]] = {}
            for round_def in manifest["rounds"]:
                constructs_by_round[round_def["id"]] = set(round_def["constructs"])
            constructs_present: dict[str, list[Any]] = {}
            for row in rows:
                for rid, names in constructs_by_round.items():
                    if row.construct in names:
                        per_round_counts[rid] = per_round_counts.get(rid, 0) + 1
                        constructs_present.setdefault(rid, []).append(row.construct)
                        break

            for rid, expected in EXPECTED_PER_ROUND.items():
                actual = per_round_counts.get(rid, 0)
                if actual != expected:
                    missing = constructs_by_round[rid] - set(
                        constructs_present.get(rid, [])
                    )
                    failures.append(
                        f"  {rid}: expected {expected}, got {actual} "
                        f"(missing constructs: {sorted(missing)})"
                    )

            total = len(rows)
            if total != EXPECTED_TOTAL:
                failures.append(
                    f"  total: expected {EXPECTED_TOTAL}, got {total}"
                )
    finally:
        # On postgres, leave the DB as we found it — cascade-delete the
        # session we created. In-memory sqlite vanishes with the engine.
        if not is_sqlite and created_session_id is not None:
            async with factory() as session:
                await session.execute(
                    delete(SessionModel).where(SessionModel.id == created_session_id)
                )
                await session.commit()
        app.dependency_overrides.clear()
        await eng.dispose()

    if failures:
        print("smoke_phase2 FAILED:")
        for line in failures:
            print(line)
        return 1
    print(f"smoke_phase2 OK — {EXPECTED_TOTAL} inference rows persisted")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
