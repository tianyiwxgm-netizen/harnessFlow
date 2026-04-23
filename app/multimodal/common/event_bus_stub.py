"""In-memory stub of L1-09 event bus (IC-09 append_event) for L1-08 unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventBusStub:
    events: list[dict[str, Any]] = field(default_factory=list)

    def append_event(self, event: dict[str, Any]) -> None:
        # shallow-copy to decouple from caller mutation
        self.events.append(dict(event))

    def clear(self) -> None:
        self.events.clear()
