"""
Unit tests for EventBus — v20.0 Phase 2 (Agent Hive Mind).

Tests subscription/publish flow, thread safety, error isolation, and edge cases.
"""

import threading
import time
from unittest.mock import Mock

import pytest

from utils.event_bus import Event, EventBus, Subscription


@pytest.fixture
def event_bus():
    """Create a fresh EventBus instance for each test."""
    bus = EventBus()
    bus.clear()
    bus._reinit_executor()  # Reinitialize executor if it was shut down by previous test
    yield bus
    # Don't shutdown - just clear subscriptions (singleton persists across tests)


def test_event_dataclass_validation():
    """Test Event dataclass validates inputs."""
    # Valid event
    event = Event(topic="test.topic", data={"key": "value"})
    assert event.topic == "test.topic"
    assert event.data == {"key": "value"}
    assert event.source is None

    # Invalid: empty topic
    with pytest.raises(ValueError, match="topic cannot be empty"):
        Event(topic="", data={})

    # Invalid: data is not a dict
    with pytest.raises(TypeError, match="data must be dict"):
        Event(topic="test", data="not a dict")


def test_singleton_pattern():
    """Test EventBus is a singleton."""
    bus1 = EventBus()
    bus2 = EventBus()
    assert bus1 is bus2


def test_subscribe_and_publish_basic(event_bus):
    """Test basic subscription and publish flow."""
    received_events = []

    def callback(event: Event):
        received_events.append(event)

    event_bus.subscribe("test.topic", callback)
    event_bus.publish("test.topic", {"message": "hello"})

    # Wait for async execution
    time.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].topic == "test.topic"
    assert received_events[0].data == {"message": "hello"}


def test_multiple_subscribers_same_topic(event_bus):
    """Test multiple subscribers to the same topic."""
    counter = {"count": 0}
    lock = threading.Lock()

    def callback1(event: Event):
        with lock:
            counter["count"] += 1

    def callback2(event: Event):
        with lock:
            counter["count"] += 10

    event_bus.subscribe("test.topic", callback1, subscriber_id="sub1")
    event_bus.subscribe("test.topic", callback2, subscriber_id="sub2")
    event_bus.publish("test.topic", {"value": 42})

    time.sleep(0.1)

    assert counter["count"] == 11  # Both callbacks invoked


def test_multiple_topics(event_bus):
    """Test publishing to different topics with different subscribers."""
    topic1_events = []
    topic2_events = []

    def callback1(event: Event):
        topic1_events.append(event)

    def callback2(event: Event):
        topic2_events.append(event)

    event_bus.subscribe("topic.one", callback1)
    event_bus.subscribe("topic.two", callback2)

    event_bus.publish("topic.one", {"data": "one"})
    event_bus.publish("topic.two", {"data": "two"})

    time.sleep(0.1)

    assert len(topic1_events) == 1
    assert len(topic2_events) == 1
    assert topic1_events[0].data["data"] == "one"
    assert topic2_events[0].data["data"] == "two"


def test_no_subscribers(event_bus):
    """Test publishing to a topic with no subscribers does not crash."""
    # Should not raise
    event_bus.publish("nonexistent.topic", {"data": "test"})


def test_subscriber_error_isolation(event_bus):
    """Test that one failing subscriber does not prevent others from executing."""
    success_calls = []

    def failing_callback(event: Event):
        raise RuntimeError("Intentional test failure")

    def success_callback(event: Event):
        success_calls.append(event)

    event_bus.subscribe("test.topic", failing_callback, subscriber_id="failer")
    event_bus.subscribe("test.topic", success_callback, subscriber_id="succeeder")

    event_bus.publish("test.topic", {"data": "test"})

    time.sleep(0.2)

    # Success callback should have executed despite failure of first
    assert len(success_calls) == 1


