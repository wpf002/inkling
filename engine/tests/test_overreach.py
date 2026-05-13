"""Engine tests for the Overreach LLM scorer.

The Anthropic SDK is fully mocked. We exercise:
  - prompt assembly given a synthetic session_summary
  - lexicon-filter retry behavior on a forbidden-term mock response
  - lexicon-filter redaction on a second failure
  - cost estimation
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from inkling_engine.llm import overreach as overreach_module
from inkling_engine.llm.lexicon_filter import REDACTED_PLACEHOLDER
from inkling_engine.llm.prompts import (
    PROMPT_VERSION,
    build_system_prompt,
    build_user_prompt,
    load_forbidden_terms,
)


def _ok_payload(extra_blurb: str = "Methodical and confident.") -> dict[str, Any]:
    return {
        "big_five": {
            "O": {"score": 60, "blurb": "Curious about new tools and frames."},
            "C": {"score": 70, "blurb": extra_blurb},
            "E": {"score": 45, "blurb": "Selective about social investment."},
            "A": {"score": 55, "blurb": "Even-keeled in cooperative play."},
            "N": {"score": 40, "blurb": "Steady under timed pressure."},
        },
        "political_values": "Center-pragmatic with a preference for outcome-led frames.",
        "life_history": "Late-stage career, partnered, college-educated.",
        "consumer_profile": "Premium subscription tolerant, late-cycle adopter.",
    }


def _bad_payload() -> dict[str, Any]:
    p = _ok_payload()
    # Insert a forbidden term verbatim into one Big Five blurb.
    forbidden = load_forbidden_terms()[0]  # e.g., "psychopath"
    p["big_five"]["N"]["blurb"] = (
        f"Reads as a borderline {forbidden} under stress, with strong cues."
    )
    return p


class FakeAnthropicClient:
    """Mock Anthropic client. .messages.create returns a SimpleNamespace
    that mimics the SDK's Message shape."""

    def __init__(self, responses: list[dict[str, Any]], usage_in: int = 1200, usage_out: int = 400):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.usage_in = usage_in
        self.usage_out = usage_out

        # Minimal nested attribute structure: client.messages.create(...)
        outer = self
        class _Messages:
            def create(self, **kwargs: Any) -> Any:  # noqa: D401
                outer.calls.append(kwargs)
                if not outer._responses:
                    raise RuntimeError("no more mocked responses")
                payload = outer._responses.pop(0)
                text = json.dumps(payload, separators=(",", ":"))
                return SimpleNamespace(
                    content=[SimpleNamespace(text=text)],
                    usage=SimpleNamespace(
                        input_tokens=outer.usage_in,
                        output_tokens=outer.usage_out,
                    ),
                )
        self.messages = _Messages()


SYNTHETIC_SUMMARY = {
    "inferences": [
        {"construct": "loss_aversion", "tier": "high", "value": {"lambda": 2.3}, "confidence": 0.7},
        {"construct": "risk_tolerance", "tier": "high", "value": {"overall_take_rate": 0.45}, "confidence": 0.9},
    ],
    "self_report": [
        {"item_id": "sr01", "response": 4},
        {"item_id": "sr02", "response": 5},
    ],
    "round_event_counts": {"choice": 16, "pursuit": 60},
}


def test_build_system_prompt_includes_forbidden_terms():
    prompt = build_system_prompt()
    terms = load_forbidden_terms()
    assert "Forbidden vocabulary" in prompt
    # At least the first three terms should appear verbatim.
    for t in terms[:3]:
        assert t in prompt


def test_build_system_prompt_extends_with_extra_terms():
    prompt = build_system_prompt(extra_forbidden=["custom-bad-word"])
    assert "custom-bad-word" in prompt


def test_build_user_prompt_includes_summary_inputs():
    prompt = build_user_prompt(SYNTHETIC_SUMMARY)
    assert "INPUTS" in prompt
    assert "loss_aversion" in prompt
    assert "sr01" in prompt


def test_score_overreach_happy_path():
    client = FakeAnthropicClient([_ok_payload()])
    result = overreach_module.score_overreach(SYNTHETIC_SUMMARY, client=client, model="test-model")
    assert len(client.calls) == 1
    inf = result.inference
    assert inf.construct == "overreach"
    assert inf.tier == "overreach"
    assert inf.confidence == 0.5
    assert inf.evidence["model"] == "test-model"
    assert inf.evidence["prompt_version"] == PROMPT_VERSION
    assert inf.evidence["retried_on_lexicon"] is False
    assert inf.evidence["input_token_count"] == 1200
    assert inf.evidence["output_token_count"] == 400
    assert result.cost_usd > 0


def test_score_overreach_retries_on_lexicon_hit_and_succeeds():
    client = FakeAnthropicClient([_bad_payload(), _ok_payload()])
    result = overreach_module.score_overreach(SYNTHETIC_SUMMARY, client=client, model="test-model")
    # Two calls were made: original + one retry.
    assert len(client.calls) == 2
    inf = result.inference
    # The persisted payload should be clean (the second mock).
    assert inf.evidence["retried_on_lexicon"] is True
    bad_term = load_forbidden_terms()[0]
    serialized = json.dumps(inf.value)
    assert bad_term.lower() not in serialized.lower()


def test_score_overreach_redacts_when_second_attempt_also_fails():
    client = FakeAnthropicClient([_bad_payload(), _bad_payload()])
    result = overreach_module.score_overreach(SYNTHETIC_SUMMARY, client=client, model="test-model")
    assert len(client.calls) == 2
    blurb = result.inference.value["big_five"]["N"]["blurb"]
    assert blurb == REDACTED_PLACEHOLDER


def test_no_anthropic_key_raises_config_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(overreach_module.OverreachConfigError):
        # No client passed → tries to construct one and fails.
        overreach_module.score_overreach(SYNTHETIC_SUMMARY, client=None)


def test_registry_shim_refuses_event_invocation():
    # The "overreach" entry in the registry is a shim that should refuse
    # event-stream invocation.
    from inkling_engine import score_round
    with pytest.raises(NotImplementedError):
        score_round("overreach", [])
