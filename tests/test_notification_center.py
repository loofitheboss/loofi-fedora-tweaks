"""
Tests for the Notification Center utility.
Part of v13.5 UX Polish.
"""

import time

import pytest

from utils.notification_center import (
    MAX_NOTIFICATIONS,
    Notification,
    NotificationCenter,
)


@pytest.fixture(autouse=True)
def reset_singleton(tmp_path, monkeypatch):
    """Reset singleton and redirect persistence to tmp_path for every test."""
    NotificationCenter.reset_singleton()
    notif_file = tmp_path / "notifications.json"
    monkeypatch.setattr("utils.notification_center.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("utils.notification_center.NOTIFICATIONS_FILE", notif_file)
    yield
    NotificationCenter.reset_singleton()


class TestSingleton:
    """Tests for the singleton pattern."""

    def test_singleton_returns_same_instance(self):
        nc1 = NotificationCenter()
        nc2 = NotificationCenter()
        assert nc1 is nc2

    def test_reset_singleton_creates_new_instance(self):
        nc1 = NotificationCenter()
        NotificationCenter.reset_singleton()
        nc2 = NotificationCenter()
        assert nc1 is not nc2


class TestAddNotification:
    """Tests for adding notifications."""

    def test_add_returns_notification(self):
        nc = NotificationCenter()
        notif = nc.add("Test", "Hello world")
        assert isinstance(notif, Notification)
        assert notif.title == "Test"
        assert notif.message == "Hello world"
        assert notif.category == "general"
        assert notif.read is False

    def test_add_with_category(self):
        nc = NotificationCenter()
        notif = nc.add("Sec Alert", "Firewall updated", category="security")
        assert notif.category == "security"

    def test_add_inserts_at_front(self):
        nc = NotificationCenter()
        nc.add("First", "msg1")
        nc.add("Second", "msg2")
        recent = nc.get_recent(10)
        assert recent[0].title == "Second"
        assert recent[1].title == "First"

    def test_notification_has_unique_id(self):
        nc = NotificationCenter()
        n1 = nc.add("A", "a")
        n2 = nc.add("B", "b")
        assert n1.id != n2.id

    def test_notification_has_timestamp(self):
        before = time.time()
        nc = NotificationCenter()
        notif = nc.add("T", "m")
        after = time.time()
        assert before <= notif.timestamp <= after


class TestUnreadCount:
    """Tests for unread count tracking."""

    def test_unread_count_initial(self):
        nc = NotificationCenter()
        assert nc.get_unread_count() == 0

    def test_unread_count_after_adds(self):
        nc = NotificationCenter()
        nc.add("A", "a")
        nc.add("B", "b")
        assert nc.get_unread_count() == 2


class TestMarkRead:
    """Tests for marking notifications as read."""

    def test_mark_read_single(self):
        nc = NotificationCenter()
        n = nc.add("Title", "msg")
        nc.mark_read(n.id)
        assert nc.get_unread_count() == 0

    def test_mark_all_read(self):
        nc = NotificationCenter()
        nc.add("A", "a")
        nc.add("B", "b")
        nc.add("C", "c")
        nc.mark_all_read()
        assert nc.get_unread_count() == 0


class TestDismiss:
    """Tests for dismissing notifications."""

    def test_dismiss_removes_notification(self):
        nc = NotificationCenter()
        n = nc.add("X", "x")
        nc.dismiss(n.id)
        assert len(nc.get_recent(10)) == 0

    def test_dismiss_nonexistent_is_safe(self):
        nc = NotificationCenter()
        nc.add("Y", "y")
        nc.dismiss("nonexistent-id")
        assert len(nc.get_recent(10)) == 1


class TestFIFOEviction:
    """Tests for FIFO eviction at MAX_NOTIFICATIONS."""

    def test_eviction_at_max(self):
        nc = NotificationCenter()
        for i in range(MAX_NOTIFICATIONS + 10):
            nc.add(f"N{i}", f"msg{i}")
        assert len(nc.get_recent(MAX_NOTIFICATIONS + 10)) == MAX_NOTIFICATIONS
        # Most recent should be the last added
        assert nc.get_recent(1)[0].title == f"N{MAX_NOTIFICATIONS + 9}"


class TestClearAll:
    """Tests for clearing all notifications."""

    def test_clear_all(self):
        nc = NotificationCenter()
        nc.add("A", "a")
        nc.add("B", "b")
        nc.clear_all()
        assert len(nc.get_recent(10)) == 0
        assert nc.get_unread_count() == 0


class TestPersistence:
    """Tests for JSON persistence round-trip."""

    def test_round_trip(self, tmp_path, monkeypatch):
        """Notifications survive a singleton reset (simulating app restart)."""
        nc = NotificationCenter()
        nc.add("Persist", "This should survive")
        nc.add("Also", "This too")

        # Reset singleton to simulate restart
        NotificationCenter.reset_singleton()
        nc2 = NotificationCenter()
        recent = nc2.get_recent(10)
        assert len(recent) == 2
        assert recent[0].title == "Also"
        assert recent[1].title == "Persist"

    def test_corrupt_file_handling(self, tmp_path, monkeypatch):
        """Corrupt JSON file should not crash, just start empty."""
        notif_file = tmp_path / "notifications.json"
        notif_file.write_text("{{{not valid json!!!")

        NotificationCenter.reset_singleton()
        nc = NotificationCenter()
        assert len(nc.get_recent(10)) == 0

    def test_empty_file_handling(self, tmp_path, monkeypatch):
        """Empty file should not crash."""
        notif_file = tmp_path / "notifications.json"
        notif_file.write_text("")

        NotificationCenter.reset_singleton()
        nc = NotificationCenter()
        assert len(nc.get_recent(10)) == 0


class TestGetRecent:
    """Tests for the get_recent method."""

    def test_get_recent_limit(self):
        nc = NotificationCenter()
        for i in range(10):
            nc.add(f"N{i}", f"msg{i}")
        recent = nc.get_recent(3)
        assert len(recent) == 3
        assert recent[0].title == "N9"

    def test_get_recent_fewer_than_limit(self):
        nc = NotificationCenter()
        nc.add("Only", "one")
        recent = nc.get_recent(20)
        assert len(recent) == 1
