"""Fit a behavioral twin from a CSV export and print the resulting profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flylab.calibration import fit_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate Fly Weight-Lab twin from CSV")
    parser.add_argument("csv_path")
    parser.add_argument("--name", default="calibrated_user")
    args = parser.parse_args()

    result = fit_from_csv(args.csv_path, name=args.name)
    print(
        json.dumps(
            {
                "profile": result.profile.__dict__,
                "n_records": result.n_records,
                "n_weeks": result.n_weeks,
                "observed_loss_kg": result.observed_loss_kg,
                "adherence_mean": result.adherence_mean,
                "adherence_source": result.adherence_source,
                "weekly_volatility_kg": result.weekly_volatility_kg,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
