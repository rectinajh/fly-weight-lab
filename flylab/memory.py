"""Simple durable per-user memory for demos and the local agent loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class UserMemoryStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else Path(os.environ.get("FLYLAB_MEMORY_DIR", ".flylab_memory"))
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in user_id)
        return self.root / f"{safe}.json"

    def save(self, user_id: str, data: dict[str, Any]) -> Path:
        path = self._path(user_id)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, user_id: str) -> dict[str, Any]:
        path = self._path(user_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def append_feedback(self, user_id: str, feedback: dict[str, Any]) -> dict[str, Any]:
        state = self.load(user_id)
        history = state.setdefault("feedback", [])
        # Deterministic demo flows can re-run the same checkpoint without
        # creating duplicate rows that look like multiple user actions.
        if not history or history[-1] != feedback:
            history.append(feedback)
        state["feedback"] = state["feedback"][-200:]
        self.save(user_id, state)
        return state

    def list_users(self) -> list[str]:
        return [path.stem for path in self.root.glob("*.json")]
