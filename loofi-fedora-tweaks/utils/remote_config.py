"""Remote app catalog fetcher with local caching and offline fallback."""
import os
import json
import urllib.request
import urllib.error
from PyQt6.QtCore import QThread, pyqtSignal

from utils.log import get_logger

logger = get_logger(__name__)


class AppConfigFetcher(QThread):
    config_ready = pyqtSignal(list)
    config_error = pyqtSignal(str)

    REMOTE_URL = "https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/config/apps.json"
    CACHE_DIR = os.path.expanduser("~/.cache/loofi-fedora-tweaks")
    CACHE_FILE = os.path.join(CACHE_DIR, "apps.json")
    LOCAL_FALLBACK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'apps.json')

    def __init__(self, force_refresh=False):
        super().__init__()
        self.force_refresh = force_refresh

    def run(self):
        # 1. Try Remote
        if self.force_refresh or not os.path.exists(self.CACHE_FILE):
            try:
                with urllib.request.urlopen(self.REMOTE_URL, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        self._save_cache(data)
                        self.config_ready.emit(data)
                        return
            except (OSError, ValueError, json.JSONDecodeError) as e:
                logger.warning("Remote fetch failed: %s", e)

        # 2. Try Cache
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self.config_ready.emit(data)
                    return
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Cache load failed: %s", e)

        # 3. Fallback to Local Package
        if os.path.exists(self.LOCAL_FALLBACK):
            try:
                with open(self.LOCAL_FALLBACK, 'r') as f:
                    data = json.load(f)
                    self.config_ready.emit(data)
                    return
            except (OSError, json.JSONDecodeError) as e:
                self.config_error.emit(f"Failed to load any config: {e}")
        else:
            self.config_error.emit("No configuration found.")

    def _save_cache(self, data):
        try:
            os.makedirs(self.CACHE_DIR, exist_ok=True)
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to save cache: %s", e)