def test_thread_safety_concurrent_publishes(event_bus):
    """Test concurrent publishes are thread-safe."""
    received_count = {"count": 0}
    lock = threading.Lock()

    def callback(event: Event):
        with lock:
            received_count["count"] += 1

    event_bus.subscribe("test.topic", callback)

    def publish_many():
        for _ in range(50):
            event_bus.publish("test.topic", {"data": "test"})

    threads = [threading.Thread(target=publish_many) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(0.5)

    # 5 threads × 50 publishes = 250 events
    assert received_count["count"] == 250


def test_thread_safety_concurrent_subscriptions(event_bus):
    """Test concurrent subscriptions are thread-safe."""
    callbacks = [Mock() for _ in range(20)]

    def subscribe_one(callback):
        event_bus.subscribe("test.topic", callback)

    threads = [threading.Thread(target=subscribe_one, args=(cb,)) for cb in callbacks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert event_bus.get_subscriber_count("test.topic") == 20


def test_unsubscribe(event_bus):
    """Test unsubscribing removes the callback."""
    received_events = []

    def callback(event: Event):
        received_events.append(event)

    event_bus.subscribe("test.topic", callback)
    event_bus.publish("test.topic", {"data": "first"})
    time.sleep(0.1)

    assert len(received_events) == 1

    # Unsubscribe
    removed = event_bus.unsubscribe("test.topic", callback)
    assert removed is True

    event_bus.publish("test.topic", {"data": "second"})
    time.sleep(0.1)

    # Should still be 1 (no new event received)
    assert len(received_events) == 1


def test_unsubscribe_with_subscriber_id(event_bus):
    """Test unsubscribing with subscriber_id removes only that subscription."""
    counter = {"count": 0}
    lock = threading.Lock()

    def callback1(event: Event):
        with lock:
            counter["count"] += 1

    def callback2(event: Event):
        with lock:
            counter["count"] += 10

    event_bus.subscribe("test.topic", callback1, subscriber_id="sub1")
    event_bus.subscribe("test.topic", callback2, subscriber_id="sub2")

    # Unsubscribe only sub1
    removed = event_bus.unsubscribe("test.topic", callback1, subscriber_id="sub1")
    assert removed is True

    event_bus.publish("test.topic", {"data": "test"})
    time.sleep(0.1)

    # Only callback2 should execute (adds 10)
    assert counter["count"] == 10


def test_get_subscriber_count(event_bus):
    """Test getting subscriber count for a topic."""
    assert event_bus.get_subscriber_count("test.topic") == 0

    event_bus.subscribe("test.topic", lambda e: None)
    assert event_bus.get_subscriber_count("test.topic") == 1

    event_bus.subscribe("test.topic", lambda e: None)
    assert event_bus.get_subscriber_count("test.topic") == 2


def test_clear(event_bus):
    """Test clearing all subscriptions."""
    event_bus.subscribe("topic1", lambda e: None)
    event_bus.subscribe("topic2", lambda e: None)
    event_bus.subscribe("topic2", lambda e: None)

    assert event_bus.get_subscriber_count("topic1") == 1
    assert event_bus.get_subscriber_count("topic2") == 2

    event_bus.clear()

    assert event_bus.get_subscriber_count("topic1") == 0
    assert event_bus.get_subscriber_count("topic2") == 0


def test_subscribe_validation(event_bus):
    """Test subscribe validates inputs."""
    # Invalid: empty topic
    with pytest.raises(ValueError, match="Topic cannot be empty"):
        event_bus.subscribe("", lambda e: None)

    # Invalid: callback not callable
    with pytest.raises(TypeError, match="Callback must be callable"):
        event_bus.subscribe("test.topic", "not callable")


def test_publish_validation(event_bus):
    """Test publish validates inputs."""
    # Invalid: empty topic
    with pytest.raises(ValueError, match="topic cannot be empty"):
        event_bus.publish("", {})

    # Invalid: data not a dict
    with pytest.raises(TypeError, match="data must be dict"):
        event_bus.publish("test.topic", "not a dict")


def test_event_source_tracking(event_bus):
    """Test event source is tracked correctly."""
    received_events = []

    def callback(event: Event):
        received_events.append(event)

    event_bus.subscribe("test.topic", callback)
    event_bus.publish("test.topic", {"data": "test"}, source="agent.battery")

    time.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].source == "agent.battery"


def test_standard_topics_format(event_bus):
    """Test standard topic formats work correctly."""
    standard_topics = [
        "system.power.battery",
        "system.thermal.throttling",
        "security.firewall.panic",
        "agent.battery_monitor.success",
        "agent.battery_monitor.failure",
        "system.storage.low",
        "network.connection.public",
    ]

    received = {topic: [] for topic in standard_topics}

    for topic in standard_topics:
        event_bus.subscribe(topic, lambda e, t=topic: received[t].append(e))

    for topic in standard_topics:
        event_bus.publish(topic, {"test": "data"})

    time.sleep(0.2)

    for topic in standard_topics:
        assert len(received[topic]) == 1, f"Topic {topic} did not receive event"


def test_subscription_dataclass():
    """Test Subscription dataclass structure."""
    callback = lambda e: None
    sub = Subscription(topic="test.topic", callback=callback, subscriber_id="test_sub")

    assert sub.topic == "test.topic"
    assert sub.callback == callback
    assert sub.subscriber_id == "test_sub"
