"""Clock adapters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class DeterministicClock:
    """Monotonic test clock starting at a fixed instant."""

    def __init__(self, start: datetime | None = None, step_seconds: float = 1.0) -> None:
        self._current = start or datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
        self._step = timedelta(seconds=step_seconds)

    def now(self) -> datetime:
        value = self._current
        self._current = self._current + self._step
        return value

    def peek(self) -> datetime:
        return self._current
