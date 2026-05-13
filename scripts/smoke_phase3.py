"""Phase 3 smoke test.

Walks the full Phase 2 round flow and then exercises every Phase 3
reveal endpoint against an in-process FastAPI app:

  1. Re-uses the Phase 2 smoke flow to land 17 round inferences.
  2. POST /sessions/{token}/stated-vs-revealed  → +1 inference row
  3. POST /sessions/{token}/overreach            → +1 inference row
                                                   (mocked LLM)
  4. POST /sessions/{token}/broker-pricing       → +1 inference row
  5. GET  /sessions/{token}/targeting            → 3 ads / 3 scams / 1 pitch
  6. POST /sessions/{token}/share-card           → +1 share_cards row
  7. POST /sessions/{token}/reveal-event x 7     → 7 reveal_level_entered
                                                   rows in round_events
                                                   (one per level)

Asserts:
  - inferences row count for the session is exactly 20
    (17 round + stated_vs_revealed + overreach + broker_pricing)
  - share_cards row count for the session is 1
  - reveal_level_entered events for levels 1..7 all present

Exits 0 on success.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "api"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

import smoke_phase2  # noqa: E402  (re-uses event builders)
from app.core import database as db_module  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.inference import Inference  # noqa: E402
from app.models.round_event import RoundEvent  # noqa: E402
from app.models.session import Session as SessionModel  # noqa: E402
from app.models.share_card import ShareCard  # noqa: E402
from app.services.content import load_round_manifest  # noqa: E402

CLEAN_OVERREACH = {
    "big_five": {
        "O": {"score": 60, "blurb": "Curious about new tools and frames."},
        "C": {"score": 70, "blurb": "Methodical when stakes rise."},
        "E": {"score": 45, "blurb": "Selective about social investment."},
        "A": {"score": 55, "blurb": "Even-keeled in cooperative play."},
        "N": {"score": 40, "blurb": "Steady under timed pressure."},
    },
    "political_values": "Center-pragmatic with a preference for outcome-led frames.",
    "life_history": "Late-stage career, partnered, college-educated.",
    "consumer_profile": "Premium subscription tolerant, late-cycle adopter.",
}


def _patch_overreach() -> None:
    """Replace the engine's score_overreach with a deterministic mock."""
    from inkling_engine.llm import overreach as engine_overreach
    from inkling_engine.llm.overreach import OverreachResult
    from inkling_engine.models import Inference as EngineInference

    def _fake(_summary: dict, **_: Any) -> OverreachResult:
        return OverreachResult(
            inference=EngineInference(
                construct="overreach",
                tier="overreach",
                value=CLEAN_OVERREACH,
                confidence=0.5,
                evidence={
                    "model": "smoke-mock",
                    "input_token_count": 1200,
                    "output_token_count": 400,
                    "prompt_version": "smoke-vN",
                    "retried_on_lexicon": False,
                    "estimated_cost_usd": 0.0096,
                },
            ),
            cost_usd=0.0096,
            input_tokens=1200,
            output_tokens=400,
        )

    engine_overreach.score_overreach = _fake  # type: ignore[assignment]


async def run() -> int:
    import os
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
    _patch_overreach()

    failures: list[str] = []
    transport = ASGITransport(app=app)
    created_session_id: uuid.UUID | None = None

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = f"smoke3-{uuid.uuid4()}"
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
            import json as _json
            items = _json.loads(
                (REPO_ROOT / "content" / "self_report" / "items.json").read_text()
            )["items"]
            resp = await client.post(
                f"/sessions/{token}/self-report",
                json={"responses": [{"item_id": it["id"], "response": 3} for it in items]},
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 201, resp.text

            # Walk the rounds via the Phase 2 builders.
            manifest = load_round_manifest()
            for r in manifest["rounds"]:
                rid = r["id"]
                events = smoke_phase2.EVENT_BUILDERS[rid]()
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

            # --- Phase 3 reveal endpoints ---

            for level in range(1, 8):
                resp = await client.post(
                    f"/sessions/{token}/reveal-event",
                    json={
                        "event_type": "reveal_level_entered",
                        "payload": {"level": level},
                        "t_ms": level * 1000,
                    },
                    headers={"X-Inkling-Session": token},
                )
                assert resp.status_code == 201, ("reveal_event", level, resp.text)

            resp = await client.post(
                f"/sessions/{token}/stated-vs-revealed",
                json={},
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["inference"] is not None

            resp = await client.post(
                f"/sessions/{token}/overreach",
                json={},
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["cached"] is False

            resp = await client.post(
                f"/sessions/{token}/broker-pricing",
                json={},
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 200, resp.text

            resp = await client.get(
                f"/sessions/{token}/targeting",
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 200, resp.text
            t_body = resp.json()
            if len(t_body["ads"]) != 3:
                failures.append(f"  targeting: expected 3 ads, got {len(t_body['ads'])}")
            if len(t_body["scams"]) != 3:
                failures.append(f"  targeting: expected 3 scams, got {len(t_body['scams'])}")
            if len(t_body["recruiter"]) != 1:
                failures.append(f"  targeting: expected 1 pitch, got {len(t_body['recruiter'])}")

            resp = await client.post(
                f"/sessions/{token}/share-card",
                json={
                    "image_dimensions": "1080x1920",
                    "headline": "Loss aversion: A $10 loss feels like a $20 win",
                    "inference_id": None,
                },
                headers={"X-Inkling-Session": token},
            )
            assert resp.status_code == 201, resp.text

            # --- Assert final DB state ---
            async with factory() as s:
                inferences = (
                    await s.execute(
                        select(Inference).where(
                            Inference.session_id == created_session_id
                        )
                    )
                ).scalars().all()
                share_cards = (
                    await s.execute(
                        select(ShareCard).where(
                            ShareCard.session_id == created_session_id
                        )
                    )
                ).scalars().all()
                reveal_events = (
                    await s.execute(
                        select(RoundEvent).where(
                            RoundEvent.session_id == created_session_id,
                            RoundEvent.round == "reveal",
                        )
                    )
                ).scalars().all()

            EXPECTED_INF = 17 + 3  # 17 from rounds, +stated_vs_revealed +overreach +broker_pricing
            if len(inferences) != EXPECTED_INF:
                failures.append(
                    f"  inferences: expected {EXPECTED_INF}, got {len(inferences)}"
                )
            constructs_present = {i.construct for i in inferences}
            for c in ("stated_vs_revealed", "overreach", "broker_pricing"):
                if c not in constructs_present:
                    failures.append(f"  inferences: missing construct '{c}'")
            if len(share_cards) != 1:
                failures.append(
                    f"  share_cards: expected 1, got {len(share_cards)}"
                )
            if len(reveal_events) != 7:
                failures.append(
                    f"  reveal events: expected 7, got {len(reveal_events)}"
                )

    finally:
        if created_session_id is not None:
            async with factory() as s:
                await s.execute(
                    delete(SessionModel).where(SessionModel.id == created_session_id)
                )
                await s.commit()
        app.dependency_overrides.clear()
        await eng.dispose()

    if failures:
        print("smoke_phase3 FAILED:")
        for line in failures:
            print(line)
        return 1
    print("smoke_phase3 OK — all 7 levels reachable, 20 inferences + 1 share_card")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))


# Silence the unused SimpleNamespace import — kept for future use when
# a richer mock is needed.
_ = SimpleNamespace
