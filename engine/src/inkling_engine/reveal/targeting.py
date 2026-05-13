"""Layer 6 scorer: pick personalized ads, scams, and a recruiter pitch.

Rule-based. No LLM call. No PII inserted into slots — only construct
labels and short adjectives from a fixed lexicon.

Each template carries a list of `targeting_keys` (constructs that the
template is "good at" reaching). We score each template by the count of
overlapping constructs in the player's strongest inferences, break ties
by category diversity, and pick 3 ads + 3 scams + 1 recruiter pitch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Adjectives we may interpolate into a {{trait}} slot. These are the
# *only* descriptive words that may fill template slots — keeps the
# output lexicon-clean by construction. The mapping is per-construct.
SLOT_VOCAB: dict[str, dict[str, str]] = {
    "loss_aversion": {"low": "willing to risk", "mid": "balanced about losses", "high": "loss-averse"},
    "risk_tolerance": {"low": "cautious", "mid": "balanced", "high": "willing to bet"},
    "stress_response": {"low": "steady under pressure", "mid": "even-keeled", "high": "fast under pressure"},
    "reaction_time_profile": {"low": "quick", "mid": "steady", "high": "deliberate"},
    "sustained_attention": {"low": "fading focus", "mid": "steady focus", "high": "sustained focus"},
    "frustration_tolerance": {"low": "patient", "mid": "balanced", "high": "composed"},
    "response_inhibition": {"low": "decisive", "mid": "balanced", "high": "careful"},
    "initial_trust_propensity": {"low": "cautious upfront", "mid": "neutral upfront", "high": "trusting upfront"},
    "adaptation_rate": {"low": "consistent", "mid": "responsive", "high": "highly responsive"},
    "retaliation_tendency": {"low": "forgiving", "mid": "balanced", "high": "score-keeping"},
    "working_memory_span": {"low": "compact recall", "mid": "average recall", "high": "wide recall"},
    "processing_speed": {"low": "deliberate", "mid": "steady", "high": "rapid"},
    "performance_under_load": {"low": "load-sensitive", "mid": "average", "high": "load-resilient"},
    "attribution_style": {"low": "charitable", "mid": "mixed", "high": "skeptical"},
    "deliberation": {"low": "decisive", "mid": "balanced", "high": "thorough"},
    "utilitarian_leaning": {"low": "rules-first", "mid": "mixed", "high": "outcome-first"},
    "personal_impersonal_sensitivity": {"low": "hands-on", "mid": "balanced", "high": "hands-off"},
}


@dataclass
class TopInference:
    construct: str
    confidence: float
    value: dict[str, Any]


def _strongest_by_construct(inferences: list[dict[str, Any]]) -> list[TopInference]:
    by_construct: dict[str, TopInference] = {}
    for inf in inferences:
        c = inf["construct"]
        conf = float(inf.get("confidence", 0.0))
        cur = by_construct.get(c)
        if cur is None or conf > cur.confidence:
            by_construct[c] = TopInference(
                construct=c, confidence=conf, value=inf.get("value") or {}
            )
    return sorted(by_construct.values(), key=lambda t: t.confidence, reverse=True)


def _score_template(template: dict[str, Any], top_constructs: set[str]) -> int:
    keys = set(template.get("targeting_keys") or template.get("vulnerability_keys") or template.get("hook_keys") or [])
    return len(keys & top_constructs)


def _pick_diverse(
    templates: list[dict[str, Any]],
    top_constructs: set[str],
    n: int,
    category_field: str,
) -> list[dict[str, Any]]:
    """Pick top-n by overlap score, breaking ties to avoid repeating
    the same category."""
    scored = sorted(
        templates,
        key=lambda t: (_score_template(t, top_constructs), t.get("id", "")),
        reverse=True,
    )
    picked: list[dict[str, Any]] = []
    used_categories: set[str] = set()
    for t in scored:
        cat = t.get(category_field, "")
        if cat in used_categories:
            continue
        picked.append(t)
        used_categories.add(cat)
        if len(picked) >= n:
            return picked
    # Not enough diverse categories — fall back to filling with leftovers.
    for t in scored:
        if t in picked:
            continue
        picked.append(t)
        if len(picked) >= n:
            return picked
    return picked


def _trait_bucket(construct: str, value: dict[str, Any]) -> str:
    """Bucket a construct's value into low/mid/high for the SLOT_VOCAB."""
    # Use the construct's "headline" numeric field; fall back to "mid"
    # when nothing maps cleanly.
    headline: float | None = None
    if construct == "loss_aversion":
        headline = float(value.get("lambda", 2.0))
        if headline < 1.5:
            return "low"
        if headline > 2.5:
            return "high"
        return "mid"
    if construct == "risk_tolerance":
        headline = float(value.get("overall_take_rate", 0.5))
    elif construct == "stress_response":
        headline = float(value.get("take_rate_delta", 0.0)) + 0.5
    elif construct == "reaction_time_profile":
        median = float(value.get("median_rt_ms", 600))
        # Faster = lower bucket. 400 ms fast, 800 ms slow.
        headline = max(0.0, min(1.0, (median - 400) / 400))
    elif construct == "sustained_attention":
        slope = float(value.get("rt_slope_ms_per_trial", 0.0))
        # Steeper positive slope = more fading. Map to high here means
        # "sustained" so invert.
        headline = max(0.0, min(1.0, 1.0 - (slope + 5) / 10.0))
    elif construct == "frustration_tolerance":
        delta = float(value.get("post_spike_rt_delta_ms", 0.0))
        headline = max(0.0, min(1.0, 1.0 - abs(delta) / 200.0))
    elif construct == "response_inhibition":
        headline = 1.0 - float(value.get("false_alarm_rate", 0.0))
    elif construct == "initial_trust_propensity":
        headline = float(value.get("initial_trust_amount", 5.0)) / 10.0
    elif construct == "adaptation_rate":
        headline = (float(value.get("adaptation_correlation", 0.0)) + 1.0) / 2.0
    elif construct == "retaliation_tendency":
        delta = float(value.get("retaliation_delta", 0.0))
        headline = max(0.0, min(1.0, -delta / 3.0))
    elif construct == "working_memory_span":
        headline = max(0.0, min(1.0, (float(value.get("span", 5)) - 3) / 5.0))
    elif construct == "processing_speed":
        ms = float(value.get("mean_tap_rt_ms", 700))
        headline = max(0.0, min(1.0, 1.0 - (ms - 400) / 600))
    elif construct == "performance_under_load":
        drop = float(value.get("drop", 0.0))
        headline = max(0.0, min(1.0, 1.0 - drop))
    elif construct == "attribution_style":
        headline = float(value.get("hostile_score", 0.5))
    elif construct == "deliberation":
        idx = float(value.get("deliberation_index", 0.0))
        headline = max(0.0, min(1.0, idx + 0.5))
    elif construct == "utilitarian_leaning":
        headline = float(value.get("utilitarian_rate", 0.5))
    elif construct == "personal_impersonal_sensitivity":
        delta = float(value.get("sensitivity_delta", 0.0))
        headline = max(0.0, min(1.0, (delta + 0.5)))

    if headline is None:
        return "mid"
    if headline < 0.33:
        return "low"
    if headline > 0.66:
        return "high"
    return "mid"


