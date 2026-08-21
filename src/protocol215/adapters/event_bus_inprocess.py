"""In-process event bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from protocol215.domain.models import DomainEvent

Handler = Callable[[DomainEvent], None]


class InProcessEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self.published: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        for handler in list(self._handlers.get(event.event_type, [])):
            handler(event)
        for handler in list(self._handlers.get("*", [])):
            handler(event)

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._handlers[event_type].append(handler)
