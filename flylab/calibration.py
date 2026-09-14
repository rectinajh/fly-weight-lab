"""Calibrate the behavioral twin from a user's real log data.

Expected CSV columns:
    date (YYYY-MM-DD)
    weight_kg
    adherence (0-1, optional)

Additional optional columns are accepted and ignored. The output is a
``UserProfile`` whose behavioral parameters are estimated from observed data
rather than hand-set defaults.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np

from .twin import UserProfile


@dataclass
class CalibrationResult:
    profile: UserProfile
    n_records: int
    n_weeks: int
    observed_loss_kg: float
    adherence_mean: float
    adherence_source: str
    weekly_volatility_kg: float


def load_records(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("date") and row.get("weight_kg"):
                rows.append(row)
    return rows


def parse_fitbit_date(value: str) -> date:
    """Parse Fitbit's ``m/d/yyyy`` or ``m/d/yyyy h:mm:ss AM/PM`` timestamps."""
    value = value.strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized Fitbit date: {value!r}")


def load_fitbit_weight_records(
    path: str | Path,
    user_id: str | None = None,
) -> list[dict]:
    """Load and normalize a raw Fitabase ``weightLogInfo_merged.csv`` export.

    Returns one record per row with fields ``date``, ``weight_kg`` and
    ``is_manual_report``. These are real observations, not synthetic logs.
    """
    records: list[dict] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if user_id is not None and row.get("Id") != user_id:
                continue
            raw_date = row.get("Date", "")
            raw_weight = row.get("WeightKg", "")
            if not raw_date or not raw_weight:
                continue
            records.append(
                {
                    "date": parse_fitbit_date(raw_date).isoformat(),
                    "weight_kg": round(float(raw_weight), 4),
                    "is_manual_report": row.get("IsManualReport", "").strip().lower()
                    == "true",
                }
            )
    records.sort(key=lambda row: row["date"])
    return records


def _weekly_averages(records: list[dict]) -> list[float]:
    values = []
    week: list[float] = []
    current_week: tuple[int, int] | None = None
    for row in records:
        parsed = date.fromisoformat(row["date"][:10])
        iso = parsed.isocalendar()
        week_key = (iso.year, iso.week)
        if current_week is None:
            current_week = week_key
        if week_key != current_week:
            if week:
                values.append(float(np.mean(week)))
            week = []
            current_week = week_key
        week.append(float(row["weight_kg"]))
    if week:
        values.append(float(np.mean(week)))
    return values


def fit_profile(records: list[dict], name: str = "calibrated_user") -> CalibrationResult:
    if not records:
        raise ValueError("Cannot calibrate from an empty record set")

    records = sorted(records, key=lambda row: date.fromisoformat(row["date"][:10]))
    weights = [float(row["weight_kg"]) for row in records]
    adherence = [
        float(row["adherence"])
        for row in records
        if row.get("adherence") not in (None, "")
    ]

    weekly = _weekly_averages(records)
    start_weight_kg = float(weights[0])
    observed_loss_kg = start_weight_kg - float(weights[-1])
    adherence_source = "explicit" if adherence else "neutral_prior"
    if adherence:
        adherence_mean = float(np.mean(adherence))
    else:
        # Weight-only logs cannot measure whether a person followed a diet.
        # We therefore keep adherence as an explicitly neutral model prior and
        # let the swarm choose protocols that are robust across plausible
        # adherence levels, rather than pretending a weight log proves
        # behavioral consistency.
        adherence_mean = 0.60

    weekly_deltas = np.diff(weekly)
    weekly_volatility_kg = float(np.std(weekly_deltas)) if len(weekly_deltas) > 1 else 0.4

    # High weight volatility is treated as a binge-prone profile.
    binge_sensitivity = float(np.clip(0.35 + weekly_volatility_kg * 0.8, 0.1, 0.9))

    # A stalled or reversing recent trend implies stronger metabolic adaptation.
    if len(weekly_deltas) >= 2:
        recent_trend = float(np.mean(weekly_deltas[-2:]))
        metabolic_adaptation = float(np.clip(0.25 + max(0.0, -recent_trend) * 1.5, 0.1, 0.8))
    else:
        metabolic_adaptation = 0.25

    # Crude maintenance estimate. A full Mifflin-St Jeor calculation needs
    # age, sex, height and activity, so this remains an editable prior.
    maintenance_kcal = 2300.0 if start_weight_kg >= 80 else 2050.0

    profile = UserProfile(
        name=name,
        start_weight_kg=start_weight_kg,
        adherence_base=float(np.clip(adherence_mean, 0.2, 0.95)),
        binge_sensitivity=binge_sensitivity,
        metabolic_adaptation=metabolic_adaptation,
        water_noise_kg=float(np.clip(weekly_volatility_kg, 0.1, 1.2)),
        maintenance_kcal=maintenance_kcal,
    )

    return CalibrationResult(
        profile=profile,
        n_records=len(records),
        n_weeks=len(weekly),
        observed_loss_kg=round(observed_loss_kg, 2),
        adherence_mean=round(adherence_mean, 3),
        adherence_source=adherence_source,
        weekly_volatility_kg=round(weekly_volatility_kg, 2),
    )


def fit_from_csv(path: str | Path, name: str = "calibrated_user") -> CalibrationResult:
    return fit_profile(load_records(path), name=name)


def fit_from_fitbit_csv(
    path: str | Path,
    user_id: str | None = None,
    name: str = "fitbit_user",
) -> CalibrationResult:
    return fit_profile(load_fitbit_weight_records(path, user_id=user_id), name=name)
