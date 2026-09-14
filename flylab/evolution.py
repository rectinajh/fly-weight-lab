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
    ):
        self.twin = twin
        self.population_size = population_size
        self.generations = generations
        self.elitism = elitism
        self.tournament_k = tournament_k
        self.seed = seed
        self.weights = weights

    def run(self) -> EvolutionResult:
        rng = random.Random(self.seed)
        population = [Fly.random(rng) for _ in range(self.population_size)]
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

            history.append(
                (
                    generation,
                    round(best_score, 3),
                    round(mean_score, 3),
                    [score for score, _ in scored],
                )
            )

            elites = [fly for _, fly in scored[: self.elitism]]
            next_population = list(elites)
            while len(next_population) < self.population_size:
                parent_a = self._tournament(scored, rng)
                parent_b = self._tournament(scored, rng)
                child = parent_a.crossover(parent_b, rng).mutate(rng)
                next_population.append(child)
            population = next_population

        return EvolutionResult(best_fly=best_fly, best_score=best_score, history=history)

    def _tournament(self, scored: list, rng: random.Random, k: int | None = None) -> Fly:
        k = k or self.tournament_k
        contestants = [scored[rng.randrange(len(scored))] for _ in range(k)]
        return max(contestants, key=lambda item: item[0])[1]
