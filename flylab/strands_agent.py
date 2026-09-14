"""Strands Agents SDK integration (optional model-driven path).

Exposes Fly Weight-Lab functions as Strands tools so a model-driven agent can
drive the swarm. The SDK itself runs locally; only the default Bedrock model
provider needs AWS credentials. Pass ``model=...`` to use another provider.

    pip install strands-agents
    from flylab.strands_agent import build_strands_agent
    agent = build_strands_agent()
    # Optional model-driven run; the repo's default local path does not use this.
"""

from __future__ import annotations

from .connectome import load_params
from .evolution import Swarm
from .plateau import detect_plateau
from .twin import BehavioralTwin, UserProfile


def _default_profile() -> UserProfile:
    return UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        water_noise_kg=0.4,
        maintenance_kcal=2300.0,
    )


def build_strands_agent(model=None):
    """Return a strands.Agent wired with the Fly Weight-Lab tools."""
    from strands import Agent, tool

    @tool
    def run_swarm(
        calorie_target: int,
        binge_sensitivity: float,
        metabolic_adaptation: float,
    ) -> dict:
        """Run the fruit-fly swarm for a user and return the evolved champion protocol.

        The swarm is grounded in the real Drosophila mushroom-body connectome.
        """
        profile = _default_profile()
        profile.binge_sensitivity = float(binge_sensitivity)
        profile.metabolic_adaptation = float(metabolic_adaptation)
        twin = BehavioralTwin(profile, connectome=load_params())
        result = Swarm(twin, population_size=300, generations=30, seed=7).run()
        fly = result.best_fly
        return {
            "champion_calories": fly.calorie_target,
            "champion_late_night": fly.late_night_rule,
            "champion_refeed": fly.refeed_schedule,
            "champion_sleep_h": fly.sleep_target,
            "champion_meal_window_h": fly.meal_window,
            "fitness": round(result.best_score, 2),
            "adherence": round(twin.adherence(fly), 2),
            "binge_risk": round(twin.binge_risk(fly), 2),
        }

    @tool
    def is_plateau(weights: list[float], threshold_kg: float = 0.2) -> bool:
        """Return True if the last few weekly weights have stalled into a plateau."""
        import numpy as np

        stalled, _ = detect_plateau(np.asarray(weights, dtype=float), threshold_kg=threshold_kg)
        return bool(stalled)

    system_prompt = (
        "You are a weight-loss agent grounded in the real Drosophila mushroom body "
        "connectome. Use the tools to run the fruit-fly swarm and surface exactly one "
        "decision for the user. Run quietly and only surface when there is a real "
        "decision to make."
    )

    kwargs = {"tools": [run_swarm, is_plateau], "system_prompt": system_prompt}
    if model is not None:
        kwargs["model"] = model
    return Agent(**kwargs)
