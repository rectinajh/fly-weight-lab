"""Run the Fly Weight-Lab business flow on real Fitbit data.

The flow follows the actual product loop:

1. ingest a real Fitbit weight log
2. calibrate a behavioral twin from observed weight trend and volatility
3. set a safe current protocol anchored to the user's real activity
4. run weekly background ticks
5. surface a decision only when there is a real plateau or protocol change
6. record the observed next-week weight outcome to durable user memory
7. persist the agent state for a later session

This is not a mocked/sample demo. The input rows come from Zenodo
10.5281/zenodo.53894 (CC-BY-4.0), normalized under ``data/real_users``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flylab.business_flow import run_business_flow
from flylab.calibration import load_records


def load_activity(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    rows.sort(key=lambda item: item["date"])
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", default="6962181067")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "real_users")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "runs")
    parser.add_argument("--population-size", type=int, default=350)
    parser.add_argument("--generations", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    weight_path = args.data_dir / f"{args.user_id}_weight.csv"
    activity_path = args.data_dir / f"{args.user_id}_activity.csv"
    if not weight_path.exists():
        raise SystemExit(f"Missing real weight file: {weight_path}")

    records = load_records(weight_path)
    activity_rows = load_activity(activity_path) if activity_path.exists() else []
    report = run_business_flow(
        args.user_id,
        records,
        activity_rows,
        population_size=args.population_size,
        generations=args.generations,
        seed=args.seed,
        memory_root=ROOT / "runs" / "memory",
        reset_memory=True,
    )
    report["data_source"] = {
        "zenodo": "10.5281/zenodo.53894",
        "license": "CC-BY-4.0",
    }

    print("=" * 78)
    print("FLY WEIGHT-LAB · REAL BUSINESS FLOW")
    print("=" * 78)
    print(f"User: {args.user_id}")
    print(
        f"Real data: {report['real_weight_summary']['n_records']} weight rows, "
        f"{report['activity_summary'].get('n_days', 0)} activity days"
    )
    print(
        f"Observed weight: {report['real_weight_summary']['start_weight_kg']} kg -> "
        f"{report['real_weight_summary']['end_weight_kg']:.2f} kg "
        f"({report['real_weight_summary']['observed_weight_change_kg']:+.2f} kg)"
    )
    if report["activity_summary"]:
        print(
            f"Observed activity: {report['activity_summary']['mean_steps']:.0f} steps/day, "
            f"{report['activity_summary']['mean_active_minutes']:.1f} active min/day"
        )
    cal = report["calibration"]
    print(
        f"Calibrated adherence prior: {cal['adherence_mean']} ({cal['adherence_source']})"
    )
    profile = cal["profile"]
    print(
        f"Calibrated binge sensitivity: {profile['binge_sensitivity']:.2f}; "
        f"metabolic adaptation: {profile['metabolic_adaptation']:.2f}"
    )
    print(f"Safety red flags: {report['safety']['red_flags']}")
    print(f"Baseline protocol safe: {report['safety']['baseline_protocol_safe']}")
    print("\nWeekly background ticks:\n")

    for entry in report["flow"]:
        week = entry["week"]
        if entry["decision"]:
            decision = entry["decision"]
            print(f"week {week:>2}  SURFACED  {decision['headline']}")
            print(f"            action: {decision['action']}")
            print(f"            reason: {decision['reason']}")
        else:
            print(f"week {week:>2}  quiet")

    state_path = args.out_dir / f"{args.user_id}_agent_state.json"
    report_path = args.out_dir / f"{args.user_id}_business_flow.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(report["agent_state"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report.pop("agent_state", None)
    report["agent_state_path"] = str(state_path)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 78)
    print(f"Agent state persisted: {state_path}")
    print(f"Business-flow report persisted: {report_path}")
    print(f"Feedback records: {len(report['memory'].get('feedback', []))}")


if __name__ == "__main__":
    main()
