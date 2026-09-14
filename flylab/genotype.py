"""A fruit fly is a candidate weight-loss protocol (its genotype).

Each gene encodes one adjustable dimension of a protocol. Flies can be created
randomly, mutated, and crossed over like chromosomes in a genetic algorithm.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

CALORIE_FLOOR = 1200
REFEEED_OPTIONS = ("none", "weekly", "biweekly")
WORKOUT_TYPES = ("cardio", "resistance", "mix")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class Fly:
    calorie_target: int
    protein_pct: float
    carb_pct: float
    meal_window: int
    meal_count: int
    late_night_rule: bool
    workout_freq: int
    workout_type: str
    sleep_target: float
    refeed_schedule: str
    step_target: int

    @property
    def fat_pct(self) -> float:
        return round(max(0.0, 1.0 - self.protein_pct - self.carb_pct), 3)

    def key(self) -> tuple:
        return (
            self.calorie_target,
            round(self.protein_pct, 3),
            round(self.carb_pct, 3),
            self.meal_window,
            self.meal_count,
            self.late_night_rule,
            self.workout_freq,
            self.workout_type,
            round(self.sleep_target, 2),
            self.refeed_schedule,
            self.step_target,
        )

    @classmethod
    def random(cls, rng: random.Random | None = None) -> "Fly":
        rng = rng or random.Random()
        protein = rng.uniform(0.25, 0.45)
        carb = rng.uniform(0.20, 0.50)
        return cls(
            calorie_target=rng.randint(1400, 2200),
            protein_pct=round(protein, 3),
            carb_pct=round(carb, 3),
            meal_window=rng.randint(8, 16),
            meal_count=rng.randint(2, 5),
            late_night_rule=rng.random() < 0.5,
            workout_freq=rng.randint(0, 6),
            workout_type=rng.choice(WORKOUT_TYPES),
            sleep_target=round(rng.uniform(7.0, 9.0), 1),
            refeed_schedule=rng.choice(REFEEED_OPTIONS),
            step_target=rng.randint(4000, 12000),
        )._normalize()

    def mutate(self, rng: random.Random | None = None, rate: float = 0.2) -> "Fly":
        rng = rng or random.Random()

        def jitter(value: float, low: float, high: float, step: float) -> float:
            if rng.random() >= rate:
                return value
            return _clamp(value + rng.uniform(-step, step), low, high)

        return Fly(
            calorie_target=int(round(jitter(self.calorie_target, CALORIE_FLOOR, 2400, 100))),
            protein_pct=round(jitter(self.protein_pct, 0.20, 0.45, 0.03), 3),
            carb_pct=round(jitter(self.carb_pct, 0.15, 0.50, 0.03), 3),
            meal_window=int(round(jitter(self.meal_window, 8, 16, 1))),
            meal_count=int(round(jitter(self.meal_count, 2, 5, 1))),
            late_night_rule=(not self.late_night_rule) if rng.random() < rate else self.late_night_rule,
            workout_freq=int(round(jitter(self.workout_freq, 0, 6, 1))),
            workout_type=rng.choice(WORKOUT_TYPES) if rng.random() < rate else self.workout_type,
            sleep_target=round(jitter(self.sleep_target, 6.5, 9.5, 0.3), 1),
            refeed_schedule=rng.choice(REFEEED_OPTIONS) if rng.random() < rate else self.refeed_schedule,
            step_target=int(round(jitter(self.step_target, 3000, 15000, 500))),
        )._normalize()

    def crossover(self, other: "Fly", rng: random.Random | None = None) -> "Fly":
        rng = rng or random.Random()

        def pick(left, right):
            return left if rng.random() < 0.5 else right

        return Fly(
            calorie_target=pick(self.calorie_target, other.calorie_target),
            protein_pct=pick(self.protein_pct, other.protein_pct),
            carb_pct=pick(self.carb_pct, other.carb_pct),
            meal_window=pick(self.meal_window, other.meal_window),
            meal_count=pick(self.meal_count, other.meal_count),
            late_night_rule=pick(self.late_night_rule, other.late_night_rule),
            workout_freq=pick(self.workout_freq, other.workout_freq),
            workout_type=pick(self.workout_type, other.workout_type),
            sleep_target=pick(self.sleep_target, other.sleep_target),
            refeed_schedule=pick(self.refeed_schedule, other.refeed_schedule),
            step_target=pick(self.step_target, other.step_target),
        )._normalize()

    def _normalize(self) -> "Fly":
        self.calorie_target = int(_clamp(self.calorie_target, CALORIE_FLOOR, 2400))
        self.protein_pct = round(_clamp(self.protein_pct, 0.20, 0.45), 3)
        self.carb_pct = round(_clamp(self.carb_pct, 0.15, 0.50), 3)
        if self.protein_pct + self.carb_pct > 0.85:
            self.carb_pct = round(0.85 - self.protein_pct, 3)
        self.carb_pct = max(0.15, self.carb_pct)
        self.meal_window = int(_clamp(self.meal_window, 8, 16))
        self.meal_count = int(_clamp(self.meal_count, 2, 5))
        self.workout_freq = int(_clamp(self.workout_freq, 0, 6))
        self.sleep_target = round(_clamp(self.sleep_target, 6.5, 9.5), 1)
        self.step_target = int(_clamp(self.step_target, 3000, 15000))
        if self.workout_type not in WORKOUT_TYPES:
            self.workout_type = "mix"
        if self.refeed_schedule not in REFEEED_OPTIONS:
            self.refeed_schedule = "none"
        return self

    def describe(self) -> str:
        return (
            f"calories={self.calorie_target} kcal, "
            f"protein={self.protein_pct:.0%}, carbs={self.carb_pct:.0%}, fat={self.fat_pct:.0%}, "
            f"window={self.meal_window}h, meals={self.meal_count}, "
            f"late_night={'yes' if self.late_night_rule else 'no'}, "
            f"workout={self.workout_freq}x/{self.workout_type}, "
            f"sleep={self.sleep_target}h, refeed={self.refeed_schedule}, steps={self.step_target}"
        )
