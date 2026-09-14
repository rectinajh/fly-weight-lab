"""Real Drosophila mushroom-body connectome grounding (Janelia MaleCNS v1.0).

The mushroom body is the fruit fly's canonical reward-learning and habit
circuit. It is wired from three cell classes:

  - Kenyon cells (context / input)
  - dopaminergic neurons (reward vs punishment: PAM vs PPL)
  - MBONs (behavioral output / decision)

We extract real structural features from the public MaleCNS dataset and use
them as a principled prior for the behavioral twin, instead of hand-tuned
constants.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class ConnectomeParams:
    source: str
    n_kenyon: int
    n_dan: int
    n_mbon: int
    kc_mbon_convergence: float
    dan_mbon_convergence: float
    reward_punishment_ratio: float
    context_recurrence_ratio: float


def load_summary(path: str | Path | None = None) -> dict:
    target = Path(path) if path else DATA_DIR / "mb_summary.json"
    return json.loads(target.read_text())


def params_from_summary(summary: dict) -> ConnectomeParams:
    families = summary["dan_family_to_mbon_weight"]
    pam = float(families.get("PAM", 0.0))
    ppl = float(families.get("PPL", 1.0))

    class_matrix = summary["class_matrix_weight"]
    total = float(summary["mb_synaptic_weight"])
    kc_kc = float(class_matrix.get("Kenyon_Cell->Kenyon_Cell", 0.0))

    return ConnectomeParams(
        source=summary["source"],
        n_kenyon=int(summary["neurons"]["Kenyon_Cell"]),
        n_dan=int(summary["neurons"]["DAN"]),
        n_mbon=int(summary["neurons"]["MBON"]),
        kc_mbon_convergence=float(summary["kc_to_mbon"]["mean_kc_per_mbon"]),
        dan_mbon_convergence=float(summary["dan_to_mbon"]["mean_dan_per_mbon"]),
        reward_punishment_ratio=pam / ppl if ppl > 0 else 1.0,
        context_recurrence_ratio=kc_kc / total if total > 0 else 0.0,
    )


def load_params(path: str | Path | None = None) -> ConnectomeParams:
    return params_from_summary(load_summary(path))
