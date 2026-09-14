"""Run the offline evaluation suite and print a compact scorecard."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flylab.evaluation import (
    champion_vs_aggressive_baseline,
    compare_two_users,
    evaluate_plateau_detection,
)


def main() -> None:
    plateau = evaluate_plateau_detection().as_dict()
    users = compare_two_users()
    baseline = champion_vs_aggressive_baseline()
    report = {
        "plateau_detection": plateau,
        "two_users": users,
        "baseline_comparison": baseline,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
