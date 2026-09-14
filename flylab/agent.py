"""Decision surface: turn the evolved champion into one surfaced decision."""

from __future__ import annotations

from dataclasses import dataclass

from .genotype import Fly
from .twin import UserProfile


@dataclass
class Decision:
    headline: str
    action: str
    reason: str


def surface_decision(
    current: Fly | None,
    champion: Fly,
    plateau_detected: bool,
    profile: UserProfile,
) -> Decision:
    actions: list[str] = []
    reasons: list[str] = []

    if current is not None:
        if champion.calorie_target > current.calorie_target:
            actions.append(
                f"Raise your daily calorie target from {current.calorie_target} to {champion.calorie_target} kcal"
            )
            reasons.append(
                "Further restriction would push adherence down and trigger metabolic adaptation"
            )
        elif champion.calorie_target < current.calorie_target:
            drop = current.calorie_target - champion.calorie_target
            actions.append(
                f"Lower your daily calorie target from {current.calorie_target} to {champion.calorie_target} kcal"
            )
            if drop < 150:
                reasons.append(
                    "A slightly tighter deficit that stays above the safety floor"
                )
            else:
                reasons.append(
                    "A modest deficit that stays above the safety floor instead of a crash cut"
                )
        if champion.late_night_rule and not current.late_night_rule:
            actions.append("Keep a fixed late-night snack")
            reasons.append(
                "For binge-prone users, a fixed late-night snack lowers binge risk"
            )
        if champion.late_night_rule is False and current.late_night_rule:
            actions.append("Drop the fixed late-night snack")
            reasons.append(
                "Your current binge risk is low enough that the protective snack is no longer needed"
            )
        if champion.refeed_schedule != "none" and current.refeed_schedule == "none":
            actions.append(
                f"Schedule a planned refeed day ({champion.refeed_schedule})"
            )
            reasons.append(
                "A planned refeed eases the rebound pressure of prolonged restriction"
            )
        if champion.refeed_schedule == "none" and current.refeed_schedule != "none":
            actions.append("Remove the planned refeed day")
            reasons.append(
                "Your binge risk no longer needs the refeed buffer, so removing it improves the real deficit"
            )
        if champion.sleep_target > current.sleep_target:
            actions.append(f"Prioritize sleep up to {champion.sleep_target} hours")
            reasons.append(
                "Sleep debt raises binge risk and lowers adherence at the same time"
            )
        if champion.meal_window > current.meal_window:
            actions.append(f"Widen the eating window to {champion.meal_window} hours")
            reasons.append("A narrower eating window is a common binge trigger")
        if champion.step_target > current.step_target:
            actions.append(
                f"Raise your daily step target from {current.step_target} to {champion.step_target}"
            )
            reasons.append(
                "Raise total energy expenditure through daily movement instead of cutting food further"
            )
        if (
            champion.workout_freq != current.workout_freq
            or champion.workout_type != current.workout_type
        ):
            actions.append(
                f"Shift training to {champion.workout_freq} {champion.workout_type} sessions per week"
            )
            reasons.append(
                "Training volume should serve long-term adherence, not create extra dietary pressure"
            )

    if not actions:
        actions.append(f"Lock in this protocol: {champion.describe()}")
        reasons.append(
            "After multi-generation convergence, this champion balances adherence and fat loss best"
        )

    headline = "Plateau detected — switch protocol" if plateau_detected else "Switch to this protocol this week"
    return Decision(
        headline=headline,
        action="; ".join(actions[:2]),
        reason=". ".join(reasons[:2]) + ".",
    )
