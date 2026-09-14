from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.business_flow import run_business_flow
from flylab.calibration import load_records


class TestRealDataFlow(unittest.TestCase):
    def test_real_fitbit_weight_file_is_present(self):
        path = Path(__file__).resolve().parents[1] / "data" / "real_users" / "6962181067_weight.csv"
        self.assertTrue(path.exists())
        with path.open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 10)
        self.assertIn("date", rows[0])
        self.assertIn("weight_kg", rows[0])

    def test_real_business_flow_surfaces_and_persists(self):
        root = Path(__file__).resolve().parents[1]
        records = load_records(root / "data" / "real_users" / "6962181067_weight.csv")
        with tempfile.TemporaryDirectory() as tmp:
            report = run_business_flow(
                "real_test_user",
                records,
                population_size=30,
                generations=5,
                seed=7,
                memory_root=tmp,
            )
            self.assertGreaterEqual(len(report["flow"]), 12)
            self.assertTrue(any(entry["decision"] for entry in report["flow"]))
            self.assertGreaterEqual(report["champion"]["calorie_target"], 1200)
            self.assertGreaterEqual(
                report["champion"]["calorie_target"],
                report["calibration"]["calorie_floor"],
            )
            self.assertLess(len(report["surfaced_weeks"]), 12)

    def test_two_preloaded_users_diverge(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            report_a = run_business_flow(
                "6962181067",
                load_records(root / "data" / "real_users" / "6962181067_weight.csv"),
                population_size=40,
                generations=6,
                seed=7,
                memory_root=tmp,
            )
            report_b = run_business_flow(
                "8877689391",
                load_records(root / "data" / "real_users" / "8877689391_weight.csv"),
                population_size=40,
                generations=6,
                seed=7,
                memory_root=tmp,
            )
        self.assertEqual(report_a["calibration"]["archetype"], "binge_prone")
        self.assertEqual(report_b["calibration"]["archetype"], "disciplined")
        champ_a = report_a["champion"]
        champ_b = report_b["champion"]
        diverged = (
            champ_a["late_night_rule"] != champ_b["late_night_rule"]
            or champ_a["refeed_schedule"] != champ_b["refeed_schedule"]
            or abs(champ_a["calorie_target"] - champ_b["calorie_target"]) >= 100
        )
        self.assertTrue(diverged, msg=f"{champ_a} vs {champ_b}")


if __name__ == "__main__":
    unittest.main()
