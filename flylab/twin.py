"""Behavioral digital twin.

This is a transparent, parametric stand-in for the real data-fit twin. In
production it is learned from a user's actual logs (weight, food, sleep, mood,
adherence). The MVP version keeps the genetic loop runnable while remaining
honest about what it models: behavioral response, not metabolism.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .genotype import Fly

KCAL_PER_KG = 7700.0


@dataclass
class UserProfile:
    name: str = "user"
    start_weight_kg: float = 90.0
    adherence_base: float = 0.70
    binge_sensitivity: float = 0.35
    metabolic_adaptation: float = 0.25
    water_noise_kg: float = 0.4
    maintenance_kcal: float = 2300.0


class BehavioralTwin:
    def __init__(self, profile: UserProfile):
        self.profile = profile

    def adherence(self, fly: Fly) -> float:
        p = self.profile
        deficit_ratio = max(0.0, (p.maintenance_kcal - fly.calorie_target) / p.maintenance_kcal)
        difficulty = (
            0.25 * deficit_ratio
            + 0.10 * max(0.0, (12 - fly.meal_window) / 12)
            + 0.06 * (fly.workout_freq / 6)
            + 0.04 * max(0.0, (8 - fly.sleep_target) / 8)
        )
        fit_bonus = 0.0
        if p.binge_sensitivity > 0.4 and fly.late_night_rule:
            fit_bonus += 0.08
        if p.binge_sensitivity > 0.4 and fly.refeed_schedule != "none":
            fit_bonus += 0.05
        return float(np.clip(p.adherence_base - difficulty + fit_bonus, 0.1, 0.95))

    def binge_risk(self, fly: Fly) -> float:
        p = self.profile
        deficit_ratio = max(0.0, (p.maintenance_kcal - fly.calorie_target) / p.maintenance_kcal)
        risk = (
            p.binge_sensitivity
            + 0.30 * deficit_ratio
            + 0.10 * max(0.0, (12 - fly.meal_window) / 12)
        )
        if fly.late_night_rule:
            risk -= 0.12
        if fly.refeed_schedule == "weekly":
            risk -= 0.10
        elif fly.refeed_schedule == "biweekly":
            risk -= 0.05
        return float(np.clip(risk, 0.0, 1.0))

    def simulate(
        self,
        fly: Fly,
        horizon_weeks: int = 12,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        rng = rng or np.random.default_rng(0)
        p = self.profile
        adherence = self.adherence(fly)
        binge_risk = self.binge_risk(fly)

        # Real cost of the "anti-perfectionism" features: a late-night snack
        # and a refeed day both add calories, so they only survive when the
        # binge reduction they buy is worth more than the deficit they cost.
        late_night_cost = 150.0 if fly.late_night_rule else 0.0
        if fly.refeed_schedule == "weekly":
            refeed_cost = 800.0 / 7.0
        elif fly.refeed_schedule == "biweekly":
            refeed_cost = 800.0 / 14.0
        else:
            refeed_cost = 0.0
        effective_intake = fly.calorie_target + late_night_cost + refeed_cost

        curve = np.empty(horizon_weeks + 1)
        curve[0] = p.start_weight_kg
        weight = p.start_weight_kg

        for week in range(1, horizon_weeks + 1):
            raw_deficit_kg = (p.maintenance_kcal - effective_intake) * 7.0 / KCAL_PER_KG
            adaptation = 1.0 - p.metabolic_adaptation * (1.0 - math.exp(-week / 5.0))
            effective = raw_deficit_kg * adherence * adaptation
            if rng.random() < binge_risk:
                weight += 0.4 + 0.3 * rng.random()
                effective *= 0.5
            weight -= effective
            weight += rng.normal(0.0, p.water_noise_kg)
            curve[week] = weight

        return curve

    def plateau_risk(self, curve: np.ndarray, window: int = 3) -> float:
        if len(curve) <= window:
            return 0.0
        weekly = np.diff(curve[-(window + 1):])
        stalled = int(np.sum(np.abs(weekly) < 0.1))
        return stalled / window
