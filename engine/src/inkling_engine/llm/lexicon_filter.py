"""Post-generation lexicon filter for the Overreach LLM output.

The model is asked to avoid the forbidden vocabulary in its system
prompt. This filter is the backstop: it scans the persisted text fields
of the structured response and reports any matches so the caller can
retry once and, on second failure, redact the offending blurb.

The term list is loaded from `content/reveal/forbidden_lexicon.json` —
the same file enumerated verbatim in the system prompt — so the model
sees the exact strings that will trip the filter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from inkling_engine.llm.prompts import load_forbidden_terms

REDACTED_PLACEHOLDER = (
    "The model produced disallowed phrasing for this trait — see logs."
)


@dataclass
class LexiconHit:
    """A single forbidden-term match inside a generated text field."""

    field_path: str  # dotted path like "big_five.N.blurb" or "political_values"
    term: str
    surrounding: str  # short snippet centered on the match


def _build_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Compile a case-insensitive word-boundary regex over all terms.

    Multi-word terms match across the space. Word boundaries on the
    outside prevent matching inside longer words; the regex is
    intentionally a strict superset of the Makefile lexicon grep so the
    post-filter is at least as conservative as the build-time rule.
    """
    escaped = [re.escape(t) for t in terms]
    escaped.sort(key=len, reverse=True)  # longest-first so multi-word wins
    return re.compile(r"(?i)\b(" + "|".join(escaped) + r")", re.IGNORECASE)


def _walk_text_fields(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Yield (dotted_path, text) for every string leaf in a nested dict/list."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, str):
        out.append((prefix or "<root>", obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_walk_text_fields(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_walk_text_fields(v, f"{prefix}[{i}]"))
    return out


def find_violations(parsed: dict[str, Any]) -> list[LexiconHit]:
    """Scan a parsed Overreach payload for any forbidden-term hits."""
    pattern = _build_pattern(load_forbidden_terms())
    hits: list[LexiconHit] = []
    for path, text in _walk_text_fields(parsed):
        for m in pattern.finditer(text):
            lo = max(0, m.start() - 24)
            hi = min(len(text), m.end() + 24)
            hits.append(
                LexiconHit(
                    field_path=path,
                    term=m.group(0),
                    surrounding=text[lo:hi],
                )
            )
    return hits


def redact_violations(parsed: dict[str, Any], hits: list[LexiconHit]) -> dict[str, Any]:
    """Return a deep-ish copy of `parsed` with every offending leaf field
    replaced by the fixed placeholder string.

    "Offending leaf" is identified by the dotted path; we do not try to
    surgically scrub the offending phrase out of the original sentence,
    since the surrounding marketing prose can still leak the implied
    label. The whole blurb goes.
    """
    if not hits:
        return parsed
    bad_paths = {h.field_path for h in hits}
    return _replace_paths(parsed, bad_paths, "")


def _replace_paths(obj: Any, bad_paths: set[str], cur: str) -> Any:
    if isinstance(obj, str):
        return REDACTED_PLACEHOLDER if (cur or "<root>") in bad_paths else obj
    if isinstance(obj, dict):
        return {
            k: _replace_paths(v, bad_paths, f"{cur}.{k}" if cur else str(k))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [
            _replace_paths(v, bad_paths, f"{cur}[{i}]") for i, v in enumerate(obj)
        ]
    return obj
