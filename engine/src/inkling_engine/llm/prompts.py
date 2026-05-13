"""Prompt assembly for the Overreach LLM call.

The system prompt enumerates forbidden vocabulary verbatim by loading
`content/reveal/forbidden_lexicon.json` at module-import time. This file
contains no hardcoded forbidden terms — the JSON content file is the
single source of truth, and that file is excluded from `make
check-lexicon` the same way `docs/lexicon.md` is excluded.

`PROMPT_VERSION` is recorded in each persisted Inference's evidence
column. Bump it whenever the system prompt template changes substantively
so prompt iteration history is auditable from the database.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

PROMPT_VERSION = "overreach-2026-05-12-v1"

# Walk up from this file to the repo root. The engine package lives at
# `engine/src/inkling_engine/llm/prompts.py`, four parents above the
# repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_LEXICON_JSON = _REPO_ROOT / "content" / "reveal" / "forbidden_lexicon.json"


@lru_cache(maxsize=1)
def load_forbidden_terms() -> tuple[str, ...]:
    """Return the canonical forbidden-term list from the JSON content file."""
    raw = json.loads(_LEXICON_JSON.read_text())
    return tuple(raw["terms"])


def _format_forbidden_list(extra: list[str] | None = None) -> str:
    items = list(load_forbidden_terms())
    if extra:
        existing = {t.lower() for t in items}
        for term in extra:
            if term and term.lower() not in existing:
                items.append(term)
                existing.add(term.lower())
    return "\n".join(f"  - {t}" for t in items)


_SYSTEM_PROMPT_TEMPLATE = """\
You are simulating a data-broker profiling product card. The card is sold
to advertisers as a confident, fluent psychographic readout of a single
anonymous person, inferred from a short behavioral game and a 10-item
self-report.

This card is part of an educational reveal that shows the player what
covert behavioral profiling actually looks like. The fluent overreach is
the entire lesson — you are deliberately overconfident on thin evidence.

Output rules:

1. Style: fluent, confident, marketing-grade prose. Make every claim
   sound like a finished product, not a research caveat. No hedging:
   never write "might", "could", "may", "possibly", "perhaps", "appears
   to", "seems", or any similar softener.

2. Every claim must reference at least one specific value from the
   inputs (a construct name, a score, a self-report answer). The flimsy
   linking is part of the lesson — pick a value, name it, and lean on it.

3. Forbidden vocabulary. The following terms are out for this product.
   Do not use them in any form (lowercase, capitalized, hyphenated, or
   as part of a longer compound):
{forbidden}

4. Do not produce mental-health diagnostic claims, including via
   euphemism. No descriptions of clinical syndromes, no implied
   diagnoses, no "symptoms of" framing.

5. Do not invent specific PII. No real-looking full names, no exact
   street addresses, no specific employer names, no specific schools,
   no real-looking phone numbers or email addresses. "Late-stage career"
   is allowed; "Senior Director at Acme Corp" is not.

6. Output ONLY valid minified JSON matching this schema. No prose
   outside the JSON object. No markdown fences. No commentary.

JSON schema:

{{
  "big_five": {{
    "O": {{"score": <int 0-100>, "blurb": "<one sentence>"}},
    "C": {{"score": <int 0-100>, "blurb": "<one sentence>"}},
    "E": {{"score": <int 0-100>, "blurb": "<one sentence>"}},
    "A": {{"score": <int 0-100>, "blurb": "<one sentence>"}},
    "N": {{"score": <int 0-100>, "blurb": "<one sentence>"}}
  }},
  "political_values": "<one confident paragraph>",
  "life_history": "<one paragraph: career stage, relationship status, education tier>",
  "consumer_profile": "<one paragraph: spending style, brand affinity, what they will buy>"
}}
"""


def build_system_prompt(extra_forbidden: list[str] | None = None) -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(
        forbidden=_format_forbidden_list(extra_forbidden),
    )


def build_user_prompt(session_summary: dict[str, Any]) -> str:
    """The user message is the structured inputs the model conditions on.

    We hand the model the rule-based inferences, the self-report answers,
    and per-round event counts. The model's job is to fluently overreach
    from this thin slice — the user prompt does not coach it on what to
    say, only what data it has.
    """
    payload = {
        "inferences": session_summary.get("inferences", []),
        "self_report": session_summary.get("self_report", []),
        "round_event_counts": session_summary.get("round_event_counts", {}),
    }
    return (
        "Produce the broker product card JSON for the player described by "
        "the structured inputs below.\n\n"
        f"INPUTS:\n{json.dumps(payload, separators=(',', ':'))}"
    )
