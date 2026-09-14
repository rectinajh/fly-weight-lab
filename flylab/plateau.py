"""Plateau detection on a simulated or real weight curve."""

from __future__ import annotations

import numpy as np


def detect_plateau(
    weight_curve: np.ndarray,
    window: int = 3,
    threshold_kg: float = 0.2,
) -> tuple[bool, float]:
    """Return (is_plateau, recent_change_kg)."""
    if len(weight_curve) <= window:
        return False, 0.0
    recent_change = float(weight_curve[-1] - weight_curve[-(window + 1)])
    return abs(recent_change) < threshold_kg, recent_change
