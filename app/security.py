"""Small, process-local API-key and rate-limit helpers for local deployments."""
from __future__ import annotations
import hmac
import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque


class FixedWindowRateLimiter:
    """In-memory fixed-window limiter. For multi-worker production, use a shared store."""
    def __init__(self):
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_id: str, limit: int, window_seconds: int = 60, now: float | None = None) -> tuple[bool, int]:
        now = time.monotonic() if now is None else now
        cutoff = now - window_seconds
        with self._lock:
            hits = self._hits[client_id]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                return False, retry_after
            hits.append(now)
            return True, 0

    def clear(self):
        with self._lock:
            self._hits.clear()


def configured_api_key() -> str | None:
    key = os.getenv("QRAM_API_KEY", "").strip()
    return key or None


def valid_api_key(candidate: str | None, expected: str) -> bool:
    if not candidate:
        return False
    try:
        return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))
    except (AttributeError, UnicodeError):
        return False


def rate_limit_value() -> int:
    try:
        return max(1, min(int(os.getenv("QRAM_RATE_LIMIT", "120")), 10000))
    except ValueError:
        return 120
