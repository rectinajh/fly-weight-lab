"""Background agent loop.

Turns the batch simulation into a background agent that matches the hackathon
theme: it runs quietly, and only surfaces ONE decision when something
materially changes (a newly detected plateau, or a better champion protocol).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .agent import Decision, surface_decision
from .connectome import ConnectomeParams, load_params
from .evolution import Swarm
from .genotype import Fly
from .safety import evaluate_protocol, safe_champion
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
        self.last_escalation_surfaced = False
        self.last_champion: Fly | None = None
        self.last_evolution: list | None = None
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

    def _run_swarm(self) -> tuple[Fly, float, list]:
        result = Swarm(
            self.twin,
            population_size=self.config.population_size,
            generations=self.config.generations,
            seed=self.config.seed,
        ).run()
        self.last_evolution = result.history
        return result.best_fly, result.best_score, result.history

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

        champion, _, _ = self._run_swarm()
        safety = evaluate_protocol(champion, self.profile)
        if not safety.safe:
            champion = safe_champion(champion, self.profile)
            safety = evaluate_protocol(champion, self.profile)
        self.last_champion = champion
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
        if due and safety.escalation and not self.last_escalation_surfaced:
            decision = Decision(
                headline="Escalate to a clinician first",
                action="Pause automatic changes and share your real weight trajectory with a doctor or dietitian",
                reason="Your inputs triggered a safety red flag. This agent is a behavioral sentinel, not a diagnosis or prescription.",
            )
            self.last_escalation_surfaced = True
            self.last_surface_week = week
            surfaced = True
        elif due and (new_plateau or changed):
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
                "safety": safety.as_dict(),
            }
        )
        return decision

    def evolution_summary(self) -> dict:
        """Return a compact, frontend-friendly view of the last swarm run."""
        if not self.last_evolution:
            return {"generations": []}

        generations = []
        for generation, best, mean, scores in self.last_evolution:
            ordered = sorted(scores)
            median = ordered[len(ordered) // 2]
            farm = "".join("1" if score >= median else "0" for score in scores)
            generations.append(
                {
                    "generation": generation,
                    "best": best,
                    "mean": mean,
                    "farm": farm,
                }
            )
        return {
            "population_size": self.config.population_size,
            "generation_count": self.config.generations,
            "generations": generations,
        }

    def state_dict(self) -> dict:
        """Return a JSON-serializable snapshot of the agent's live state."""
        return {
            "profile": asdict(self.profile),
            "current": asdict(self.current),
            "config": asdict(self.config),
            "weights": self.weights,
            "prev_plateau": self.prev_plateau,
            "last_surface_week": self.last_surface_week,
            "last_fingerprint": (
                list(self.last_fingerprint) if self.last_fingerprint is not None else None
            ),
            "last_escalation_surfaced": self.last_escalation_surfaced,
            "history": self.history,
        }

    def save_state(self, path: str | Path) -> Path:
        """Persist the agent state to a JSON file and return its path."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.state_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @classmethod
    def from_state(
        cls,
        state: dict,
        connectome: ConnectomeParams | None = None,
    ) -> "WeightLossAgent":
        """Restore an agent from a snapshot without rerunning the swarm."""
        agent = cls(
            profile=UserProfile(**state["profile"]),
            current=Fly(**state["current"]),
            config=AgentConfig(**state["config"]),
            connectome=connectome if connectome is not None else load_params(),
        )
        agent.weights = list(state.get("weights", [agent.weights[0]]))
        agent.prev_plateau = bool(state.get("prev_plateau", False))
        agent.last_surface_week = state.get("last_surface_week")
        fingerprint = state.get("last_fingerprint")
        agent.last_fingerprint = tuple(fingerprint) if fingerprint is not None else None
        agent.last_escalation_surfaced = bool(state.get("last_escalation_surfaced", False))
        agent.history = list(state.get("history", []))
        return agent

    @classmethod
    def load_state(
        cls,
        path: str | Path,
        connectome: ConnectomeParams | None = None,
    ) -> "WeightLossAgent":
        """Load a persisted agent state from a JSON file."""
        raw = Path(path).read_text(encoding="utf-8")
        return cls.from_state(json.loads(raw), connectome=connectome)
