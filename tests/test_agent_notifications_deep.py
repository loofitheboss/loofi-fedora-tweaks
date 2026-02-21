"""
Tests for utils/agent_notifications.py — Agent notification system.

Covers:
- AgentNotificationConfig: to_dict, from_dict (empty, partial, full)
- AgentNotifier: notify, _should_notify, _check_cooldown, _get_result_severity
- _send_desktop, _send_in_app, _send_webhook
- validate_webhook_url
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.agent_notifications import (
    AgentNotificationConfig,
    AgentNotifier,
)
from utils.agents import AgentResult


def _make_result(success=True, message="ok", data=None, action_id="a1"):
    return AgentResult(
        success=success,
        message=message,
        data=data or {},
        action_id=action_id,
        timestamp=time.time(),
    )


class TestAgentNotificationConfig(unittest.TestCase):

    def test_defaults(self):
        c = AgentNotificationConfig()
        self.assertFalse(c.enabled)
        self.assertEqual(c.channels, ["desktop", "in_app"])
        self.assertEqual(c.min_severity, "high")
        self.assertIsNone(c.webhook_url)

    def test_to_dict(self):
        c = AgentNotificationConfig(enabled=True, webhook_url="https://example.com/hook")
        d = c.to_dict()
        self.assertTrue(d["enabled"])
        self.assertEqual(d["webhook_url"], "https://example.com/hook")

    def test_from_dict_empty(self):
        c = AgentNotificationConfig.from_dict({})
        self.assertFalse(c.enabled)

    def test_from_dict_none(self):
        c = AgentNotificationConfig.from_dict(None)
        self.assertFalse(c.enabled)

    def test_from_dict_full(self):
        d = {
            "enabled": True,
            "channels": ["webhook"],
            "min_severity": "medium",
            "webhook_url": "https://hook.example.com",
            "webhook_headers": {"Authorization": "Bearer token"},
            "cooldown_seconds": 120,
            "notify_on_error": False,
            "notify_on_alert": False,
        }
        c = AgentNotificationConfig.from_dict(d)
        self.assertTrue(c.enabled)
        self.assertEqual(c.channels, ["webhook"])
        self.assertEqual(c.min_severity, "medium")
        self.assertEqual(c.cooldown_seconds, 120)
        self.assertFalse(c.notify_on_error)

    def test_roundtrip(self):
        c = AgentNotificationConfig(enabled=True, min_severity="critical")
        c2 = AgentNotificationConfig.from_dict(c.to_dict())
        self.assertEqual(c.enabled, c2.enabled)
        self.assertEqual(c.min_severity, c2.min_severity)


class TestAgentNotifierNotify(unittest.TestCase):

    def setUp(self):
        self.notifier = AgentNotifier()

    def test_disabled_config_returns_false(self):
        config = AgentNotificationConfig(enabled=False)
        result = _make_result()
        self.assertFalse(self.notifier.notify("a1", "Agent1", result, config))

    @patch.object(AgentNotifier, "_send_desktop", return_value=True)
    def test_enabled_desktop(self, mock_desktop):
        config = AgentNotificationConfig(
            enabled=True,
            channels=["desktop"],
            min_severity="info",
        )
        result = _make_result(success=False)
        sent = self.notifier.notify("a1", "Agent1", result, config)
        self.assertTrue(sent)
        mock_desktop.assert_called_once()

    @patch.object(AgentNotifier, "_send_in_app")
    def test_enabled_in_app(self, mock_inapp):
        config = AgentNotificationConfig(
            enabled=True,
            channels=["in_app"],
            min_severity="info",
        )
        result = _make_result(success=False)
        sent = self.notifier.notify("a1", "Agent1", result, config)
        self.assertTrue(sent)
        mock_inapp.assert_called_once()

    @patch.object(AgentNotifier, "_send_webhook", return_value=True)
    def test_enabled_webhook(self, mock_webhook):
        config = AgentNotificationConfig(
            enabled=True,
            channels=["webhook"],
            webhook_url="https://example.com/hook",
            min_severity="info",
        )
        result = _make_result(success=False)
        sent = self.notifier.notify("a1", "Agent1", result, config)
        self.assertTrue(sent)

    def test_cooldown_blocks(self):
        config = AgentNotificationConfig(
            enabled=True,
            channels=["in_app"],
            min_severity="info",
            cooldown_seconds=9999,
        )
        result = _make_result(success=False)
        self.notifier._last_notify["a1"] = time.time()
        sent = self.notifier.notify("a1", "Agent1", result, config)
        self.assertFalse(sent)


class TestShouldNotify(unittest.TestCase):

    def setUp(self):
        self.notifier = AgentNotifier()

    def test_error_with_notify_on_error(self):
        config = AgentNotificationConfig(enabled=True, notify_on_error=True)
        result = _make_result(success=False)
        self.assertTrue(self.notifier._should_notify("a1", result, config))

    def test_alert_in_data(self):
        config = AgentNotificationConfig(enabled=True, notify_on_alert=True)
        result = _make_result(data={"alert": True})
        self.assertTrue(self.notifier._should_notify("a1", result, config))

    def test_below_severity_threshold(self):
        config = AgentNotificationConfig(
            enabled=True,
            min_severity="critical",
            notify_on_error=False,
            notify_on_alert=False,
        )
        result = _make_result(data={"severity": "low"})
        self.assertFalse(self.notifier._should_notify("a1", result, config))

    def test_above_severity_threshold(self):
        config = AgentNotificationConfig(
            enabled=True,
            min_severity="low",
            notify_on_error=False,
            notify_on_alert=False,
        )
        result = _make_result(data={"severity": "high"})
        self.assertTrue(self.notifier._should_notify("a1", result, config))


class TestGetResultSeverity(unittest.TestCase):

    def test_alert_is_high(self):
        result = _make_result(data={"alert": True})
        self.assertEqual(AgentNotifier._get_result_severity(result), "high")

    def test_explicit_severity(self):
        result = _make_result(data={"severity": "critical"})
        self.assertEqual(AgentNotifier._get_result_severity(result), "critical")

    def test_unknown_severity_fallback(self):
        result = _make_result(data={"severity": "unknown_value"})
        # unknown severity, success=True → info
        self.assertEqual(AgentNotifier._get_result_severity(result), "info")

    def test_failure_is_medium(self):
        result = _make_result(success=False, data={})
        self.assertEqual(AgentNotifier._get_result_severity(result), "medium")

    def test_success_no_data(self):
        result = _make_result(data={})
        self.assertEqual(AgentNotifier._get_result_severity(result), "info")


class TestSendDesktop(unittest.TestCase):

    @patch("utils.notifications.NotificationManager.send", return_value=True)
    def test_success(self, mock_send):
        result = _make_result(success=False)
        self.assertTrue(AgentNotifier._send_desktop("Agent1", result))
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        self.assertIn("Agent1", call_kwargs["title"])

    @patch("utils.notifications.NotificationManager.send", side_effect=OSError("fail"))
    def test_exception(self, mock_send):
        result = _make_result()
        self.assertFalse(AgentNotifier._send_desktop("Agent1", result))


class TestSendInApp(unittest.TestCase):

    @patch("utils.notification_center.NotificationCenter")
    def test_success(self, mock_nc_cls):
        mock_nc = MagicMock()
        mock_nc_cls.return_value = mock_nc
        result = _make_result()
        AgentNotifier._send_in_app("Agent1", result)
        mock_nc.add.assert_called_once()

    @patch("utils.notification_center.NotificationCenter", side_effect=OSError("fail"))
    def test_exception(self, mock_nc_cls):
        result = _make_result()
        AgentNotifier._send_in_app("Agent1", result)  # Should not raise


class TestSendWebhook(unittest.TestCase):

    def test_no_url(self):
        config = AgentNotificationConfig()
        result = _make_result()
        self.assertFalse(AgentNotifier._send_webhook("a1", "Agent1", result, config))

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_with_url(self, mock_req_cls, mock_urlopen):
        config = AgentNotificationConfig(webhook_url="https://example.com/hook")
        result = _make_result()
        sent = AgentNotifier._send_webhook("a1", "Agent1", result, config)
        self.assertTrue(sent)
        # Wait a moment for the thread to start
        import time
        time.sleep(0.1)


class TestValidateWebhookUrl(unittest.TestCase):

    def test_https(self):
        self.assertTrue(AgentNotifier.validate_webhook_url("https://example.com"))

    def test_http(self):
        self.assertTrue(AgentNotifier.validate_webhook_url("http://example.com"))

    def test_empty(self):
        self.assertFalse(AgentNotifier.validate_webhook_url(""))

    def test_invalid(self):
        self.assertFalse(AgentNotifier.validate_webhook_url("ftp://example.com"))

    def test_none_strings(self):
        self.assertFalse(AgentNotifier.validate_webhook_url(""))


if __name__ == '__main__':
    unittest.main()
