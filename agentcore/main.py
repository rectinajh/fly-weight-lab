"""AgentCore Runtime entrypoint for Fly Weight-Lab.

Wraps the Strands agent from ``flylab.strands_agent`` in a Bedrock AgentCore
app. The runtime exposes ``POST /invocations`` and ``GET /ping`` automatically.

Default invocation payload (local, no model or AWS required):
    {}

Optional model-driven payload:
    {"mode": "agent", "prompt": "Detect a plateau and surface the one decision for this user."}
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

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
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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


def _connectome_dict() -> dict[str, Any]:
    params = load_params()
    return {
        "source": params.source,
        "n_kenyon": params.n_kenyon,
        "n_dan": params.n_dan,
        "n_mbon": params.n_mbon,
        "kc_mbon_convergence": round(params.kc_mbon_convergence, 1),
        "dan_mbon_convergence": round(params.dan_mbon_convergence, 1),
        "reward_punishment_ratio": round(params.reward_punishment_ratio, 2),
        "context_recurrence_ratio": round(params.context_recurrence_ratio, 4),
    }


def _serialize_evolution(history: list) -> dict[str, Any]:
    generations = []
    for generation, best, mean, scores in history:
        ordered = sorted(scores)
        median = ordered[len(ordered) // 2]
        farm = "".join("1" if score >= median else "0" for score in scores)
        generations.append(
            {"generation": generation, "best": best, "mean": mean, "farm": farm}
        )
    return {"generations": generations}


def _load_demo_records(user_id: str) -> tuple[list, list, dict | None]:
    from flylab.calibration import load_records

    weight_path = DATA_DIR / "real_users" / f"{user_id}_weight.csv"
    if not weight_path.exists():
        return [], [], None
    weight_records = load_records(weight_path)
    activity_records: list[dict] = []
    activity_path = DATA_DIR / "real_users" / f"{user_id}_activity.csv"
    if activity_path.exists():
        with activity_path.open(newline="", encoding="utf-8") as handle:
            activity_records = list(csv.DictReader(handle))
        activity_records.sort(key=lambda row: row.get("date", ""))
    source = {
        "path": f"data/real_users/{user_id}",
        "zenodo": "10.5281/zenodo.53894",
        "license": "CC-BY-4.0",
    }
    return weight_records, activity_records, source


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
            "connectome": _connectome_dict(),
            "evolution": _serialize_evolution(result.history),
        }


async def _business_flow(request: Request) -> JSONResponse:
    """Run the real-data product loop from an uploaded CSV payload."""
    from flylab.business_flow import run_business_flow

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "request body must be JSON"}, status_code=400)

    report = _run_business_flow_payload(payload)
    if "error" in report:
        return JSONResponse(report, status_code=400)
    return JSONResponse(report)


def _run_business_flow_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a business-flow payload and run it (shared by route + entrypoint)."""
    from flylab.business_flow import run_business_flow

    user_id = str(payload.get("user_id", "uploaded_user"))
    weight_records = payload.get("weight_records")
    activity_records = payload.get("activity_records", [])

    demo_source = None
    if isinstance(weight_records, list) and weight_records:
        weight_records = weight_records
    else:
        weight_records, activity_records, demo_source = _load_demo_records(user_id)
        if not weight_records:
            return {"error": f"no real records found for user_id={user_id}"}

    if not isinstance(activity_records, list):
        return {"error": "activity_records must be a list"}

    report = run_business_flow(
        user_id,
        weight_records,
        activity_records,
        population_size=int(payload.get("population_size", 250)),
        generations=int(payload.get("generations", 25)),
        seed=int(payload.get("seed", 7)),
        memory_root=Path("runs/memory"),
        reset_memory=True,
    )
    report["connectome"] = _connectome_dict()
    if demo_source:
        report["data_source"] = demo_source
    return report


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

        if payload.get("mode") in {"business_flow", "demo"}:
            return _run_business_flow_payload(payload)

        return _run_local_swarm(payload)


app.add_route("/business-flow", _business_flow, methods=["POST"])
