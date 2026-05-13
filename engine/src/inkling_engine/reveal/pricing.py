"""Layer 5 scorer: profile-as-product price model.

Rule-based. The prices are illustrative against public CPM ranges for
data-broker segment packages (Acxiom, Experian, LiveRamp, etc.). They
are not audited — the construct doc notes this. The point is that a
plausible price tag makes the reveal viscerally real.

Base prices (USD per data point):
  - demographic correlate (inferred):   $0.005
  - behavioral construct (high tier):   $0.010
  - behavioral construct (medium tier): $0.005
  - overreach guess per Big Five trait: $0.020
  - consumer-profile paragraph:         $0.050

Total is summed, then multiplied by the 1.25x "aggregate profile"
package premium.
"""
from __future__ import annotations

from typing import Any

PRICE_HIGH = 0.010
PRICE_MEDIUM = 0.005
PRICE_DEMOGRAPHIC = 0.005
PRICE_OVERREACH_TRAIT = 0.020
PRICE_CONSUMER_PARAGRAPH = 0.050
PACKAGE_PREMIUM = 1.25


def _components_from_inferences(
    inferences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for inf in inferences:
        construct = inf["construct"]
        tier = inf.get("tier", "medium")
        if tier == "high":
            unit = PRICE_HIGH
            label = "Behavioral construct (high tier)"
        elif tier == "medium":
            unit = PRICE_MEDIUM
            label = "Behavioral construct (medium tier)"
        elif tier == "overreach":
            # Overreach inferences are itemized below (per trait + paragraphs)
            # rather than priced as a single behavioral construct.
            continue
        else:
            unit = PRICE_DEMOGRAPHIC
            label = "Demographic correlate"
        components.append({
            "label": label,
            "construct": construct,
            "price": round(unit, 4),
        })
    return components


def _components_from_overreach(
    overreach_value: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not overreach_value:
        return []
    out: list[dict[str, Any]] = []
    big_five = overreach_value.get("big_five", {})
    for trait in ("O", "C", "E", "A", "N"):
        if trait in big_five:
            out.append({
                "label": f"Big Five trait ({trait})",
                "construct": f"big_five.{trait}",
                "price": round(PRICE_OVERREACH_TRAIT, 4),
            })
    if overreach_value.get("consumer_profile"):
        out.append({
            "label": "Consumer profile paragraph",
            "construct": "consumer_profile",
            "price": round(PRICE_CONSUMER_PARAGRAPH, 4),
        })
    if overreach_value.get("political_values"):
        out.append({
            "label": "Political-values paragraph",
            "construct": "political_values",
            "price": round(PRICE_OVERREACH_TRAIT, 4),
        })
    if overreach_value.get("life_history"):
        out.append({
            "label": "Life-history paragraph",
            "construct": "life_history",
            "price": round(PRICE_OVERREACH_TRAIT, 4),
        })
    return out


def price_profile(
    inferences: list[dict[str, Any]],
    overreach_value: dict[str, Any] | None,
) -> dict[str, Any]:
    """Returns the structured `value` payload for a `broker_pricing` Inference.

    `inferences` is the full list of round-emitted Inference rows (tier
    high or medium). `overreach_value` is the `value` column of the
    `overreach` Inference row, or None if the overreach was unavailable
    (cost cap, disabled). When None, only the rule-based inferences
    contribute to the price.
    """
    components = _components_from_inferences(inferences) + _components_from_overreach(
        overreach_value
    )
    raw_total = sum(c["price"] for c in components)
    total = round(raw_total * PACKAGE_PREMIUM, 4)
    return {
        "components": components,
        "raw_subtotal": round(raw_total, 4),
        "package_premium": PACKAGE_PREMIUM,
        "total": total,
        "framing": (
            "Aggregate behavioral + psychographic profile. Illustrative "
            "against public CPM ranges; not an audited price quote."
        ),
    }
