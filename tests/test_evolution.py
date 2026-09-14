from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.evolution import Swarm
from flylab.connectome import load_params
from flylab.agent_loop import WeightLossAgent
from flylab.genotype import CALORIE_FLOOR, Fly
from flylab.twin import BehavioralTwin, UserProfile


class TestGenotype(unittest.TestCase):
    def test_random_within_constraints(self):
        fly = Fly.random()
        self.assertGreaterEqual(fly.calorie_target, CALORIE_FLOOR)
        self.assertLessEqual(fly.protein_pct + fly.carb_pct, 0.85 + 1e-6)
        self.assertGreaterEqual(fly.fat_pct, 0.0)
        self.assertTrue(6.5 <= fly.sleep_target <= 9.5)

    def test_mutate_and_crossover_stay_valid(self):
        base = Fly.random()
        for _ in range(200):
            mutated = base.mutate()
            self.assertGreaterEqual(mutated.calorie_target, CALORIE_FLOOR)
            self.assertTrue(6.5 <= mutated.sleep_target <= 9.5)
        crossed = base.crossover(Fly.random())
        self.assertGreaterEqual(crossed.calorie_target, CALORIE_FLOOR)


class TestEvolution(unittest.TestCase):
    def test_swarm_improves_fitness(self):
        twin = BehavioralTwin(
            UserProfile(
                name="test",
                adherence_base=0.6,
                binge_sensitivity=0.5,
                metabolic_adaptation=0.4,
            )
        )
        result = Swarm(twin, population_size=200, generations=20, seed=1).run()
        first_best = result.history[0][1]
        last_best = result.history[-1][1]
        self.assertGreater(last_best, first_best)


class TestConnectome(unittest.TestCase):
    def test_real_params_load(self):
        params = load_params()
        self.assertEqual(params.n_kenyon, 4064)
        self.assertEqual(params.n_mbon, 97)
        self.assertGreater(params.reward_punishment_ratio, 1.0)
        self.assertLessEqual(params.context_recurrence_ratio, 1.0)


class TestAgentLoop(unittest.TestCase):
    def test_surfaces_on_plateau_and_quiet_otherwise(self):
        profile = UserProfile(
            name="test",
            start_weight_kg=88.0,
            adherence_base=0.6,
            binge_sensitivity=0.6,
            metabolic_adaptation=0.5,
            maintenance_kcal=2300.0,
        )
        current = Fly(
            calorie_target=1500,
            protein_pct=0.40,
            carb_pct=0.25,
            meal_window=8,
            meal_count=3,
            late_night_rule=False,
            workout_freq=5,
            workout_type="cardio",
            sleep_target=7.0,
            refeed_schedule="none",
            step_target=10000,
        )
        agent = WeightLossAgent(profile, current, connectome=load_params())
        curve = BehavioralTwin(profile, connectome=load_params()).simulate(current, 12)

        surfaced_weeks = []
        for week in range(1, 13):
            agent.ingest(float(curve[week]))
            decision = agent.tick(week)
            if decision is not None:
                surfaced_weeks.append(week)

        self.assertGreaterEqual(len(surfaced_weeks), 1)
        self.assertLess(len(surfaced_weeks), 12)


if __name__ == "__main__":
    unittest.main()
