"""Structured JSON telemetry for the local agent loop.

This is intentionally lightweight. For a real deployment it can be replaced by
OpenTelemetry / CloudWatch spans.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("flylab.telemetry")


def emit(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))


@contextmanager
def timed(event: str, **fields: Any):
    start = time.perf_counter()
    try:
        yield
    finally:
        emit(
            event,
            duration_ms=round((time.perf_counter() - start) * 1000, 1),
            **fields,
        )
