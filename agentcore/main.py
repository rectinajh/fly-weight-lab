"""AgentCore Runtime entrypoint for Fly Weight-Lab.

Wraps the Strands agent from ``flylab.strands_agent`` in a Bedrock AgentCore
app. The runtime exposes ``POST /invocations`` and ``GET /ping`` automatically.

Default invocation payload (local, no model or AWS required):
    {}

Optional model-driven payload:
    {"mode": "agent", "prompt": "Detect a plateau and surface the one decision for this user."}
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp
from starlette.middleware.cors import CORSMiddleware

from flylab.connectome import load_params
from flylab.evolution import Swarm
from flylab.genotype import Fly
from flylab.safety import evaluate_protocol, safe_champion
from flylab.strands_agent import build_strands_agent
from flylab.telemetry import emit, timed
from flylab.twin import BehavioralTwin, UserProfile

app = BedrockAgentCoreApp()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_strands_agent()
    return _agent


def _default_current() -> Fly:
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


def _run_local_swarm(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the fruit-fly swarm directly, without a model call."""
    with timed("local_swarm"):
        profile = UserProfile(
            name="deployed_smoke_test",
            start_weight_kg=88.0,
            adherence_base=float(payload.get("adherence_base", 0.6)),
            binge_sensitivity=float(payload.get("binge_sensitivity", 0.6)),
            metabolic_adaptation=float(payload.get("metabolic_adaptation", 0.5)),
            water_noise_kg=0.4,
            maintenance_kcal=2300.0,
        )
        twin = BehavioralTwin(profile, connectome=load_params())
        result = Swarm(twin, population_size=300, generations=30, seed=7).run()
        champion = result.best_fly
        safety = evaluate_protocol(champion, profile)
        if not safety.safe:
            champion = safe_champion(champion, profile)
            safety = evaluate_protocol(champion, profile)
        emit("local_champion", calories=champion.calorie_target, safety=safety.safe)
        return {
            "mode": "local",
            "champion": asdict(champion),
            "fitness": round(result.best_score, 3),
            "adherence": round(twin.adherence(champion), 3),
            "binge_risk": round(twin.binge_risk(champion), 3),
            "safety": safety.as_dict(),
        }


@app.entrypoint
async def main(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the fruit-fly agent and return a serializable result.

    Local mode is the default because the hackathon demo should work without
    AWS credentials. Model-driven mode is opt-in.
    """
    with timed("agent_invocation", mode=payload.get("mode", "local")):
        if payload.get("mode") == "agent":
            prompt = payload.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                return {"error": "payload.prompt must be a non-empty string"}

            result = await _get_agent().invoke_async(prompt)
            if hasattr(result, "to_dict"):
                return {"result": result.to_dict()}
            return {"result": str(result)}

        return _run_local_swarm(payload)
