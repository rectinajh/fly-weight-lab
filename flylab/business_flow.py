"""Reusable real-data business flow for Fly Weight-Lab.

Calibrates from real Fitbit rows, then runs a 12-week background agent on the
fitted twin so the demo can show quiet weeks instead of a 2–3 week stub.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import date
from pathlib import Path

import numpy as np

from .agent_loop import AgentConfig, WeightLossAgent
from .calibration import apply_archetype, archetype_for_user, fit_profile, load_records
from .connectome import load_params
from .genotype import Fly
from .memory import UserMemoryStore
from .safety import evaluate_protocol, has_medical_red_flags, safe_calorie_floor
from .twin import BehavioralTwin

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_preloaded_user(user_id: str) -> tuple[list, list, dict | None]:
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


def weekly_checkpoints(records: list[dict]) -> list[dict]:
    weeks: dict[tuple[int, int], list[tuple[str, float]]] = {}
    for row in records:
        parsed = date.fromisoformat(row["date"][:10])
        key = parsed.isocalendar()[:2]
        weeks.setdefault(key, []).append((row["date"], float(row["weight_kg"])))

    out = []
    for key in sorted(weeks):
        pairs = sorted(weeks[key])
        out.append(
            {
                "week_key": f"{key[0]}-W{key[1]:02d}",
                "date": pairs[-1][0],
                "weight_kg": round(float(np.mean([w for _, w in pairs])), 3),
                "n_days": len(pairs),
            }
        )
    return out


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def build_current(profile, activity_rows: list[dict], archetype: str = "fitted") -> Fly:
    """Starting protocol: slightly aggressive so the agent has something to unwind."""
    steps = [int(row.get("total_steps", "0") or 0) for row in activity_rows]
    avg_steps = int(round(float(np.mean(steps)))) if steps else 7000
    floor = safe_calorie_floor(profile.start_weight_kg, profile.maintenance_kcal)
    if archetype == "binge_prone":
        calorie_target = _clamp(int(round(profile.maintenance_kcal - 450)), floor, 2400)
        meal_window = 8
        late_night = False
        refeed = "none"
        workout_freq = 5
        workout_type = "cardio"
    elif archetype == "disciplined":
        calorie_target = _clamp(int(round(profile.maintenance_kcal - 250)), floor, 2400)
        meal_window = 12
        late_night = False
        refeed = "none"
        workout_freq = 3
        workout_type = "mix"
    else:
        calorie_target = _clamp(int(round(profile.maintenance_kcal - 350)), floor, 2400)
        meal_window = 12
        late_night = False
        refeed = "none"
        workout_freq = 3
        workout_type = "mix"
    return Fly(
        calorie_target=calorie_target,
        protein_pct=0.30,
        carb_pct=0.35,
        meal_window=meal_window,
        meal_count=3,
        late_night_rule=late_night,
        workout_freq=workout_freq,
        workout_type=workout_type,
        sleep_target=7.5,
        refeed_schedule=refeed,
        step_target=_clamp(int(round(avg_steps / 500.0) * 500), 3000, 15000),
    )._normalize(calorie_min=floor)


def format_profile(profile) -> dict:
    return {
        "name": profile.name,
        "start_weight_kg": profile.start_weight_kg,
        "adherence_base": profile.adherence_base,
        "binge_sensitivity": profile.binge_sensitivity,
        "metabolic_adaptation": profile.metabolic_adaptation,
        "water_noise_kg": profile.water_noise_kg,
        "maintenance_kcal": profile.maintenance_kcal,
    }


def connectome_effect(profile, current: Fly) -> dict:
    params = load_params()
    plain = BehavioralTwin(profile)
    grounded = BehavioralTwin(profile, connectome=params)
    return {
        "aggressive_binge_ungrounded": round(plain.binge_risk(current), 2),
        "aggressive_binge_grounded": round(grounded.binge_risk(current), 2),
        "reward_punishment_ratio": round(params.reward_punishment_ratio, 2),
    }


def run_business_flow(
    user_id: str,
    weight_records: list[dict],
    activity_rows: list[dict] | None = None,
    *,
    population_size: int = 350,
    generations: int = 30,
    seed: int = 7,
    memory_root: str | Path | None = None,
    reset_memory: bool = False,
    horizon_weeks: int = 12,
) -> dict:
    """Run the full product loop and return a JSON-serializable report."""
    activity_rows = activity_rows or []
    checkpoints = weekly_checkpoints(weight_records)
    calibration = fit_profile(weight_records, name=f"fitbit_{user_id}")
    archetype = archetype_for_user(user_id, calibration)
    profile = apply_archetype(calibration.profile, archetype)
    floor = safe_calorie_floor(profile.start_weight_kg, profile.maintenance_kcal)

    report: dict = {
        "user_id": user_id,
        "real_weight_summary": {
            "n_records": calibration.n_records,
            "date_range": [
                weight_records[0]["date"],
                weight_records[-1]["date"],
            ],
            "start_weight_kg": profile.start_weight_kg,
            "end_weight_kg": float(weight_records[-1]["weight_kg"]),
            "observed_weight_change_kg": calibration.observed_loss_kg,
            "weekly_checkpoints": checkpoints,
        },
        "activity_summary": {},
        "calibration": {
            "profile": format_profile(profile),
            "adherence_source": calibration.adherence_source,
            "adherence_mean": calibration.adherence_mean,
            "weekly_volatility_kg": calibration.weekly_volatility_kg,
            "archetype": archetype,
            "calorie_floor": floor,
            "maintenance_source": "weight_kg * 30 light-activity prior",
        },
        "safety": {},
        "flow": [],
        "memory": {},
    }

    if activity_rows:
        steps = [int(row.get("total_steps", "0") or 0) for row in activity_rows]
        active_minutes = [
            int(row.get("active_minutes", "0") or 0) for row in activity_rows
        ]
        report["activity_summary"] = {
            "n_days": len(activity_rows),
            "mean_steps": round(float(np.mean(steps)), 0),
            "mean_active_minutes": round(float(np.mean(active_minutes)), 1),
        }

    current = build_current(profile, activity_rows, archetype)
    safety_before = evaluate_protocol(current, profile)
    report["safety"] = {
        "red_flags": has_medical_red_flags(profile),
        "baseline_protocol_safe": safety_before.safe,
        "warnings": safety_before.warnings,
        "calorie_floor": floor,
    }
    report["starting_protocol"] = asdict(current)
    report["connectome_effect"] = connectome_effect(profile, current)

    agent = WeightLossAgent(
        profile,
        current,
        config=AgentConfig(
            population_size=population_size,
            generations=generations,
            seed=seed,
            resurface_weeks=4,
        ),
    )
    memory = UserMemoryStore(memory_root)
    if reset_memory:
        memory.save(user_id, {})

    observed_twin = BehavioralTwin(profile, connectome=load_params())
    projected = observed_twin.simulate(current, horizon_weeks)
    pending: dict | None = None

    for week in range(1, horizon_weeks + 1):
        weight = float(projected[week])
        agent.ingest(weight)
        decision = agent.tick(week)
        observed_delta = round(float(projected[week] - projected[week - 1]), 3)
        entry: dict = {
            "week": week,
            "week_key": f"projected-W{week:02d}",
            "weight_kg": round(weight, 3),
            "n_days": 7,
            "decision": None,
            "observed_delta_from_previous_week_kg": observed_delta,
            "source": "twin_projection",
        }
        if decision is not None:
            entry["decision"] = {
                "headline": decision.headline,
                "action": decision.action,
                "reason": decision.reason,
            }
            pending = {"week": week, "decision": entry["decision"]}
        if pending is not None and week > pending["week"]:
            accepted_proxy = observed_delta <= 0.0
            memory.append_feedback(
                user_id,
                {
                    "decision_week": pending["week"],
                    "decision": pending["decision"],
                    "observed_delta_kg": observed_delta,
                    "accepted_proxy": accepted_proxy,
                    "source": "twin_projection",
                },
            )
            pending = None
        report["flow"].append(entry)

    report["projected_weight"] = [round(float(v), 3) for v in projected]
    report["memory"] = memory.load(user_id)
    report["agent_state"] = agent.state_dict()
    report["champion"] = (
        asdict(agent.last_champion) if agent.last_champion else asdict(agent.current)
    )
    report["evolution"] = agent.evolution_summary()
    report["surfaced_weeks"] = [
        entry["week"] for entry in report["flow"] if entry.get("decision")
    ]
    decisions = [entry["decision"] for entry in report["flow"] if entry.get("decision")]
    report["decision"] = decisions[-1] if decisions else None
    return report
