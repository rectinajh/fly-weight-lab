"""Runnable MVP demo for the Fly Weight-Lab plateau breaker.

Run from the repository root:
    python examples/demo_plateau_breaker.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.agent import surface_decision
from flylab.evolution import Swarm
from flylab.genotype import Fly
from flylab.plateau import detect_plateau
from flylab.twin import BehavioralTwin, UserProfile
from flylab.visualize import chart, print_evolution


def demo_plateau_breaker() -> None:
    profile = UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        water_noise_kg=0.4,
        maintenance_kcal=2300.0,
    )
    twin = BehavioralTwin(profile)

    # The user's current protocol: aggressive and clearly stalling.
    current = Fly(
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

    current_curve = twin.simulate(current, 12)
    stalled, change = detect_plateau(current_curve)

    print("=" * 68)
    print("PLATEAU BREAKER DEMO")
    print("=" * 68)
    print(f"User: {profile.name}")
    print(f"Current aggressive protocol: {current.describe()}")
    print(f"Current 12-week change: {change:+.2f} kg | plateau detected: {stalled}")
    print(
        f"Current adherence: {twin.adherence(current):.2f} "
        f"| binge risk: {twin.binge_risk(current):.2f}"
    )

    swarm = Swarm(twin, population_size=600, generations=50, seed=7)
    result = swarm.run()
    print_evolution(result, farm_every=10)
    chart_path = chart(result, out_path="/tmp/flylab_plateau.png")
    if chart_path:
        print(f"\nChart saved: {chart_path}")

    decision = surface_decision(current, result.best_fly, stalled, profile)
    print("\n" + "=" * 68)
    print("SURFACED DECISION")
    print("=" * 68)
    print(f"[{decision.headline}]")
    print(f"Action: {decision.action}")
    print(f"Why:    {decision.reason}")
    print(f"\nChampion protocol: {result.best_fly.describe()}")
    print(
        f"Champion adherence: {twin.adherence(result.best_fly):.2f} "
        f"| binge risk: {twin.binge_risk(result.best_fly):.2f}"
    )


def demo_two_users() -> None:
    print("\n\n" + "=" * 68)
    print("TWO USERS, SAME GOAL, OPPOSITE PLANS")
    print("=" * 68)

    users = (
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
            binge_sensitivity=0.1,
            metabolic_adaptation=0.2,
            maintenance_kcal=2300.0,
        ),
    )

    for profile in users:
        twin = BehavioralTwin(profile)
        result = Swarm(twin, population_size=600, generations=50, seed=7).run()
        fly = result.best_fly
        print(f"\n{profile.name}: {fly.describe()}")
        print(
            f"  late_night={fly.late_night_rule}, refeed={fly.refeed_schedule}, "
            f"calories={fly.calorie_target}, sleep={fly.sleep_target}h"
        )
        print(
            f"  adherence={twin.adherence(fly):.2f}, "
            f"binge_risk={twin.binge_risk(fly):.2f}, best_fitness={result.best_score:.2f}"
        )


if __name__ == "__main__":
    demo_plateau_breaker()
    demo_two_users()
