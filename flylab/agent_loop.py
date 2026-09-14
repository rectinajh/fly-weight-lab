"""Background agent loop.

Turns the batch simulation into a background agent that matches the hackathon
theme: it runs quietly, and only surfaces ONE decision when something
materially changes (a newly detected plateau, or a better champion protocol).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Decision, surface_decision
from .connectome import ConnectomeParams, load_params
from .evolution import Swarm
from .genotype import Fly
from .twin import BehavioralTwin, UserProfile


@dataclass
class AgentConfig:
    plateau_window: int = 3
    plateau_threshold_kg: float = 0.2
    resurface_weeks: int = 3
    population_size: int = 400
    generations: int = 40
    seed: int = 7
    adapt_on_plateau: float = 0.05


class WeightLossAgent:
    """A background agent that runs the swarm and surfaces decisions sparingly."""

    def __init__(
        self,
        profile: UserProfile,
        current: Fly,
        config: AgentConfig | None = None,
        connectome: ConnectomeParams | None = None,
    ):
        self.profile = profile
        self.config = config or AgentConfig()
        self.connectome = connectome if connectome is not None else load_params()
        self.twin = BehavioralTwin(profile, connectome=self.connectome)
        self.current = current
        self.weights: list[float] = [profile.start_weight_kg]
        self.prev_plateau = False
        self.last_surface_week: int | None = None
        self.last_fingerprint: tuple | None = None
        self.history: list[dict] = []

    def ingest(self, weight_kg: float) -> None:
        self.weights.append(weight_kg)

    def _plateau(self) -> bool:
        if len(self.weights) <= self.config.plateau_window:
            return False
        delta = self.weights[-1] - self.weights[-(self.config.plateau_window + 1)]
        return abs(delta) < self.config.plateau_threshold_kg

    @staticmethod
    def _fingerprint(fly: Fly) -> tuple:
        return (
            fly.calorie_target,
            fly.late_night_rule,
            fly.refeed_schedule,
            fly.meal_window,
            round(fly.sleep_target, 1),
        )

    def _run_swarm(self) -> tuple[Fly, float]:
        result = Swarm(
            self.twin,
            population_size=self.config.population_size,
            generations=self.config.generations,
            seed=self.config.seed,
        ).run()
        return result.best_fly, result.best_score

    def tick(self, week: int) -> Decision | None:
        """Run one background tick. Returns a Decision only if worth surfacing."""
        plateau = self._plateau()

        # Learn from a newly detected plateau: adapt the twin so a re-run finds
        # a genuinely new lever instead of re-surfacing the same advice.
        if plateau and not self.prev_plateau:
            self.twin.profile.metabolic_adaptation = min(
                0.8,
                self.twin.profile.metabolic_adaptation + self.config.adapt_on_plateau,
            )

        champion, _ = self._run_swarm()
        champion_fp = self._fingerprint(champion)
        current_fp = self._fingerprint(self.current)

        new_plateau = plateau and not self.prev_plateau
        changed = champion_fp != current_fp
        due = (
            self.last_surface_week is None
            or (week - self.last_surface_week) >= self.config.resurface_weeks
        )

        surfaced = False
        decision: Decision | None = None
        if due and (new_plateau or changed):
            decision = surface_decision(self.current, champion, plateau, self.profile)
            self.current = champion
            self.last_surface_week = week
            self.last_fingerprint = champion_fp
            surfaced = True

        self.prev_plateau = plateau
        self.history.append(
            {
                "week": week,
                "plateau": plateau,
                "surfaced": surfaced,
                "action": decision.action if decision else None,
            }
        )
        return decision
