"""Ground the behavioral twin in the real Drosophila mushroom body.

Run from the repository root:
    python examples/demo_connectome.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.agent import surface_decision
from flylab.connectome import load_params
from flylab.evolution import Swarm
from flylab.genotype import Fly
from flylab.plateau import detect_plateau
from flylab.twin import BehavioralTwin, UserProfile
from flylab.visualize import print_evolution


def main() -> None:
    params = load_params()

    print("=" * 68)
    print("REAL MUSHROOM BODY — Janelia MaleCNS v1.0")
    print("=" * 68)
    print(f"  Kenyon cells (context):            {params.n_kenyon}")
    print(f"  Dopaminergic neurons (reward):     {params.n_dan}")
    print(f"  MBONs (decision):                  {params.n_mbon}")
    print(f"  KC -> MBON convergence:            {params.kc_mbon_convergence:.0f} KCs per MBON")
    print(f"  DAN -> MBON modulation:            {params.dan_mbon_convergence:.1f} DANs per MBON")
    print(
        f"  Reward (PAM) : Punishment (PPL):   {params.reward_punishment_ratio:.2f} : 1"
    )
    print(f"  Context recurrence (KC->KC share): {params.context_recurrence_ratio:.1%}")

    profile = UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        water_noise_kg=0.4,
        maintenance_kcal=2300.0,
    )

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

    plain = BehavioralTwin(profile)
    grounded = BehavioralTwin(profile, connectome=params)

    print("\n" + "=" * 68)
    print("WHY THE REAL WIRING CHANGES THE PREDICTION")
    print("=" * 68)
    print(f"  Aggressive protocol binge risk, un-grounded: {plain.binge_risk(current):.2f}")
    print(f"  Aggressive protocol binge risk, grounded:    {grounded.binge_risk(current):.2f}")
    print(
        "  The connectome tells us reward outranks punishment, so restriction"
    )
    print("  is answered with stronger craving pressure than a hand-tuned model assumes.")

    result = Swarm(grounded, population_size=600, generations=50, seed=7).run()
    print_evolution(result, farm_every=10)

    stalled, change = detect_plateau(grounded.simulate(current, 12))
    decision = surface_decision(current, result.best_fly, stalled, profile)

    print("\n" + "=" * 68)
    print("SURFACED DECISION (connectome-grounded twin)")
    print("=" * 68)
    print(f"[{decision.headline}]")
    print(f"Action: {decision.action}")
    print(f"Why:    {decision.reason}")
    print(f"\nChampion protocol: {result.best_fly.describe()}")
    print(
        f"Champion adherence: {grounded.adherence(result.best_fly):.2f} "
        f"| binge risk: {grounded.binge_risk(result.best_fly):.2f}"
    )


if __name__ == "__main__":
    main()
