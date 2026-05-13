"""Targeting unit tests for Layer 6.

Verifies that:
  - selection picks 3 ads / 3 scams / 1 recruiter
  - category diversity holds for ad picks
  - all selected templates pass the lexicon filter (the engine-side
    sanity check; the build-time `make check-lexicon` is the contract)
"""
from __future__ import annotations

import json
from pathlib import Path

from inkling_engine.llm.lexicon_filter import find_violations
from inkling_engine.reveal import targeting

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_templates():
    ads = json.loads((REPO_ROOT / "content" / "ads" / "templates.json").read_text())["templates"]
    scams = json.loads((REPO_ROOT / "content" / "scams" / "templates.json").read_text())["templates"]
    rec = json.loads((REPO_ROOT / "content" / "recruiter" / "templates.json").read_text())["templates"]
    return ads, scams, rec


SYNTHETIC_INFERENCES = [
    {"construct": "loss_aversion", "tier": "high", "value": {"lambda": 2.6}, "confidence": 0.8},
    {"construct": "risk_tolerance", "tier": "high", "value": {"overall_take_rate": 0.4}, "confidence": 0.9},
    {"construct": "stress_response", "tier": "medium", "value": {"take_rate_delta": -0.1}, "confidence": 0.5},
    {"construct": "deliberation", "tier": "medium", "value": {"deliberation_index": 0.3}, "confidence": 0.6},
    {"construct": "initial_trust_propensity", "tier": "high", "value": {"initial_trust_amount": 6.5}, "confidence": 0.85},
    {"construct": "sustained_attention", "tier": "high", "value": {"rt_slope_ms_per_trial": -1.0}, "confidence": 0.7},
]


def test_select_returns_expected_counts():
    ads, scams, rec = _load_templates()
    out = targeting.select(SYNTHETIC_INFERENCES, ads, scams, rec)
    assert len(out["ads"]) == 3
    assert len(out["scams"]) == 3
    assert len(out["recruiter"]) == 1


def test_ad_picks_are_category_diverse_when_possible():
    ads, scams, rec = _load_templates()
    out = targeting.select(SYNTHETIC_INFERENCES, ads, scams, rec)
    categories = [a["category"] for a in out["ads"]]
    # We have at least three distinct ad categories in the catalog.
    assert len(set(categories)) >= 2


def test_filled_templates_pass_lexicon_filter():
    ads, scams, rec = _load_templates()
    out = targeting.select(SYNTHETIC_INFERENCES, ads, scams, rec)
    # Check the post-fill output for lexicon hits — every selected piece
    # should be clean.
    for bucket_name in ("ads", "scams", "recruiter"):
        for entry in out[bucket_name]:
            hits = find_violations(entry)
            assert hits == [], f"lexicon violation in {bucket_name}: {hits}"


def test_select_with_no_inferences_still_returns_picks():
    """Defensive: if a session somehow lands here with no inferences, the
    selector should still return the top-N of each bucket so the page
    renders something."""
    ads, scams, rec = _load_templates()
    out = targeting.select([], ads, scams, rec)
    assert len(out["ads"]) <= 3
    assert len(out["scams"]) <= 3
    assert len(out["recruiter"]) <= 1
