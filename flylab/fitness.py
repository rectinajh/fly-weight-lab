"""Fitness evaluation for a single fruit fly."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .genotype import Fly
from .twin import BehavioralTwin


@dataclass
class FitnessWeights:
    loss: float = 10.0
    adherence: float = 30.0
    plateau: float = 20.0
    binge: float = 15.0
    dropout: float = 20.0


def _fly_seed(fly: Fly) -> int:
    return abs(hash(fly.key())) % (2**31)


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

    score = (
        w.loss * loss
        + w.adherence * adherence
        - w.plateau * plateau
        - w.binge * binge
        - w.dropout * dropout
    )

    metrics = {
        "loss_kg": round(loss, 2),
        "adherence": round(adherence, 3),
        "plateau": round(plateau, 3),
        "binge": round(binge, 3),
        "dropout": round(dropout, 3),
        "curve": curve,
    }
    return score, metrics
