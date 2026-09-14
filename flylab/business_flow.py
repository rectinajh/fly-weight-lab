"""Reusable real-data business flow for Fly Weight-Lab.

The CLI and the local HTTP backend both use this module, so the product loop
is implemented once and exercised through the same code path in every demo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np

from .agent_loop import AgentConfig, WeightLossAgent
from .calibration import fit_profile
from .genotype import Fly
from .memory import UserMemoryStore
from .safety import evaluate_protocol, has_medical_red_flags, safe_calorie_floor


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


def build_current(profile, activity_rows: list[dict]) -> Fly:
    steps = [int(row.get("total_steps", "0") or 0) for row in activity_rows]
    avg_steps = int(round(float(np.mean(steps)))) if steps else 7000
    calorie_target = _clamp(
        int(round(profile.maintenance_kcal - 350)),
        safe_calorie_floor(profile.start_weight_kg),
        2400,
    )
    return Fly(
        calorie_target=calorie_target,
        protein_pct=0.30,
        carb_pct=0.35,
        meal_window=12,
        meal_count=3,
        late_night_rule=False,
        workout_freq=3,
        workout_type="mix",
        sleep_target=7.5,
        refeed_schedule="none",
        step_target=_clamp(int(round(avg_steps / 500.0) * 500), 3000, 15000),
    )._normalize()


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
) -> dict:
    """Run the full product loop and return a JSON-serializable report."""
    activity_rows = activity_rows or []
    checkpoints = weekly_checkpoints(weight_records)
    calibration = fit_profile(weight_records, name=f"fitbit_{user_id}")
    profile = calibration.profile

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

    current = build_current(profile, activity_rows)
    safety_before = evaluate_protocol(current, profile)
    report["safety"] = {
        "red_flags": has_medical_red_flags(profile),
        "baseline_protocol_safe": safety_before.safe,
        "warnings": safety_before.warnings,
    }

    agent = WeightLossAgent(
        profile,
        current,
        config=AgentConfig(
            population_size=population_size,
            generations=generations,
            seed=seed,
            resurface_weeks=2,
        ),
    )
    memory = UserMemoryStore(memory_root)
    if reset_memory:
        memory.save(user_id, {})
    pending: dict | None = None

    for week, checkpoint in enumerate(checkpoints, start=1):
        weight = checkpoint["weight_kg"]
        agent.ingest(weight)
        decision = agent.tick(week)
        observed_delta = 0.0
        if week > 1:
            observed_delta = round(
                checkpoints[week - 1]["weight_kg"]
                - checkpoints[week - 2]["weight_kg"],
                3,
            )

        entry: dict = {
            "week": week,
            "week_key": checkpoint["week_key"],
            "weight_kg": weight,
            "n_days": checkpoint["n_days"],
            "decision": None,
            "observed_delta_from_previous_week_kg": observed_delta,
        }

        if decision is not None:
            entry["decision"] = {
                "headline": decision.headline,
                "action": decision.action,
                "reason": decision.reason,
            }
            pending = {
                "week": week,
                "decision": entry["decision"],
            }
        else:
            entry["decision"] = None

        if pending is not None and week > pending["week"]:
            accepted_proxy = observed_delta <= 0.0
            memory.append_feedback(
                user_id,
                {
                    "decision_week": pending["week"],
                    "decision": pending["decision"],
                    "observed_delta_kg": observed_delta,
                    "accepted_proxy": accepted_proxy,
                    "source": "real_weight_checkpoint",
                },
            )
            pending = None

        report["flow"].append(entry)

    report["memory"] = memory.load(user_id)
    report["agent_state"] = agent.state_dict()
    return report
