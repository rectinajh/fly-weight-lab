"""Safety guardrails for Fly Weight-Lab.

The product never diagnoses or prescribes. These guards keep generated
protocols above safe floors and force escalation when the input profile looks
medically out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .genotype import Fly
from .twin import UserProfile


@dataclass
class SafetyReport:
    safe: bool = True
    blocked: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    escalation: bool = False

    def as_dict(self) -> dict:
        return {
            "safe": self.safe,
            "blocked": self.blocked,
            "warnings": self.warnings,
            "escalation": self.escalation,
        }


def safe_calorie_floor(
    weight_kg: float,
    maintenance_kcal: float | None = None,
) -> int:
    """Return a conservative floor without pretending to be medical advice.

    ``14 kcal/kg`` was too low: a 61.5 kg user could still be handed 1329 kcal.
    The floor is the max of 1200, 22 kcal/kg, and 80% of estimated maintenance.
    """
    per_kg = int(round(float(weight_kg) * 22.0))
    maintenance = float(maintenance_kcal) if maintenance_kcal else float(weight_kg) * 30.0
    from_maintenance = int(round(maintenance * 0.80))
    return max(1200, per_kg, from_maintenance)


def has_medical_red_flags(profile: UserProfile) -> bool:
    return (
        profile.start_weight_kg < 40.0
        or profile.start_weight_kg > 220.0
        or profile.adherence_base < 0.15
        or profile.binge_sensitivity > 0.9
    )


def evaluate_protocol(fly: Fly, profile: UserProfile) -> SafetyReport:
    report = SafetyReport()
    floor = safe_calorie_floor(profile.start_weight_kg, profile.maintenance_kcal)

    if fly.calorie_target < floor:
        report.safe = False
        report.blocked.append(
            f"calorie target {fly.calorie_target} is below safe floor {floor} kcal"
        )
    if fly.protein_pct < 0.15:
        report.safe = False
        report.blocked.append("protein percentage is below 15%")
    if fly.protein_pct > 0.60:
        report.safe = False
        report.blocked.append("protein percentage is above 60%")
    if fly.sleep_target < 6.0:
        report.safe = False
        report.blocked.append(f"sleep target {fly.sleep_target}h is below 6h")
    if fly.meal_window < 8:
        report.safe = False
        report.blocked.append("meal window is narrower than 8 hours")

    if profile.binge_sensitivity > 0.7 and not fly.late_night_rule:
        report.warnings.append(
            "high binge sensitivity with no planned late-night snack; risk of rebound"
        )
    if profile.binge_sensitivity > 0.75 and fly.refeed_schedule == "none":
        report.warnings.append(
            "high binge sensitivity with no planned refeed; risk of rebound"
        )

    report.escalation = has_medical_red_flags(profile)
    return report


def safe_champion(fly: Fly, profile: UserProfile) -> Fly:
    """Repair a champion protocol to a safe version without rerunning the swarm."""
    floor = safe_calorie_floor(profile.start_weight_kg, profile.maintenance_kcal)
    repaired = Fly(
        calorie_target=max(fly.calorie_target, floor),
        protein_pct=max(0.15, min(0.60, fly.protein_pct)),
        carb_pct=max(0.15, min(0.50, fly.carb_pct)),
        meal_window=max(8, fly.meal_window),
        meal_count=max(2, fly.meal_count),
        late_night_rule=fly.late_night_rule,
        workout_freq=max(0, fly.workout_freq),
        workout_type=fly.workout_type,
        sleep_target=max(6.5, fly.sleep_target),
        refeed_schedule=fly.refeed_schedule,
        step_target=max(3000, fly.step_target),
    )._normalize()
    return repaired


def escalation_message(profile: UserProfile) -> str:
    return (
        "This profile includes signals that are outside self-directed weight-loss "
        "coaching. Please consult a licensed healthcare professional before changing "
        "your diet or activity."
    )
