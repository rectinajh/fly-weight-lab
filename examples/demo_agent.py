"""Run Fly Weight-Lab as a background agent.

The agent ingests weekly weights and only surfaces a decision when something
materially changes (a new protocol is found, or a plateau appears). Quiet weeks
produce no output, which is exactly the hackathon theme.

Run from the repository root:
    python examples/demo_agent.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.agent_loop import WeightLossAgent
from flylab.connectome import load_params
from flylab.genotype import Fly
from flylab.twin import BehavioralTwin, UserProfile


def main() -> None:
    profile = UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        water_noise_kg=0.4,
        maintenance_kcal=2300.0,
    )

    # The user's current protocol: aggressive and, in reality, backfiring.
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

    params = load_params()
    agent = WeightLossAgent(profile, current, connectome=params)

    # Observed reality: the user stays on the aggressive protocol. We simulate
    # their weekly weights with the grounded twin.
    observed_twin = BehavioralTwin(profile, connectome=params)
    curve = observed_twin.simulate(current, 12)

    print("=" * 68)
    print("BACKGROUND AGENT — 12 WEEKS, QUIET UNLESS SOMETHING CHANGES")
    print("=" * 68)
    for week in range(1, 13):
        agent.ingest(float(curve[week]))
        decision = agent.tick(week)
        if decision:
            print(f"  week {week:>2}: SURFACED -> {decision.action}")
        else:
            print(f"  week {week:>2}: (quiet)")

    surfaces = [h for h in agent.history if h["surfaced"]]
    print("\n" + "=" * 68)
    print(f"SUMMARY: {len(surfaces)} decision(s) surfaced across 12 weeks.")
    print("The agent ran quietly the rest of the time.")


if __name__ == "__main__":
    main()
