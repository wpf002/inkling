"""Layer 1 scorer: gap between self-report Likert answers and the
gameplay-derived equivalents.

Maps each of the 10 self-report items to a single numeric path inside
one of the round inferences, normalizes both to [0, 1], computes
divergence per pair, and surfaces the top three largest divergences as
the "punch" for Layer 1.

Item sr10 (novelty) has no direct gameplay equivalent and is skipped.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# (item_id, construct, value_path, normalize_to_unit, inverted)
#
# value_path is dotted notation into the inference.value object.
# normalize_to_unit is a function name from NORMALIZERS that maps the
# raw value onto [0, 1]. `inverted` flips the gameplay score so high
# self-report corresponds to high gameplay across the pair.
PAIRS: list[dict[str, Any]] = [
    {
        "item_id": "sr01",
        "construct_self": "risk_tolerance",
        "inference_construct": "risk_tolerance",
        "value_path": "overall_take_rate",
        "normalize": "passthrough",
        "inverted": False,
    },
    {
        "item_id": "sr02",
        "construct_self": "loss_aversion",
        "inference_construct": "loss_aversion",
        "value_path": "lambda",
        "normalize": "lambda_to_unit",
        "inverted": False,
    },
    {
        "item_id": "sr03",
        "construct_self": "trust",
        "inference_construct": "initial_trust_propensity",
        "value_path": "initial_trust_amount",
        "normalize": "amount_over_10",
        "inverted": False,
    },
    {
        "item_id": "sr04",
        "construct_self": "fairness",
        "inference_construct": "retaliation_tendency",
        "value_path": "retaliation_delta",
        "normalize": "negative_delta_to_unit",
        "inverted": False,
    },
    {
        "item_id": "sr05",
        "construct_self": "attribution",
        "inference_construct": "attribution_style",
        "value_path": "hostile_score",
        "normalize": "passthrough",
        "inverted": False,
    },
    {
        "item_id": "sr06",
        "construct_self": "deliberation",
        "inference_construct": "deliberation",
        "value_path": "deliberation_index",
        "normalize": "deliberation_index_to_unit",
        "inverted": False,
    },
    {
        "item_id": "sr07",
        "construct_self": "moral_utilitarian",
        "inference_construct": "utilitarian_leaning",
        "value_path": "utilitarian_rate",
        "normalize": "passthrough",
        "inverted": False,
    },
    {
        "item_id": "sr08",
        "construct_self": "stress_response",
        "inference_construct": "stress_response",
        "value_path": "take_rate_delta",
        "normalize": "signed_delta_to_unit",
        "inverted": False,
    },
    {
        "item_id": "sr09",
        "construct_self": "attention",
        "inference_construct": "sustained_attention",
        "value_path": "rt_slope_ms_per_trial",
        "normalize": "rt_slope_to_unit",
        "inverted": True,
    },
]


def _passthrough(x: float) -> float:
    return _clip01(x)


def _lambda_to_unit(x: float) -> float:
    # λ ~ 1 means losses == gains; populations cluster near 2; we map
    # λ ∈ [0.5, 4.0] onto [0, 1].
    return _clip01((x - 0.5) / 3.5)


def _amount_over_10(x: float) -> float:
    return _clip01(x / 10.0)


def _negative_delta_to_unit(x: float) -> float:
    # retaliation_delta is negative when retaliating (sent less after a
    # bad return). High punishment willingness → larger negative delta →
    # higher unit score. We map delta ∈ [-3, 0] onto [1, 0].
    return _clip01(min(0.0, x) / -3.0)


def _deliberation_index_to_unit(x: float) -> float:
    # Index is (second_half - first_half) / first_half, typically in
    # [-0.5, 0.5]. Slowdown (positive) → more deliberative → higher unit.
    return _clip01(x + 0.5)


def _signed_delta_to_unit(x: float) -> float:
    # Take-rate delta ∈ [-1, 1]. Positive means took more under pressure
    # (handles deadlines well). Map onto [0, 1].
    return _clip01((x + 1.0) / 2.0)


def _rt_slope_to_unit(x: float) -> float:
    # Slope in ms/trial. Steeper positive = more slowdown. Cap at
    # ±20 ms/trial. We don't invert here — inversion is applied in the
    # main pair loop using the `inverted` flag.
    return _clip01((x + 20.0) / 40.0)


NORMALIZERS = {
    "passthrough": _passthrough,
    "lambda_to_unit": _lambda_to_unit,
    "amount_over_10": _amount_over_10,
    "negative_delta_to_unit": _negative_delta_to_unit,
    "deliberation_index_to_unit": _deliberation_index_to_unit,
    "signed_delta_to_unit": _signed_delta_to_unit,
    "rt_slope_to_unit": _rt_slope_to_unit,
}


def _clip01(x: float) -> float:
    if math.isnan(x):
        return 0.5
    return max(0.0, min(1.0, x))


def _dig(value: dict[str, Any], path: str) -> float | None:
    cur: Any = value
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    if isinstance(cur, int | float):
        return float(cur)
    return None


@dataclass
class StatedVsRevealedPair:
    item_id: str
    construct: str
    self_norm: float
    game_norm: float
    divergence: float
    self_response: int  # raw Likert 1..5
    game_value: float | None  # raw gameplay value (pre-normalization)


def _self_norm(response: int) -> float:
    return _clip01((response - 1) / 4.0)


def compute_pairs(
    inferences: list[dict[str, Any]],
    self_report: list[dict[str, Any]],
) -> list[StatedVsRevealedPair]:
    """Build the 9-pair comparison set.

    Both inputs are loose dicts matching the Inference and self-report
    persistence shapes. Pairs whose gameplay inference is missing for
    the session are skipped silently — the caller decides whether to
    surface that absence.
    """
    by_construct: dict[str, dict[str, Any]] = {
        inf["construct"]: inf.get("value", {}) for inf in inferences
    }
    by_item: dict[str, int] = {r["item_id"]: int(r["response"]) for r in self_report}

    pairs: list[StatedVsRevealedPair] = []
    for spec in PAIRS:
        item_id = spec["item_id"]
        response = by_item.get(item_id)
        if response is None:
            continue
        inf_value = by_construct.get(spec["inference_construct"])
        if inf_value is None:
            continue
        raw = _dig(inf_value, spec["value_path"])
        if raw is None:
            continue

        normalize = NORMALIZERS[spec["normalize"]]
        game = normalize(raw)
        if spec["inverted"]:
            game = 1.0 - game
        self_n = _self_norm(response)
        pairs.append(
            StatedVsRevealedPair(
                item_id=item_id,
                construct=spec["construct_self"],
                self_norm=self_n,
                game_norm=game,
                divergence=abs(self_n - game),
                self_response=response,
                game_value=raw,
            )
        )
    return pairs


def top_divergences(
    pairs: list[StatedVsRevealedPair], n: int = 3
) -> list[StatedVsRevealedPair]:
    return sorted(pairs, key=lambda p: p.divergence, reverse=True)[:n]


def build_inference_value(
    pairs: list[StatedVsRevealedPair],
) -> dict[str, Any]:
    """Shape for the `stated_vs_revealed` Inference row's value column."""
    return {
        "pairs": [
            {
                "item_id": p.item_id,
                "construct": p.construct,
                "self_norm": round(p.self_norm, 4),
                "game_norm": round(p.game_norm, 4),
                "divergence": round(p.divergence, 4),
                "self_response": p.self_response,
                "game_value": p.game_value,
            }
            for p in pairs
        ],
        "top": [
            {
                "item_id": p.item_id,
                "construct": p.construct,
                "divergence": round(p.divergence, 4),
            }
            for p in top_divergences(pairs, n=3)
        ],
    }