_SLOT_RE = re.compile(r"\{\{(.+?)\}\}")


def _fill_slots(text: str, by_construct: dict[str, TopInference]) -> str:
    def repl(m: re.Match[str]) -> str:
        slot = m.group(1).strip()
        if slot in SLOT_VOCAB and slot in by_construct:
            bucket = _trait_bucket(slot, by_construct[slot].value)
            return SLOT_VOCAB[slot][bucket]
        # Unknown slot — leave neutral.
        return "balanced"
    return _SLOT_RE.sub(repl, text)


def _fill_template(
    template: dict[str, Any],
    by_construct: dict[str, TopInference],
    text_fields: list[str],
) -> dict[str, Any]:
    filled = dict(template)
    for field in text_fields:
        if field in template and isinstance(template[field], str):
            filled[field] = _fill_slots(template[field], by_construct)
    return filled


def select(
    inferences: list[dict[str, Any]],
    ad_templates: list[dict[str, Any]],
    scam_templates: list[dict[str, Any]],
    recruiter_templates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Pick + fill the 3 ads, 3 scams, 1 recruiter pitch. Returns a dict
    ready to render in Layer 6."""
    strongest = _strongest_by_construct(inferences)
    top_constructs = {t.construct for t in strongest[:8]}
    by_construct = {t.construct: t for t in strongest}

    ads = _pick_diverse(ad_templates, top_constructs, 3, category_field="category")
    scams = _pick_diverse(scam_templates, top_constructs, 3, category_field="type")
    recruiter = _pick_diverse(
        recruiter_templates, top_constructs, 1, category_field="role"
    )

    return {
        "ads": [
            _fill_template(a, by_construct, ["headline_template", "body_template"])
            for a in ads
        ],
        "scams": [
            _fill_template(s, by_construct, ["scenario_template"]) for s in scams
        ],
        "recruiter": [
            _fill_template(r, by_construct, ["pitch_template"]) for r in recruiter
        ],
        "top_constructs": sorted(top_constructs),
    }
