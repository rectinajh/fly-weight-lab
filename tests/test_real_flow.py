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
            self.assertGreaterEqual(len(report["flow"]), 2)
            self.assertTrue(any(entry["decision"] for entry in report["flow"]))
            self.assertEqual(len(report["memory"].get("feedback", [])), 1)


if __name__ == "__main__":
    unittest.main()
