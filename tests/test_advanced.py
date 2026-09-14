from __future__ import annotations

import asyncio
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.calibration import fit_profile
from flylab.evaluation import evaluate_plateau_detection
from flylab.genotype import Fly
from flylab.memory import UserMemoryStore
from flylab.safety import evaluate_protocol, safe_calorie_floor, safe_champion
from flylab.strands_agent import build_model, build_strands_agent, build_tools
from flylab.twin import UserProfile


class TestCalibration(unittest.TestCase):
    def test_fit_profile_from_records(self):
        records = [
            {"date": "2026-01-01", "weight_kg": "88.0", "adherence": "0.6"},
            {"date": "2026-01-08", "weight_kg": "87.4", "adherence": "0.65"},
            {"date": "2026-01-15", "weight_kg": "87.2", "adherence": "0.55"},
            {"date": "2026-01-22", "weight_kg": "87.1", "adherence": "0.5"},
        ]
        result = fit_profile(records)
        self.assertEqual(result.profile.start_weight_kg, 88.0)
        self.assertGreater(result.profile.binge_sensitivity, 0.0)
        self.assertGreaterEqual(result.profile.metabolic_adaptation, 0.1)


class TestSafety(unittest.TestCase):
    def test_unsafe_protocol_is_repaired(self):
        profile = UserProfile(start_weight_kg=88.0)
        unsafe = Fly(
            calorie_target=900,
            protein_pct=0.10,
            carb_pct=0.20,
            meal_window=6,
            meal_count=2,
            late_night_rule=False,
            workout_freq=3,
            workout_type="mix",
            sleep_target=5.0,
            refeed_schedule="none",
            step_target=4000,
        )
        report = evaluate_protocol(unsafe, profile)
        self.assertFalse(report.safe)
        repaired = safe_champion(unsafe, profile)
        self.assertTrue(evaluate_protocol(repaired, profile).safe)
        self.assertGreaterEqual(
            repaired.calorie_target, safe_calorie_floor(88.0, profile.maintenance_kcal)
        )
        self.assertGreater(safe_calorie_floor(61.5, 1845.0), 1329)


class TestEvaluation(unittest.TestCase):
    def test_plateau_metrics_are_bounded(self):
        metrics = evaluate_plateau_detection(samples=20)
        self.assertGreaterEqual(metrics.precision, 0.0)
        self.assertLessEqual(metrics.precision, 1.0)
        self.assertGreater(metrics.accuracy, 0.5)


class TestMemory(unittest.TestCase):
    def test_feedback_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = UserMemoryStore(tmp)
            store.append_feedback("alice", {"accepted": True, "adherence": 0.8})
            state = store.load("alice")
            self.assertEqual(state["feedback"][-1]["accepted"], True)


class TestStrandsLocalAgent(unittest.TestCase):
    def test_tools_are_narrow(self):
        names = [getattr(tool, "__name__", None) for tool in build_tools()]
        self.assertIn("evolve_champion", names)
        self.assertIn("emit_decision", names)
        self.assertIn("run_background_loop", names)
        self.assertGreaterEqual(len(names), 6)

    def test_mock_model_agent_completes(self):
        self.assertIsNotNone(build_model("mock"))
        agent = build_strands_agent(provider="mock")
        result = asyncio.run(
            agent.invoke_async("Detect a plateau and surface one decision.")
        )
        self.assertEqual(result.stop_reason, "end_turn")
        self.assertTrue(result.message["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
