"""Overreach scorer: one LLM call per session → one Inference row.

The flow:
  1. Build system + user prompt from a session_summary dict.
  2. Call Claude Sonnet via the Anthropic SDK (one request).
  3. Parse the model's JSON response.
  4. Run the parsed payload through the lexicon filter.
  5. On any filter hit, retry once with the matched terms appended to
     the forbidden list. On the second failure, redact the offending
     blurb to a placeholder string and persist.
  6. Return (Inference, cost_estimate_usd, usage_dict) so the API layer
     can track daily spend and persist token counts in evidence.

The scorer is registered in the runner registry for symmetry. The
registered adapter raises on round-event input — overreach is invoked
explicitly with a session_summary, not events.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from inkling_engine.llm.lexicon_filter import (
    find_violations,
    redact_violations,
)
from inkling_engine.llm.prompts import (
    PROMPT_VERSION,
    build_system_prompt,
    build_user_prompt,
)
from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.scoring.runner import register_scorer

logger = logging.getLogger("inkling.engine.overreach")

DEFAULT_MODEL = "claude-sonnet-4-6"
INPUT_TOKEN_CAP = 6000
OUTPUT_TOKEN_CAP = 1500
TEMPERATURE = 0.8

# Sonnet 4.6 published pricing (USD per million tokens). The API layer
# uses these to update the daily_spend table.
SONNET_INPUT_USD_PER_M = 3.0
SONNET_OUTPUT_USD_PER_M = 15.0


class OverreachConfigError(RuntimeError):
    """Raised when the Anthropic client cannot be constructed."""


@dataclass
class OverreachResult:
    inference: Inference
    cost_usd: float
    input_tokens: int
    output_tokens: int


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        (input_tokens / 1_000_000.0) * SONNET_INPUT_USD_PER_M
        + (output_tokens / 1_000_000.0) * SONNET_OUTPUT_USD_PER_M
    )


def _extract_text(message: Any) -> str:
    """Pull the assistant text out of an Anthropic Message response.

    The SDK returns a `Message` with a `content` list of content blocks.
    For a text-only request we expect a single TextBlock; we join all
    text blocks defensively.
    """
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


def _parse_payload(text: str) -> dict[str, Any]:
    """Strict JSON parse with one fallback for stray fences."""
    s = text.strip()
    if s.startswith("```"):
        # Some models occasionally wrap JSON in a code fence despite
        # being told not to. Strip the outermost fence.
        s = s.strip("`")
        # remove possible "json\n" prefix from the fence header
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    return json.loads(s)


def _default_client() -> Any:
    """Construct an Anthropic client from env, lazily.

    Imported lazily so engine tests that mock the client never need the
    real SDK initialized.
    """
    try:
        from anthropic import Anthropic  # type: ignore
    except ImportError as e:
        raise OverreachConfigError(
            "anthropic SDK not installed — pip install anthropic"
        ) from e
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise OverreachConfigError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


def _call_model(
    client: Any,
    system_prompt: str,
    user_prompt: str,
    model: str,
) -> tuple[str, int, int]:
    """Issue one messages.create call. Returns (text, in_tokens, out_tokens)."""
    response = client.messages.create(
        model=model,
        max_tokens=OUTPUT_TOKEN_CAP,
        temperature=TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = _extract_text(response)
    usage = getattr(response, "usage", None)
    in_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    out_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return text, in_tokens, out_tokens


def score_overreach(
    session_summary: dict[str, Any],
    client: Any | None = None,
    model: str | None = None,
) -> OverreachResult:
    """Generate one Overreach Inference for a session.

    Caller is responsible for idempotency: check for an existing
    `construct="overreach"` row before invoking this function.
    """
    model_name = model or os.environ.get("OVERREACH_MODEL", DEFAULT_MODEL)
    if client is None:
        client = _default_client()

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(session_summary)

    text, in_tokens, out_tokens = _call_model(
        client, system_prompt, user_prompt, model_name
    )
    parsed = _parse_payload(text)

    hits = find_violations(parsed)
    retried = False
    if hits:
        retried = True
        matched_terms = sorted({h.term for h in hits})
        logger.warning(
            "overreach_lexicon_hit model=%s prompt_version=%s terms=%s",
            model_name,
            PROMPT_VERSION,
            matched_terms,
        )
        retry_system = build_system_prompt(extra_forbidden=matched_terms)
        text2, in2, out2 = _call_model(
            client, retry_system, user_prompt, model_name
        )
        in_tokens += in2
        out_tokens += out2
        parsed = _parse_payload(text2)
        hits = find_violations(parsed)
        if hits:
            logger.warning(
                "overreach_lexicon_hit_after_retry model=%s prompt_version=%s "
                "terms=%s — redacting offending fields",
                model_name,
                PROMPT_VERSION,
                sorted({h.term for h in hits}),
            )
            parsed = redact_violations(parsed, hits)

    cost = _estimate_cost_usd(in_tokens, out_tokens)
    inference = Inference(
        construct="overreach",
        tier="overreach",
        value=parsed,
        confidence=0.5,
        evidence={
            "model": model_name,
            "input_token_count": in_tokens,
            "output_token_count": out_tokens,
            "prompt_version": PROMPT_VERSION,
            "retried_on_lexicon": retried,
            "estimated_cost_usd": round(cost, 6),
        },
    )
    return OverreachResult(
        inference=inference,
        cost_usd=cost,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
    )


# Registry adapter — the runner expects a function that takes events
# and returns inferences. Overreach takes a session_summary, so the
# registered shim refuses event-based invocation and exists only so
# `registered_rounds()` reports "overreach" alongside the real rounds.
def _registry_shim(_events: Iterable[RoundEventDTO]) -> list[Inference]:
    raise NotImplementedError(
        "overreach is not scored from a round-event stream — call "
        "inkling_engine.llm.overreach.score_overreach(session_summary)."
    )


register_scorer("overreach", _registry_shim)
