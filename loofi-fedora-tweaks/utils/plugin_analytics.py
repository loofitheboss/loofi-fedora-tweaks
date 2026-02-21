"""Opt-in plugin marketplace analytics pipeline."""
import json
import logging
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils.settings import SettingsManager

logger = logging.getLogger(__name__)

DEFAULT_ANALYTICS_ENDPOINT = "https://api.loofi.software/marketplace/v1/analytics/events"


@dataclass(frozen=True)
class AnalyticsEvent:
    """Anonymized analytics event payload."""
    event_type: str
    action: str
    plugin_id: str
    anonymous_client_id: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginAnalytics:
    """Collect and send anonymized usage events when explicit consent is enabled."""

    def __init__(
        self,
        settings_manager: Optional[SettingsManager] = None,
        batch_size: int = 10,
        timeout: int = 5,
    ):
        self.settings = settings_manager or SettingsManager.instance()
        self.batch_size = max(1, int(batch_size))
        self.timeout = timeout
        self._queue: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def is_enabled(self) -> bool:
        """Return whether analytics is explicitly enabled."""
        return bool(self.settings.get("plugin_analytics_enabled", False))

    def set_enabled(self, enabled: bool) -> None:
        """Persist opt-in/out state and bootstrap anonymous client id when enabling."""
        enabled = bool(enabled)
        self.settings.set("plugin_analytics_enabled", enabled)
        if enabled:
            self._get_or_create_anonymous_id()
        else:
            with self._lock:
                self._queue = []
        self.settings.save()

    def queue_size(self) -> int:
        """Current in-memory queue size (primarily for tests/diagnostics)."""
        with self._lock:
            return len(self._queue)

    def track_event(
        self,
        event_type: str,
        action: str,
        plugin_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Queue one event and flush automatically once batch size is reached."""
        if not self.is_enabled():
            return False

        event = AnalyticsEvent(
            event_type=str(event_type or "unknown"),
            action=str(action or "unknown"),
            plugin_id=str(plugin_id or ""),
            anonymous_client_id=self._get_or_create_anonymous_id(),
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=self._sanitize_metadata(metadata or {}),
        )

        should_flush = False
        with self._lock:
            self._queue.append(asdict(event))
            should_flush = len(self._queue) >= self.batch_size

        if should_flush:
            return self.flush()
        return True

    def flush(self) -> bool:
        """Send queued events as one batch. Failed sends keep events in queue."""
        if not self.is_enabled():
            return False

        with self._lock:
            if not self._queue:
                return True
            batch = list(self._queue)
            self._queue = []

        endpoint = self.settings.get("plugin_analytics_endpoint", DEFAULT_ANALYTICS_ENDPOINT)
        payload = {"events": batch}

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "User-Agent": "Loofi-Fedora-Tweaks",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout):
                pass
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            logger.warning("Failed to send analytics batch: %s", exc)
            with self._lock:
                self._queue = batch + self._queue
            return False

    def _get_or_create_anonymous_id(self) -> str:
        anon_id = str(self.settings.get("plugin_analytics_anonymous_id", "") or "").strip()
        if anon_id:
            return anon_id

        anon_id = uuid.uuid4().hex
        self.settings.set("plugin_analytics_anonymous_id", anon_id)
        self.settings.save()
        return anon_id

    @staticmethod
    def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Keep metadata JSON-safe and bounded to avoid accidental sensitive payloads."""
        sanitized: Dict[str, Any] = {}
        for key, value in metadata.items():
            key_str = str(key)[:64]
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key_str] = value
            else:
                sanitized[key_str] = str(value)
        return sanitized
