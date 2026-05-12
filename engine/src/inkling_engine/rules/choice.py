"""Round 1 (Choice) scorer.

Three inferences emitted from the gamble trial stream:
  - loss aversion (lambda, tier=high) via prospect-theory MLE
  - risk tolerance (take rate, tier=high) split by hurried/unhurried
  - stress response (delta of take-rate and reaction-time, tier=medium)
"""
from collections.abc import Iterable
from typing import Any

import numpy as np
from scipy.optimize import minimize

from inkling_engine.models import Inference, RoundEventDTO
from inkling_engine.rules.shared import safe_log, sigmoid, trials_from_events
from inkling_engine.scoring.runner import register_scorer

ALPHA: float = 0.88
LAMBDA_BOUNDS = (0.05, 20.0)
BETA_BOUNDS = (1e-3, 5.0)
LAMBDA_INIT = 2.0
BETA_INIT = 0.2


def _eu(win: float, lose: float, lam: float) -> float:
    return 0.5 * (win**ALPHA) - 0.5 * lam * (lose**ALPHA)


def _neg_log_likelihood(params: np.ndarray, valid: list[dict[str, Any]]) -> float:
    lam, beta = params
    total = 0.0
    for t in valid:
        eu = _eu(float(t["win"]), float(t["lose"]), lam)
        p_take = sigmoid(beta * eu)
        y = 1 if t["choice"] == "take" else 0
        total -= y * safe_log(p_take) + (1 - y) * safe_log(1.0 - p_take)
    return total


def _null_log_likelihood(valid: list[dict[str, Any]]) -> float:
    n = len(valid)
    if n == 0:
        return 0.0
    takes = sum(1 for t in valid if t["choice"] == "take")
    p = takes / n
    if p in (0.0, 1.0):
        return 0.0
    return -(takes * safe_log(p) + (n - takes) * safe_log(1.0 - p))


def _fit_loss_aversion(
    valid: list[dict[str, Any]],
) -> tuple[float, float, float, float, list[dict[str, Any]]]:
    if not valid:
        return LAMBDA_INIT, BETA_INIT, 0.0, 0.0, []
    res = minimize(
        _neg_log_likelihood,
        x0=np.array([LAMBDA_INIT, BETA_INIT]),
        args=(valid,),
        method="L-BFGS-B",
        bounds=[LAMBDA_BOUNDS, BETA_BOUNDS],
    )
    lam, beta = float(res.x[0]), float(res.x[1])
    nll = float(res.fun)
    log_likelihood = -nll
    per_trial = []
    for t in valid:
        eu = _eu(float(t["win"]), float(t["lose"]), lam)
        per_trial.append(
            {
                "trial": t["trial"],
                "win": t["win"],
                "lose": t["lose"],
                "choice": t["choice"],
                "p_take": sigmoid(beta * eu),
            }
        )
    return lam, beta, nll, log_likelihood, per_trial


def _loss_aversion_inference(trials: list[dict[str, Any]]) -> Inference:
    valid = [t for t in trials if t["choice"] in ("take", "decline")]
    n_valid = len(valid)
    underpowered = n_valid < 6
    distinct_choices = {t["choice"] for t in valid}
    unidentified = n_valid > 0 and len(distinct_choices) == 1

    lam, beta, nll, log_likelihood, per_trial = _fit_loss_aversion(valid)
    null_nll = _null_log_likelihood(valid)

    if null_nll <= 0.0:
        confidence = 0.0
    else:
        residual = nll
        confidence = max(0.0, min(1.0, 1.0 - (residual / null_nll)))

    if underpowered:
        confidence = min(confidence, 0.1)

    evidence: dict[str, Any] = {
        "trials_used": n_valid,
        "log_likelihood": log_likelihood,
        "per_trial": per_trial,
    }
    if unidentified:
        evidence["unidentified"] = True
    if underpowered:
        evidence["underpowered"] = True

    return Inference(
        construct="loss_aversion",
        tier="high",
        value={"lambda": lam, "beta": beta, "alpha": ALPHA},
        confidence=confidence,
        evidence=evidence,
    )


def _risk_tolerance_inference(trials: list[dict[str, Any]]) -> Inference:
    valid = [t for t in trials if t["choice"] in ("take", "decline")]
    by_cond: dict[str, list[dict[str, Any]]] = {}
    for t in valid:
        by_cond.setdefault(t["condition"], []).append(t)

    def take_rate(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return sum(1 for r in rows if r["choice"] == "take") / len(rows)

    overall = take_rate(valid)
    unhurried = take_rate(by_cond.get("unhurried", []))
    hurried = take_rate(by_cond.get("hurried", []))
    confidence = min(len(valid) / 8.0, 1.0)

    return Inference(
        construct="risk_tolerance",
        tier="high",
        value={
            "overall_take_rate": overall,
            "unhurried": unhurried,
            "hurried": hurried,
        },
        confidence=confidence,
        evidence={
            "trials_per_condition": {
                "unhurried": len(by_cond.get("unhurried", [])),
                "hurried": len(by_cond.get("hurried", [])),
            }
        },
    )


def _stress_response_inference(trials: list[dict[str, Any]]) -> Inference:
    valid = [t for t in trials if t["choice"] in ("take", "decline")]
    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for t in valid:
        gid = t["gamble_id"]
        if gid is None:
            continue
        by_pair.setdefault(gid, {})[t["condition"]] = t

    pair_deltas: list[dict[str, Any]] = []
    take_diffs: list[float] = []
    rt_diffs: list[float] = []

    for gid, pair in by_pair.items():
        u = pair.get("unhurried")
        h = pair.get("hurried")
        if u is None or h is None:
            continue
        u_take = 1 if u["choice"] == "take" else 0
        h_take = 1 if h["choice"] == "take" else 0
        td = h_take - u_take
        take_diffs.append(float(td))
        if u.get("rt_ms") is not None and h.get("rt_ms") is not None:
            rd = float(h["rt_ms"]) - float(u["rt_ms"])
            rt_diffs.append(rd)
        else:
            rd = None
        pair_deltas.append(
            {
                "gamble_id": gid,
                "take_delta": td,
                "rt_delta_ms": rd,
            }
        )

    take_rate_delta = float(np.mean(take_diffs)) if take_diffs else 0.0
    reaction_time_delta_ms = float(np.mean(rt_diffs)) if rt_diffs else 0.0

    if not take_diffs:
        directional = 0.0
    else:
        signs = [1 if d > 0 else (-1 if d < 0 else 0) for d in take_diffs]
        directional = abs(sum(signs)) / len(signs)
    confidence = directional * 0.8 + 0.2

    return Inference(
        construct="stress_response",
        tier="medium",
        value={
            "take_rate_delta": take_rate_delta,
            "reaction_time_delta_ms": reaction_time_delta_ms,
        },
        confidence=confidence,
        evidence={"per_gamble_deltas": pair_deltas},
    )


def score_choice(events: Iterable[RoundEventDTO]) -> list[Inference]:
    by_trial = trials_from_events(events)
    trials = list(by_trial.values())
    return [
        _loss_aversion_inference(trials),
        _risk_tolerance_inference(trials),
        _stress_response_inference(trials),
    ]


register_scorer("choice", score_choice)
