# tests/test_event_bus.py
from backend.core.event_bus import EventBus


def test_subscribe_and_publish():
    bus = EventBus()
    received = []
    bus.subscribe("tick", lambda e: received.append(e))
    bus.publish("tick", {"price": 1000.0})
    assert received == [{"price": 1000.0}]


def test_multiple_subscribers():
    bus = EventBus()
    a, b = [], []
    bus.subscribe("tick", lambda e: a.append(e))
    bus.subscribe("tick", lambda e: b.append(e))
    bus.publish("tick", {"price": 1005.0})
    assert len(a) == 1 and len(b) == 1


def test_unsubscribe():
    bus = EventBus()
    received = []
    handler = lambda e: received.append(e)
    bus.subscribe("tick", handler)
    bus.unsubscribe("tick", handler)
    bus.publish("tick", {"price": 1000.0})
    assert received == []


def test_publish_unknown_event_does_nothing():
    bus = EventBus()
    bus.publish("unknown", {})  # 不抛异常
