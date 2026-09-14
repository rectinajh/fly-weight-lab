"""Strands Agents SDK integration.

The local path uses a deterministic ``MockModel`` so the full Strands tool-call
loop runs without API keys. For a real model, set:

    STRANDS_MODEL_PROVIDER=ollama
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL=llama3.2

or ``openai`` / ``anthropic`` / ``bedrock`` when the corresponding SDK and
credentials are available. ``mock`` is the default.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any, AsyncGenerator

from .agent import Decision, surface_decision
from .connectome import load_params
from .evolution import Swarm
from .genotype import Fly
from .memory import UserMemoryStore
from .plateau import detect_plateau
from .twin import BehavioralTwin, UserProfile


def default_profile() -> UserProfile:
    return UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        water_noise_kg=0.4,
        maintenance_kcal=2300.0,
    )


def default_current() -> Fly:
    return Fly(
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


def profile_from_dict(data: dict[str, Any]) -> UserProfile:
    return UserProfile(
        name=str(data.get("name", "user")),
        start_weight_kg=float(data.get("start_weight_kg", 88.0)),
        adherence_base=float(data.get("adherence_base", 0.6)),
        binge_sensitivity=float(data.get("binge_sensitivity", 0.6)),
        metabolic_adaptation=float(data.get("metabolic_adaptation", 0.5)),
        water_noise_kg=float(data.get("water_noise_kg", 0.4)),
        maintenance_kcal=float(data.get("maintenance_kcal", 2300.0)),
    )


def fly_from_dict(data: dict[str, Any]) -> Fly:
    return Fly(
        calorie_target=int(data["calorie_target"]),
        protein_pct=float(data["protein_pct"]),
        carb_pct=float(data["carb_pct"]),
        meal_window=int(data["meal_window"]),
        meal_count=int(data["meal_count"]),
        late_night_rule=bool(data["late_night_rule"]),
        workout_freq=int(data["workout_freq"]),
        workout_type=str(data["workout_type"]),
        sleep_target=float(data["sleep_target"]),
        refeed_schedule=str(data["refeed_schedule"]),
        step_target=int(data["step_target"]),
    )._normalize()


def decision_to_dict(decision: Decision) -> dict[str, str]:
    return {
        "headline": decision.headline,
        "action": decision.action,
        "reason": decision.reason,
    }


def build_tools():
    """Return narrow Strands tools for the model to compose."""
    from strands import tool

    @tool
    def get_user_context(
        user_id: str = "demo",
        start_weight_kg: float = 88.0,
        adherence_base: float = 0.6,
        binge_sensitivity: float = 0.6,
        metabolic_adaptation: float = 0.5,
        maintenance_kcal: float = 2300.0,
    ) -> dict:
        """Load the user profile and current protocol context."""
        profile = UserProfile(
            name=user_id,
            start_weight_kg=start_weight_kg,
            adherence_base=adherence_base,
            binge_sensitivity=binge_sensitivity,
            metabolic_adaptation=metabolic_adaptation,
            water_noise_kg=0.4,
            maintenance_kcal=maintenance_kcal,
        )
        return {"profile": asdict(profile), "current": asdict(default_current())}

    @tool
    def detect_plateau(weights: list[float], threshold_kg: float = 0.2) -> dict:
        """Return whether weekly weights have stalled into a plateau."""
        stalled, change = detect_plateau(weights, threshold_kg=threshold_kg)
        return {"plateau": bool(stalled), "recent_change_kg": round(float(change), 2)}

    @tool
    def simulate_candidate(
        calorie_target: int,
        protein_pct: float,
        carb_pct: float,
        meal_window: int,
        meal_count: int,
        late_night_rule: bool,
        workout_freq: int,
        workout_type: str,
        sleep_target: float,
        refeed_schedule: str,
        step_target: int,
        binge_sensitivity: float = 0.6,
        adherence_base: float = 0.6,
        metabolic_adaptation: float = 0.5,
        horizon_weeks: int = 12,
    ) -> dict:
        """Simulate one candidate protocol through the behavioral twin."""
        profile = UserProfile(
            name="candidate",
            start_weight_kg=88.0,
            adherence_base=adherence_base,
            binge_sensitivity=binge_sensitivity,
            metabolic_adaptation=metabolic_adaptation,
            water_noise_kg=0.4,
            maintenance_kcal=2300.0,
        )
        fly = Fly(
            calorie_target=calorie_target,
            protein_pct=protein_pct,
            carb_pct=carb_pct,
            meal_window=meal_window,
            meal_count=meal_count,
            late_night_rule=late_night_rule,
            workout_freq=workout_freq,
            workout_type=workout_type,
            sleep_target=sleep_target,
            refeed_schedule=refeed_schedule,
            step_target=step_target,
        )._normalize()
        twin = BehavioralTwin(profile, connectome=load_params())
        curve = twin.simulate(fly, horizon_weeks)
        return {
            "start_weight_kg": round(float(curve[0]), 2),
            "end_weight_kg": round(float(curve[-1]), 2),
            "loss_kg": round(float(curve[0] - curve[-1]), 2),
            "adherence": round(twin.adherence(fly), 3),
            "binge_risk": round(twin.binge_risk(fly), 3),
            "plateau_risk": round(twin.plateau_risk(curve), 3),
        }

    @tool
    def evolve_champion(
        binge_sensitivity: float = 0.6,
        metabolic_adaptation: float = 0.5,
        adherence_base: float = 0.6,
        start_weight_kg: float = 88.0,
        maintenance_kcal: float = 2300.0,
        population_size: int = 300,
        generations: int = 30,
    ) -> dict:
        """Run the fruit-fly swarm and return the evolved champion protocol."""
        profile = UserProfile(
            name="swarm",
            start_weight_kg=start_weight_kg,
            adherence_base=adherence_base,
            binge_sensitivity=binge_sensitivity,
            metabolic_adaptation=metabolic_adaptation,
            water_noise_kg=0.4,
            maintenance_kcal=maintenance_kcal,
        )
        twin = BehavioralTwin(profile, connectome=load_params())
        result = Swarm(
            twin,
            population_size=int(population_size),
            generations=int(generations),
            seed=7,
        ).run()
        return {
            "champion": asdict(result.best_fly),
            "fitness": round(result.best_score, 3),
            "adherence": round(twin.adherence(result.best_fly), 3),
            "binge_risk": round(twin.binge_risk(result.best_fly), 3),
        }

    @tool
    def surface_decision(
        current: dict,
        champion: dict,
        plateau_detected: bool = False,
    ) -> dict:
        """Turn the current and champion protocols into one surfaced decision."""
        profile = default_profile()
        decision = surface_decision(
            fly_from_dict(current),
            fly_from_dict(champion),
            bool(plateau_detected),
            profile,
        )
        return decision_to_dict(decision)

    @tool
    def record_feedback(
        user_id: str,
        accepted: bool,
        adherence: float,
        weight_delta_kg: float,
    ) -> dict:
        """Record a human decision so the next run can learn from it."""
        feedback = {
            "user_id": user_id,
            "accepted": bool(accepted),
            "adherence": round(float(adherence), 3),
            "weight_delta_kg": round(float(weight_delta_kg), 2),
        }
        return UserMemoryStore().append_feedback(user_id, feedback)

    return [
        get_user_context,
        detect_plateau,
        simulate_candidate,
        evolve_champion,
        surface_decision,
        record_feedback,
    ]


class MockModel:
    """Deterministic Strands-compatible model for offline demos and tests.

    It forces a narrow tool-call loop: evolve a champion, surface one decision,
    then finish. This proves the agent orchestration without an API key.
    """

    stateful = False

    def __init__(self) -> None:
        self._stage = 0

    def update_config(self, **kwargs: Any) -> None:
        return None

    def get_config(self) -> dict:
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("MockModel does not support structured output")

    async def stream(
        self,
        messages,
        tool_specs=None,
        system_prompt=None,
        *,
        tool_choice=None,
        system_prompt_content=None,
        invocation_state=None,
        cancel_signal=None,
        **kwargs,
    ) -> AsyncGenerator[dict[str, Any], None]:
        stage = self._stage
        self._stage += 1

        if stage == 0:
            yield {"messageStart": {"role": "assistant"}}
            yield {
                "contentBlockStart": {
                    "contentBlockIndex": 0,
                    "start": {
                        "toolUse": {
                            "toolUseId": "mock_evolve",
                            "name": "evolve_champion",
                        }
                    },
                }
            }
            yield {
                "contentBlockDelta": {
                    "contentBlockIndex": 0,
                    "delta": {
                        "toolUse": {
                            "input": json.dumps(
                                {
                                    "binge_sensitivity": 0.6,
                                    "metabolic_adaptation": 0.5,
                                    "adherence_base": 0.6,
                                }
                            )
                        }
                    },
                }
            }
            yield {"contentBlockStop": {"contentBlockIndex": 0}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            return

        if stage == 1:
            champion = {
                "calorie_target": 1800,
                "protein_pct": 0.35,
                "carb_pct": 0.30,
                "meal_window": 12,
                "meal_count": 4,
                "late_night_rule": True,
                "workout_freq": 3,
                "workout_type": "mix",
                "sleep_target": 8.0,
                "refeed_schedule": "weekly",
                "step_target": 7000,
            }
            yield {"messageStart": {"role": "assistant"}}
            yield {
                "contentBlockStart": {
                    "contentBlockIndex": 0,
                    "start": {
                        "toolUse": {
                            "toolUseId": "mock_surface",
                            "name": "surface_decision",
                        }
                    },
                }
            }
            yield {
                "contentBlockDelta": {
                    "contentBlockIndex": 0,
                    "delta": {
                        "toolUse": {
                            "input": json.dumps(
                                {
                                    "current": asdict(default_current()),
                                    "champion": champion,
                                    "plateau_detected": True,
                                }
                            )
                        }
                    },
                }
            }
            yield {"contentBlockStop": {"contentBlockIndex": 0}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            return

        text = "The swarm evolved a gentler protocol and surfaced one decision for the user."
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "contentBlockIndex": 0,
                "start": {},
            }
        }
        yield {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"text": text},
            }
        }
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "end_turn"}}


def build_model(provider: str | None = None):
    provider = provider or os.getenv("STRANDS_MODEL_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockModel()
    if provider == "ollama":
        from strands.models import OllamaModel

        return OllamaModel(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model_id=os.getenv("OLLAMA_MODEL", "llama3.2"),
        )
    if provider == "openai":
        import openai
        from strands.models import OpenAIModel

        return OpenAIModel(
            client=openai.AsyncOpenAI(),
            model_id=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )
    if provider == "anthropic":
        from strands.models import AnthropicModel

        return AnthropicModel(
            model_id=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            max_tokens=1024,
        )
    if provider == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel()
    raise ValueError(f"Unsupported STRANDS_MODEL_PROVIDER: {provider}")


def build_strands_agent(model=None, provider: str | None = None):
    """Return a Strands agent wired with the Fly Weight-Lab narrow tools."""
    from strands import Agent

    system_prompt = (
        "You are a weight-loss agent grounded in the real Drosophila mushroom body "
        "connectome. Use the narrow tools to inspect context, detect a plateau, "
        "evolve a champion protocol, surface exactly one decision, and record human "
        "feedback. Stay quiet unless there is a real decision to make."
    )
    return Agent(
        model=model or build_model(provider),
        tools=build_tools(),
        system_prompt=system_prompt,
    )
