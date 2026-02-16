"""
Agent Notifications — Desktop and webhook alerts for agent results.
Part of v19.0 "Vanguard".

Provides:
- AgentNotificationConfig: Per-agent notification settings
- AgentNotifier: Routes agent results to desktop notifications and webhooks
- Severity-based filtering with configurable thresholds
- Webhook POST with JSON payload via urllib (no external dependencies)
- Integration with existing NotificationManager and NotificationCenter
"""

import json
import logging
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from utils.agents import AgentResult

logger = logging.getLogger(__name__)

# Module constants
DEFAULT_MIN_SEVERITY = "high"
WEBHOOK_TIMEOUT_SECONDS = 10
NOTIFICATION_COOLDOWN_SECONDS = 60
SEVERITY_RANKS = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class AgentNotificationConfig:
    """Per-agent notification settings."""
    enabled: bool = False
    channels: List[str] = field(default_factory=lambda: ["desktop", "in_app"])
    min_severity: str = DEFAULT_MIN_SEVERITY
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = field(default_factory=dict)
    cooldown_seconds: int = NOTIFICATION_COOLDOWN_SECONDS
    notify_on_error: bool = True
    notify_on_alert: bool = True

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "channels": self.channels,
            "min_severity": self.min_severity,
            "webhook_url": self.webhook_url,
            "webhook_headers": self.webhook_headers,
            "cooldown_seconds": self.cooldown_seconds,
            "notify_on_error": self.notify_on_error,
            "notify_on_alert": self.notify_on_alert,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentNotificationConfig":
        if not data:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            channels=data.get("channels", ["desktop", "in_app"]),
            min_severity=data.get("min_severity", DEFAULT_MIN_SEVERITY),
            webhook_url=data.get("webhook_url"),
            webhook_headers=data.get("webhook_headers", {}),
            cooldown_seconds=data.get("cooldown_seconds", NOTIFICATION_COOLDOWN_SECONDS),
            notify_on_error=data.get("notify_on_error", True),
            notify_on_alert=data.get("notify_on_alert", True),
        )


class AgentNotifier:
    """
    Routes agent results to configured notification channels.

    Usage:
        notifier = AgentNotifier()
        notifier.notify(agent_id, agent_name, result, notification_config)
    """

    def __init__(self):
        self._last_notify: Dict[str, float] = {}

    def notify(
        self,
        agent_id: str,
        agent_name: str,
        result: AgentResult,
        config: AgentNotificationConfig,
    ) -> bool:
        """
        Process a result through notification channels.

        Returns True if at least one notification was sent.
        """
        if not config.enabled:
            return False

        if not self._should_notify(agent_id, result, config):
            return False

        sent = False

        if "desktop" in config.channels:
            if self._send_desktop(agent_name, result):
                sent = True

        if "in_app" in config.channels:
            self._send_in_app(agent_name, result)
            sent = True

        if "webhook" in config.channels and config.webhook_url:
            self._send_webhook(agent_id, agent_name, result, config)
            sent = True

        if sent:
            self._last_notify[agent_id] = time.time()

        return sent

    def _should_notify(
        self,
        agent_id: str,
        result: AgentResult,
        config: AgentNotificationConfig,
    ) -> bool:
        """Check if this result warrants a notification."""
        # Always notify on errors if configured
        if config.notify_on_error and not result.success:
            return self._check_cooldown(agent_id, config)

        # Always notify on alerts if configured
        if config.notify_on_alert and result.data and result.data.get("alert"):
            return self._check_cooldown(agent_id, config)

        # Check severity threshold
        result_severity = self._get_result_severity(result)
        min_rank = SEVERITY_RANKS.get(config.min_severity, 3)
        result_rank = SEVERITY_RANKS.get(result_severity, 0)

        if result_rank < min_rank:
            return False

        return self._check_cooldown(agent_id, config)

    def _check_cooldown(self, agent_id: str, config: AgentNotificationConfig) -> bool:
        """Check if cooldown period has elapsed for this agent."""
        last = self._last_notify.get(agent_id, 0)
        return (time.time() - last) >= config.cooldown_seconds

    @staticmethod
    def _get_result_severity(result: AgentResult) -> str:
        """Infer severity from result data."""
        if result.data:
            if result.data.get("alert"):
                return "high"
            severity = result.data.get("severity", "info")
            if severity in SEVERITY_RANKS:
                return str(severity)
        if not result.success:
            return "medium"
        return "info"

    @staticmethod
    def _send_desktop(agent_name: str, result: AgentResult) -> bool:
        """Send desktop notification via existing NotificationManager."""
        try:
            from utils.notifications import NotificationManager
            icon = "dialog-warning" if not result.success else "dialog-information"
            urgency = "critical" if not result.success else "normal"
            title = f"Agent: {agent_name}"
            body = result.message[:200]
            return NotificationManager.send(
                title=title, body=body, icon=icon, urgency=urgency
            )
        except (ImportError, AttributeError, OSError) as exc:
            logger.debug("Desktop notification failed: %s", exc)
            return False

    @staticmethod
    def _send_in_app(agent_name: str, result: AgentResult):
        """Add to in-app NotificationCenter."""
        try:
            from utils.notification_center import NotificationCenter
            nc = NotificationCenter()
            category = "security" if "security" in agent_name.lower() else "system"
            nc.add(
                title=f"Agent: {agent_name}",
                message=result.message[:200],
                category=category,
            )
        except (ImportError, AttributeError, OSError) as exc:
            logger.debug("In-app notification failed: %s", exc)

    @staticmethod
    def _send_webhook(
        agent_id: str,
        agent_name: str,
        result: AgentResult,
        config: AgentNotificationConfig,
    ) -> bool:
        """POST JSON payload to webhook URL in a background thread."""
        if not config.webhook_url:
            return False

        payload = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "success": result.success,
            "message": result.message,
            "action_id": result.action_id,
            "timestamp": result.timestamp,
            "data": result.data,
        }

        def _do_post():
            try:
                data = json.dumps(payload).encode("utf-8")
                headers = {"Content-Type": "application/json"}
                headers.update(config.webhook_headers)
                req = urllib.request.Request(
                    config.webhook_url,
                    data=data,
                    headers=headers,
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT_SECONDS)
                logger.debug("Webhook sent for agent %s", agent_id)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                logger.debug("Webhook failed for agent %s: %s", agent_id, exc)

        thread = threading.Thread(target=_do_post, daemon=True, name="AgentWebhook")
        thread.start()
        return True

    @staticmethod
    def validate_webhook_url(url: str) -> bool:
        """Basic URL validation for webhook configuration."""
        if not url:
            return False
        return url.startswith("https://") or url.startswith("http://")
