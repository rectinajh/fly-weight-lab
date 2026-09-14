"""Offline evaluation for the Fly Weight-Lab decision loop."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .connectome import load_params
from .evolution import Swarm
from .genotype import Fly
from .plateau import detect_plateau
from .twin import BehavioralTwin, UserProfile


@dataclass
class PlateauMetrics:
    precision: float
    recall: float
    f1: float
    accuracy: float

    def as_dict(self) -> dict:
        return {
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "f1": round(self.f1, 3),
            "accuracy": round(self.accuracy, 3),
        }


def synthetic_plateau_curve(
    weeks: int = 12,
    plateau_start: int | None = None,
    seed: int = 0,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    curve = [88.0]
    for week in range(1, weeks + 1):
        loss = 0.0 if plateau_start is not None and week >= plateau_start else rng.normal(0.45, 0.08)
        curve.append(curve[-1] - max(0.0, loss) + rng.normal(0.0, 0.15))
    return np.asarray(curve)


def evaluate_plateau_detection(samples: int = 80) -> PlateauMetrics:
    y_true = []
    y_pred = []
    for i in range(samples):
        is_plateau = i % 2 == 0
        curve = synthetic_plateau_curve(
            plateau_start=7 if is_plateau else None,
            seed=i,
        )
        detected, _ = detect_plateau(curve, threshold_kg=0.2)
        y_true.append(is_plateau)
        y_pred.append(bool(detected))

    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(y_true)
    return PlateauMetrics(precision, recall, f1, accuracy)


def compare_two_users() -> dict:
    params = load_params()
    users = [
        UserProfile(
            name="binge_prone",
            start_weight_kg=88.0,
            adherence_base=0.62,
            binge_sensitivity=0.65,
            metabolic_adaptation=0.35,
            maintenance_kcal=2300.0,
        ),
        UserProfile(
            name="disciplined",
            start_weight_kg=88.0,
            adherence_base=0.85,
            binge_sensitivity=0.10,
            metabolic_adaptation=0.20,
            maintenance_kcal=2300.0,
        ),
    ]
    out = {}
    for profile in users:
        twin = BehavioralTwin(profile, connectome=params)
        result = Swarm(twin, population_size=250, generations=25, seed=7).run()
        fly = result.best_fly
        out[profile.name] = {
            "calorie_target": fly.calorie_target,
            "late_night_rule": fly.late_night_rule,
            "refeed_schedule": fly.refeed_schedule,
            "sleep_target": fly.sleep_target,
            "meal_window": fly.meal_window,
            "fitness": round(result.best_score, 2),
        }
    return out


def champion_vs_aggressive_baseline() -> dict:
    params = load_params()
    profile = UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        maintenance_kcal=2300.0,
    )
    twin = BehavioralTwin(profile, connectome=params)
    aggressive = Fly(
        calorie_target=1500,
        protein_pct=0.40,
        carb_pct=0.25,
        meal_window=8,
        meal_count=3,
        late_night_rule=False,
        workout_freq=5,
        workout_type="cardio",
        sleep_target=7.0,
        refeed_schedule="none",
        step_target=10000,
    )
    champion = Swarm(twin, population_size=250, generations=25, seed=7).run().best_fly
    return {
        "aggressive": {
            "adherence": round(twin.adherence(aggressive), 3),
            "binge_risk": round(twin.binge_risk(aggressive), 3),
            "loss_kg": round(float(twin.simulate(aggressive, 12)[0] - twin.simulate(aggressive, 12)[-1]), 2),
        },
        "champion": {
            "adherence": round(twin.adherence(champion), 3),
            "binge_risk": round(twin.binge_risk(champion), 3),
            "loss_kg": round(float(twin.simulate(champion, 12)[0] - twin.simulate(champion, 12)[-1]), 2),
        },
    }
