"""Pricer unit tests for Layer 5."""
from __future__ import annotations

from inkling_engine.reveal import pricing

HIGH_INFS = [
    {"construct": "loss_aversion", "tier": "high", "value": {}, "confidence": 0.7},
    {"construct": "risk_tolerance", "tier": "high", "value": {}, "confidence": 0.9},
    {"construct": "reaction_time_profile", "tier": "high", "value": {}, "confidence": 0.8},
]
MEDIUM_INFS = [
    {"construct": "stress_response", "tier": "medium", "value": {}, "confidence": 0.4},
    {"construct": "frustration_tolerance", "tier": "medium", "value": {}, "confidence": 0.5},
]


def test_price_only_round_inferences_no_overreach():
    result = pricing.price_profile(HIGH_INFS + MEDIUM_INFS, overreach_value=None)
    # 3 * 0.010 + 2 * 0.005 = 0.040 base, * 1.25 premium = 0.050
    assert result["raw_subtotal"] == 0.04
    assert result["total"] == 0.05
    assert len(result["components"]) == 5


def test_price_with_overreach_includes_traits_and_paragraphs():
    overreach_val = {
        "big_five": {
            "O": {"score": 50, "blurb": "x"},
            "C": {"score": 50, "blurb": "x"},
            "E": {"score": 50, "blurb": "x"},
            "A": {"score": 50, "blurb": "x"},
            "N": {"score": 50, "blurb": "x"},
        },
        "political_values": "p",
        "life_history": "l",
        "consumer_profile": "c",
    }
    result = pricing.price_profile(HIGH_INFS + MEDIUM_INFS, overreach_value=overreach_val)
    # base 0.04 + 5 * 0.020 (traits) + 0.020 (political) + 0.020 (life)
    # + 0.050 (consumer) = 0.04 + 0.10 + 0.04 + 0.05 = 0.23
    assert abs(result["raw_subtotal"] - 0.23) < 1e-9
    assert abs(result["total"] - 0.2875) < 1e-6
    constructs = {c["construct"] for c in result["components"]}
    assert "big_five.O" in constructs
    assert "consumer_profile" in constructs


def test_price_handles_empty_inputs():
    result = pricing.price_profile([], overreach_value=None)
    assert result["raw_subtotal"] == 0.0
    assert result["total"] == 0.0
    assert result["components"] == []
