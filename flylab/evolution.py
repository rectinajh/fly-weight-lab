"""Genetic swarm: spawn, evaluate, breed, mutate, cull, converge."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .fitness import FitnessWeights, evaluate
from .genotype import Fly
from .twin import BehavioralTwin


@dataclass
class EvolutionResult:
    best_fly: Fly
    best_score: float
    history: list  # list of (generation, best_score, mean_score, population_scores)


def farm_from_ranked_scores(scores: list[float], elitism: int = 5) -> str:
    """Encode actual GA survival, not a median split.

    ``2`` = elite kept unchanged, ``1`` = parent pool, ``0`` = culled.
    """
    n = len(scores)
    if n == 0:
        return ""
    elite_cut = min(max(1, elitism), n)
    parent_cut = min(n, max(elite_cut, n // 4))
    return "".join(
        "2" if i < elite_cut else "1" if i < parent_cut else "0" for i in range(n)
    )


class Swarm:
    def __init__(
        self,
        twin: BehavioralTwin,
        population_size: int = 500,
        generations: int = 60,
        elitism: int = 5,
        tournament_k: int = 3,
        seed: int | None = None,
        weights: FitnessWeights | None = None,
        calorie_min: int | None = None,
    ):
        self.twin = twin
        self.population_size = population_size
        self.generations = generations
        self.elitism = elitism
        self.tournament_k = tournament_k
        self.seed = seed
        self.weights = weights
        self.calorie_min = calorie_min

    def run(self) -> EvolutionResult:
        rng = random.Random(self.seed)
        population = [
            Fly.random(rng, calorie_min=self.calorie_min)
            for _ in range(self.population_size)
        ]
        best_fly: Fly | None = None
        best_score = float("-inf")
        history: list = []

        for generation in range(self.generations):
            scored = []
            for fly in population:
                score, _ = evaluate(self.twin, fly, weights=self.weights)
                scored.append((score, fly))
            scored.sort(key=lambda item: item[0], reverse=True)

            top_score, top_fly = scored[0]
            mean_score = sum(score for score, _ in scored) / len(scored)

            if top_score > best_score:
                best_score = top_score
                best_fly = top_fly

            ranked_scores = [score for score, _ in scored]
            history.append(
                (
                    generation,
                    round(best_score, 3),
                    round(mean_score, 3),
                    ranked_scores,
                    farm_from_ranked_scores(ranked_scores, self.elitism),
                )
            )

            elites = [fly for _, fly in scored[: self.elitism]]
            next_population = list(elites)
            while len(next_population) < self.population_size:
                parent_a = self._tournament(scored, rng)
                parent_b = self._tournament(scored, rng)
                child = parent_a.crossover(parent_b, rng).mutate(
                    rng, calorie_min=self.calorie_min
                )
                next_population.append(child)
            population = next_population

        return EvolutionResult(best_fly=best_fly, best_score=best_score, history=history)

    def _tournament(self, scored: list, rng: random.Random, k: int | None = None) -> Fly:
        k = k or self.tournament_k
        contestants = [scored[rng.randrange(len(scored))] for _ in range(k)]
        return max(contestants, key=lambda item: item[0])[1]


def unpack_history_row(row) -> tuple:
    """Accept both legacy 4-tuples and farm-aware 5-tuples."""
    generation, best, mean, scores = row[0], row[1], row[2], row[3]
    farm = row[4] if len(row) > 4 else farm_from_ranked_scores(scores)
    return generation, best, mean, scores, farm
