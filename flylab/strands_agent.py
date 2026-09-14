"""Strands Agents SDK integration.

Demo mode uses a deterministic ``FlowModel`` that composes the six narrow
tools against real Fitbit users. Set ``STRANDS_MODEL_PROVIDER=bedrock`` (or
ollama / openai / anthropic) to let a real model choose the same tools.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, AsyncGenerator

from .agent import Decision, surface_decision as compose_decision
from .business_flow import (
    build_current,
    connectome_effect,
    load_preloaded_user,
    run_business_flow,
    weekly_checkpoints,
)
from .calibration import apply_archetype, archetype_for_user, fit_profile
from .connectome import load_params
from .evolution import Swarm
from .genotype import Fly
from .memory import UserMemoryStore
from .plateau import detect_plateau as detect_weight_plateau
from .safety import safe_calorie_floor
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


def _compact(value: Any) -> Any:
    if isinstance(value, dict):
        skip = {"evolution", "agent_state", "projected_weight", "flow", "farm"}
        return {
            key: _compact(item)
            for key, item in value.items()
            if key not in skip
        }
    if isinstance(value, list) and len(value) > 24:
        return {"n": len(value), "head": value[:3], "tail": value[-3:]}
    return value


class LabSession:
    """Shared mutable state so Strands tools compose one coherent demo run."""

    def __init__(
        self,
        user_id: str = "6962181067",
        weight_records: list | None = None,
        activity_records: list | None = None,
        population_size: int = 180,
        generations: int = 18,
        seed: int = 7,
        horizon_weeks: int = 12,
        memory_root: str | Path | None = None,
    ) -> None:
        self.user_id = user_id
        self.weight_records = list(weight_records or [])
        self.activity_records = list(activity_records or [])
        self.population_size = population_size
        self.generations = generations
        self.seed = seed
        self.horizon_weeks = horizon_weeks
        self.memory_root = memory_root
        self.data_source: dict | None = None
        self.profile: UserProfile | None = None
        self.current: Fly | None = None
        self.champion: Fly | None = None
        self.weights: list[float] = []
        self.report: dict[str, Any] | None = None
        self.tool_trace: list[dict[str, Any]] = []
        self.archetype = "fitted"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "LabSession":
        user_id = str(payload.get("user_id", "6962181067"))
        session = cls(
            user_id=user_id,
            weight_records=payload.get("weight_records") or [],
            activity_records=payload.get("activity_records") or [],
            population_size=int(payload.get("population_size", 180)),
            generations=int(payload.get("generations", 18)),
            seed=int(payload.get("seed", 7)),
            horizon_weeks=int(payload.get("horizon_weeks", 12)),
            memory_root=payload.get("memory_root"),
        )
        if not session.weight_records:
            weights, activity, source = load_preloaded_user(user_id)
            session.weight_records = weights
            session.activity_records = activity
            session.data_source = source
        return session

    def record(self, tool: str, payload: dict[str, Any], output: Any) -> Any:
        self.tool_trace.append(
            {"tool": tool, "input": _compact(payload), "output": _compact(output)}
        )
        return output


def build_tools(session: LabSession | None = None):
    """Return narrow Strands tools for the model to compose."""
    from strands import tool

    lab = session or LabSession()

    @tool
    def get_user_context(user_id: str = "6962181067") -> dict:
        """Load the real user log, fit the behavioral twin, and return context."""
        if user_id and user_id != lab.user_id and not lab.weight_records:
            lab.user_id = user_id
            weights, activity, source = load_preloaded_user(user_id)
            lab.weight_records = weights
            lab.activity_records = activity
            lab.data_source = source
        if not lab.weight_records:
            profile = default_profile()
            current = default_current()
            lab.profile = profile
            lab.current = current
            lab.weights = [profile.start_weight_kg]
            out = {"profile": asdict(profile), "current": asdict(current), "source": "defaults"}
            return lab.record("get_user_context", {"user_id": user_id}, out)

        calibration = fit_profile(lab.weight_records, name=f"fitbit_{lab.user_id}")
        lab.archetype = archetype_for_user(lab.user_id, calibration)
        lab.profile = apply_archetype(calibration.profile, lab.archetype)
        lab.current = build_current(lab.profile, lab.activity_records, lab.archetype)
        checkpoints = weekly_checkpoints(lab.weight_records)
        lab.weights = [float(row["weight_kg"]) for row in checkpoints] or [
            lab.profile.start_weight_kg
        ]
        out = {
            "profile": asdict(lab.profile),
            "current": asdict(lab.current),
            "archetype": lab.archetype,
            "adherence_source": calibration.adherence_source,
            "observed_weight_change_kg": calibration.observed_loss_kg,
            "n_records": calibration.n_records,
            "weekly_weights": lab.weights,
            "calorie_floor": safe_calorie_floor(
                lab.profile.start_weight_kg, lab.profile.maintenance_kcal
            ),
        }
        return lab.record("get_user_context", {"user_id": user_id}, out)

    @tool
    def detect_plateau(weights: list[float] | None = None, threshold_kg: float = 0.2) -> dict:
        """Return whether weekly weights have stalled into a plateau."""
        series = weights if weights else lab.weights
        stalled, change = detect_weight_plateau(series, threshold_kg=threshold_kg)
        out = {"plateau": bool(stalled), "recent_change_kg": round(float(change), 2)}
        return lab.record("detect_plateau", {"n_weights": len(series)}, out)

    @tool
    def simulate_candidate(
        calorie_target: int = 1500,
        protein_pct: float = 0.40,
        carb_pct: float = 0.25,
        meal_window: int = 8,
        meal_count: int = 3,
        late_night_rule: bool = False,
        workout_freq: int = 5,
        workout_type: str = "cardio",
        sleep_target: float = 7.0,
        refeed_schedule: str = "none",
        step_target: int = 10000,
        binge_sensitivity: float = 0.6,
        adherence_base: float = 0.6,
        metabolic_adaptation: float = 0.5,
        horizon_weeks: int = 12,
    ) -> dict:
        """Simulate one candidate protocol through the behavioral twin."""
        profile = lab.profile or UserProfile(
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
        out = {
            "start_weight_kg": round(float(curve[0]), 2),
            "end_weight_kg": round(float(curve[-1]), 2),
            "loss_kg": round(float(curve[0] - curve[-1]), 2),
            "adherence": round(twin.adherence(fly), 3),
            "binge_risk": round(twin.binge_risk(fly), 3),
            "plateau_risk": round(twin.plateau_risk(curve), 3),
            "connectome_effect": connectome_effect(profile, fly),
        }
        return lab.record("simulate_candidate", {"calorie_target": calorie_target}, out)

    @tool
    def evolve_champion(
        binge_sensitivity: float = 0.6,
        metabolic_adaptation: float = 0.5,
        adherence_base: float = 0.6,
        start_weight_kg: float = 88.0,
        maintenance_kcal: float = 2300.0,
        population_size: int = 180,
        generations: int = 18,
    ) -> dict:
        """Run the fruit-fly swarm and return the evolved champion protocol."""
        profile = lab.profile or UserProfile(
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
            seed=lab.seed,
            calorie_min=safe_calorie_floor(profile.start_weight_kg, profile.maintenance_kcal),
        ).run()
        lab.champion = result.best_fly
        out = {
            "champion": asdict(result.best_fly),
            "fitness": round(result.best_score, 3),
            "adherence": round(twin.adherence(result.best_fly), 3),
            "binge_risk": round(twin.binge_risk(result.best_fly), 3),
        }
        return lab.record("evolve_champion", {"population_size": population_size}, out)

    @tool
    def run_background_loop(horizon_weeks: int = 12) -> dict:
        """Run the 12-week quiet background agent and persist the product report."""
        if not lab.weight_records:
            get_user_context(lab.user_id)
        report = run_business_flow(
            lab.user_id,
            lab.weight_records,
            lab.activity_records,
            population_size=lab.population_size,
            generations=lab.generations,
            seed=lab.seed,
            memory_root=lab.memory_root or Path("runs/memory"),
            reset_memory=True,
            horizon_weeks=int(horizon_weeks),
        )
        lab.report = report
        if report.get("champion"):
            lab.champion = fly_from_dict(report["champion"])
        out = {
            "weeks": len(report.get("flow", [])),
            "surfaced_weeks": report.get("surfaced_weeks", []),
            "decision": report.get("decision"),
            "champion": report.get("champion"),
            "archetype": report.get("calibration", {}).get("archetype"),
        }
        return lab.record("run_background_loop", {"horizon_weeks": horizon_weeks}, out)

    @tool
    def emit_decision(
        current: dict | None = None,
        champion: dict | None = None,
        plateau_detected: bool = False,
    ) -> dict:
        """Turn the current and champion protocols into one surfaced decision."""
        profile = lab.profile or default_profile()
        current_fly = fly_from_dict(current) if current else lab.current or default_current()
        if champion:
            champion_fly = fly_from_dict(champion)
        elif lab.champion:
            champion_fly = lab.champion
        else:
            champion_fly = current_fly
        decision = compose_decision(
            current_fly,
            champion_fly,
            bool(plateau_detected),
            profile,
        )
        out = decision_to_dict(decision)
        if lab.report is not None and lab.report.get("decision") is None:
            lab.report["decision"] = out
        return lab.record("emit_decision", {"plateau_detected": plateau_detected}, out)

    @tool
    def record_feedback(
        user_id: str = "demo",
        accepted: bool = True,
        adherence: float = 0.6,
        weight_delta_kg: float = 0.0,
    ) -> dict:
        """Record a human decision so the next run can learn from it."""
        target = user_id or lab.user_id
        feedback = {
            "user_id": target,
            "accepted": bool(accepted),
            "adherence": round(float(adherence), 3),
            "weight_delta_kg": round(float(weight_delta_kg), 2),
            "source": "strands_tool",
        }
        state = UserMemoryStore(lab.memory_root).append_feedback(target, feedback)
        if lab.report is not None:
            lab.report.setdefault("memory", state)
        return lab.record("record_feedback", {"accepted": accepted}, {"ok": True, "n": len(state.get("feedback", []))})

    return [
        get_user_context,
        detect_plateau,
        simulate_candidate,
        evolve_champion,
        run_background_loop,
        emit_decision,
        record_feedback,
    ]


def _tool_use_events(tool_use_id: str, name: str, payload: dict[str, Any]):
    yield {"messageStart": {"role": "assistant"}}
    yield {
        "contentBlockStart": {
            "contentBlockIndex": 0,
            "start": {"toolUse": {"toolUseId": tool_use_id, "name": name}},
        }
    }
    yield {
        "contentBlockDelta": {
            "contentBlockIndex": 0,
            "delta": {"toolUse": {"input": json.dumps(payload)}},
        }
    }
    yield {"contentBlockStop": {"contentBlockIndex": 0}}
    yield {"messageStop": {"stopReason": "tool_use"}}


class FlowModel:
    """Deterministic Strands model that drives the live demo tool loop."""

    stateful = False

    def __init__(self, session: LabSession) -> None:
        self.session = session
        self._stage = 0

    def update_config(self, **kwargs: Any) -> None:
        return None

    def get_config(self) -> dict:
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("FlowModel does not support structured output")

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
        current = self.session.current or default_current()

        if stage == 0:
            async for event in _agen(
                _tool_use_events(
                    "flow_context",
                    "get_user_context",
                    {"user_id": self.session.user_id},
                )
            ):
                yield event
            return
        if stage == 1:
            async for event in _agen(
                _tool_use_events(
                    "flow_plateau",
                    "detect_plateau",
                    {"weights": self.session.weights or [88.0, 87.9, 87.8], "threshold_kg": 0.2},
                )
            ):
                yield event
            return
        if stage == 2:
            async for event in _agen(
                _tool_use_events("flow_simulate", "simulate_candidate", asdict(current))
            ):
                yield event
            return
        if stage == 3:
            async for event in _agen(
                _tool_use_events(
                    "flow_loop",
                    "run_background_loop",
                    {"horizon_weeks": self.session.horizon_weeks},
                )
            ):
                yield event
            return
        if stage == 4:
            plateau = False
            if self.session.weights:
                plateau, _ = detect_weight_plateau(self.session.weights)
            payload = {
                "current": asdict(current),
                "champion": asdict(self.session.champion or current),
                "plateau_detected": bool(plateau),
            }
            async for event in _agen(
                _tool_use_events("flow_emit", "emit_decision", payload)
            ):
                yield event
            return
        if stage == 5:
            async for event in _agen(
                _tool_use_events(
                    "flow_feedback",
                    "record_feedback",
                    {
                        "user_id": self.session.user_id,
                        "accepted": True,
                        "adherence": 0.6,
                        "weight_delta_kg": 0.0,
                    },
                )
            ):
                yield event
            return

        text = (
            "Strands composed get_user_context → detect_plateau → "
            "simulate_candidate → run_background_loop → emit_decision → "
            "record_feedback, and surfaced one decision."
        )
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}}
        yield {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": text}}}
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "end_turn"}}


async def _agen(events):
    for event in events:
        yield event


class MockModel:
    """Deterministic Strands-compatible model for offline tests."""

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
            async for event in _agen(
                _tool_use_events(
                    "mock_evolve",
                    "evolve_champion",
                    {
                        "binge_sensitivity": 0.6,
                        "metabolic_adaptation": 0.5,
                        "adherence_base": 0.6,
                    },
                )
            ):
                yield event
            return

        if stage == 1:
            async for event in _agen(
                _tool_use_events(
                    "mock_surface",
                    "emit_decision",
                    {
                        "current": asdict(default_current()),
                        "champion": {
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
                        },
                        "plateau_detected": True,
                    },
                )
            ):
                yield event
            return

        text = "The swarm evolved a gentler protocol and surfaced one decision for the user."
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}}
        yield {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": text}}}
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "end_turn"}}


def build_model(provider: str | None = None, session: LabSession | None = None):
    provider = provider or os.getenv("STRANDS_MODEL_PROVIDER", "mock").lower()
    if provider == "flow":
        return FlowModel(session or LabSession())
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


def build_strands_agent(model=None, provider: str | None = None, session: LabSession | None = None):
    """Return a Strands agent wired with the Fly Weight-Lab narrow tools."""
    from strands import Agent

    system_prompt = (
        "You are a weight-loss agent grounded in the real Drosophila mushroom body "
        "connectome. Use the narrow tools to inspect context, detect a plateau, "
        "simulate candidates, run the background loop, emit exactly one decision, "
        "and record human feedback. Stay quiet unless there is a real decision to make."
    )
    return Agent(
        model=model or build_model(provider, session=session),
        tools=build_tools(session),
        system_prompt=system_prompt,
    )


async def run_demo_with_strands(payload: dict[str, Any]) -> dict[str, Any]:
    """Live demo path: Strands composes tools, then the dashboard report is returned."""
    session = LabSession.from_payload(payload)
    if not session.weight_records:
        return {"error": f"no real records found for user_id={session.user_id}"}

    provider = os.getenv("STRANDS_MODEL_PROVIDER", "flow").lower()
    if provider == "mock":
        provider = "flow"
    agent = build_strands_agent(session=session, provider=provider)
    prompt = (
        f"Run the Fly Weight-Lab loop for user {session.user_id}. "
        "Call get_user_context, detect_plateau, simulate_candidate, "
        "run_background_loop, emit_decision, and record_feedback. "
        "Surface exactly one decision."
    )
    result = await agent.invoke_async(prompt)
    if session.report is None:
        session.report = run_business_flow(
            session.user_id,
            session.weight_records,
            session.activity_records,
            population_size=session.population_size,
            generations=session.generations,
            seed=session.seed,
            memory_root=Path("runs/memory"),
            reset_memory=True,
            horizon_weeks=session.horizon_weeks,
        )
    report = session.report
    text = ""
    if hasattr(result, "message") and isinstance(result.message, dict):
        content = result.message.get("content") or []
        if content and isinstance(content[0], dict):
            text = str(content[0].get("text") or "")
    report["strands"] = {
        "provider": provider,
        "stop_reason": getattr(result, "stop_reason", None),
        "message": text,
        "tool_trace": session.tool_trace,
    }
    if session.data_source:
        report["data_source"] = session.data_source
    return report
