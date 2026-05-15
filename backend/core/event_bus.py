# backend/core/event_bus.py
from collections import defaultdict
from typing import Callable, Any


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable) -> None:
        self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    def publish(self, event: str, data: Any) -> None:
        for handler in list(self._handlers[event]):
            handler(data)


bus = EventBus()  # 全局单例
