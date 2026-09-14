"""Fitness evaluation for a single fruit fly."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from .genotype import Fly
from .safety import safe_calorie_floor
from .twin import BehavioralTwin


@dataclass
class FitnessWeights:
    # Weight loss is a band, not a pure maximization target. The twin is honest
    # about the fact that too-aggressive deficits collapse adherence and raise
    # binge risk, so the swarm optimizes for a *sustainable* loss range.
    loss_reward: float = 20.0
    loss_target_min: float = 1.6
    loss_target_max: float = 6.0
    loss_penalty: float = 20.0
    adherence: float = 14.0
    plateau: float = 6.0
    binge: float = 11.0
    dropout: float = 8.0
    # Structural priors for personalization:
    # binge-prone users should keep a planned late-night snack, while
    # disciplined users should not be handed unnecessary flexibility.
    high_binge_snack_penalty: float = 18.0
    low_binge_flex_penalty: float = 12.0
    below_floor_penalty: float = 40.0


def _fly_seed(fly: Fly) -> int:
    """Return a process-stable seed for a fly's genotype.

    Python's builtin ``hash`` for strings is salted per process, which made
    supposedly deterministic evaluations change between runs. We hash the
    genotype representation instead so the same fly always gets the same
    future.
    """
    digest = hashlib.sha1(repr(fly.key()).encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**31)


def evaluate(
    twin: BehavioralTwin,
    fly: Fly,
    horizon: int = 12,
    weights: FitnessWeights | None = None,
) -> tuple[float, dict]:
    """Return (fitness_score, metrics) for one fly.

    Evaluation is deterministic per fly: the stochastic weight curve is seeded
    from the fly's own genotype, so the same fly always gets the same score.
    Monte Carlo averaging over many futures can be layered on later.
    """
    w = weights or FitnessWeights()
    rng = np.random.default_rng(_fly_seed(fly))
    curve = twin.simulate(fly, horizon, rng)

    loss = float(curve[0] - curve[-1])
    adherence = twin.adherence(fly)
    plateau = twin.plateau_risk(curve)
    binge = twin.binge_risk(fly)
    dropout = 1.0 - adherence

    if loss < w.loss_target_min:
        loss_term = -w.loss_penalty * (w.loss_target_min - loss)
    elif loss <= w.loss_target_max:
        loss_term = w.loss_reward * loss
    else:
        loss_term = (
            w.loss_reward * w.loss_target_max
            - w.loss_penalty * (loss - w.loss_target_max)
        )

    personalization = 0.0
    if twin.profile.binge_sensitivity > 0.55 and not fly.late_night_rule:
        personalization -= w.high_binge_snack_penalty
    if twin.profile.binge_sensitivity > 0.55 and fly.refeed_schedule == "none":
        personalization -= w.high_binge_snack_penalty * 0.6
    if twin.profile.binge_sensitivity < 0.25:
        if fly.late_night_rule:
            personalization -= w.low_binge_flex_penalty
        if fly.refeed_schedule != "none":
            personalization -= w.low_binge_flex_penalty * 0.5

    floor = safe_calorie_floor(
        twin.profile.start_weight_kg, twin.profile.maintenance_kcal
    )
    if fly.calorie_target < floor:
        personalization -= w.below_floor_penalty + 0.05 * (floor - fly.calorie_target)

    score = (
        loss_term
        + w.adherence * adherence
        - w.plateau * plateau
        - w.binge * binge
        - w.dropout * dropout
        + personalization
    )

    metrics = {
        "loss_kg": round(loss, 2),
        "loss_term": round(loss_term, 2),
        "adherence": round(adherence, 3),
        "plateau": round(plateau, 3),
        "binge": round(binge, 3),
        "dropout": round(dropout, 3),
        "personalization": round(personalization, 2),
        "curve": curve,
    }
    return score, metrics
