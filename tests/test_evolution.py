from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flylab.evolution import Swarm
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


if __name__ == "__main__":
    unittest.main()
