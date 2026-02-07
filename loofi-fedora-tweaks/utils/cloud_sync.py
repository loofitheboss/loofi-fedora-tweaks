"""
Cloud Sync Manager - Handles cloud sync and community presets.
Integrates with GitHub Gist and community preset repository.
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from datetime import datetime


class CloudSyncManager:
    """Manages cloud sync operations and community presets."""
    
    # Community presets repository
    PRESETS_REPO = "https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks-presets/main"
    PRESETS_INDEX_URL = f"{PRESETS_REPO}/index.json"
    
    # Gist API
    GIST_API = "https://api.github.com/gists"
    
    # Local storage
    CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
    TOKEN_FILE = CONFIG_DIR / ".gist_token"
    GIST_ID_FILE = CONFIG_DIR / ".gist_id"
    CACHE_DIR = CONFIG_DIR / "cache"
    
    # ==================== TOKEN MANAGEMENT ====================
    
    @classmethod
    def ensure_dirs(cls):
        """Ensure config directories exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_gist_token(cls) -> Optional[str]:
        """
        Get stored GitHub Gist token.
        
        Note: Token is stored in a hidden file. For better security,
        consider using the system keyring in a future update.
        """
        try:
            with open(cls.TOKEN_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None
    
    @classmethod
    def save_gist_token(cls, token: str) -> bool:
        """Save GitHub Gist token."""
        cls.ensure_dirs()
        try:
            with open(cls.TOKEN_FILE, "w") as f:
                f.write(token)
            # Set restrictive permissions
            os.chmod(cls.TOKEN_FILE, 0o600)
            return True
        except Exception:
            return False
    
    @classmethod
    def clear_gist_token(cls) -> bool:
        """Remove stored token."""
        try:
            cls.TOKEN_FILE.unlink(missing_ok=True)
            cls.GIST_ID_FILE.unlink(missing_ok=True)
            return True
        except Exception:
            return False
    
    @classmethod
    def get_gist_id(cls) -> Optional[str]:
        """Get stored Gist ID for syncing."""
        try:
            with open(cls.GIST_ID_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None
    
    @classmethod
    def save_gist_id(cls, gist_id: str) -> bool:
        """Save Gist ID for future syncs."""
        cls.ensure_dirs()
        try:
            with open(cls.GIST_ID_FILE, "w") as f:
                f.write(gist_id)
            return True
        except Exception:
            return False
    
    # ==================== GIST SYNC ====================
    
    @classmethod
    def sync_to_gist(cls, config: dict) -> tuple:
        """
        Sync configuration to GitHub Gist.
        
        Args:
            config: Configuration dictionary to sync.
        
        Returns:
            (success: bool, message: str)
        """
        token = cls.get_gist_token()
        if not token:
            return (False, "No GitHub token configured. Go to Settings to add your token.")
        
        gist_id = cls.get_gist_id()
        
        # Prepare gist content
        gist_content = {
            "description": "Loofi Fedora Tweaks - Config Backup",
            "public": False,
            "files": {
                "loofi-fedora-tweaks-config.json": {
                    "content": json.dumps(config, indent=2)
                }
            }
        }
        
        try:
            data = json.dumps(gist_content).encode("utf-8")
            
            if gist_id:
                # Update existing gist
                url = f"{cls.GIST_API}/{gist_id}"
                request = urllib.request.Request(url, data=data, method="PATCH")
            else:
                # Create new gist
                url = cls.GIST_API
                request = urllib.request.Request(url, data=data, method="POST")
            
            request.add_header("Authorization", f"token {token}")
            request.add_header("Content-Type", "application/json")
            request.add_header("Accept", "application/vnd.github.v3+json")
            
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode())
                new_gist_id = result.get("id")
                
                if new_gist_id and new_gist_id != gist_id:
                    cls.save_gist_id(new_gist_id)
                
                return (True, f"Config synced to Gist: {new_gist_id}")
        
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return (False, "Invalid GitHub token. Please update your token in Settings.")
            elif e.code == 404 and gist_id:
                # Gist was deleted, create a new one
                cls.GIST_ID_FILE.unlink(missing_ok=True)
                return cls.sync_to_gist(config)  # Retry
            else:
                return (False, f"GitHub API error: {e.code}")
        except Exception as e:
            return (False, f"Sync failed: {str(e)}")
    
    @classmethod
    def sync_from_gist(cls, gist_id: Optional[str] = None) -> tuple:
        """
        Download configuration from GitHub Gist.
        
        Args:
            gist_id: Optional Gist ID. Uses stored ID if not provided.
        
        Returns:
            (success: bool, config_or_message: dict|str)
        """
        gist_id = gist_id or cls.get_gist_id()
        if not gist_id:
            return (False, "No Gist ID configured. Sync your config first or enter a Gist ID.")
        
        token = cls.get_gist_token()
        
        try:
            url = f"{cls.GIST_API}/{gist_id}"
            request = urllib.request.Request(url)
            
            if token:
                request.add_header("Authorization", f"token {token}")
            request.add_header("Accept", "application/vnd.github.v3+json")
            
            with urllib.request.urlopen(request, timeout=30) as response:
                gist_data = json.loads(response.read().decode())
                
                files = gist_data.get("files", {})
                config_file = files.get("loofi-fedora-tweaks-config.json")
                
                if not config_file:
                    return (False, "Gist does not contain a valid config file.")
                
                config = json.loads(config_file["content"])
                return (True, config)
        
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return (False, "Gist not found. Check the Gist ID.")
            else:
                return (False, f"GitHub API error: {e.code}")
        except Exception as e:
            return (False, f"Download failed: {str(e)}")
    
    # ==================== COMMUNITY PRESETS ====================
    
    @classmethod
    def fetch_community_presets(cls, use_cache: bool = True) -> tuple:
        """
        Fetch list of community presets from GitHub.
        
        Args:
            use_cache: If True, use cached index if available (< 1 hour old).
        
        Returns:
            (success: bool, presets_or_message: list|str)
        """
        cls.ensure_dirs()
        cache_file = cls.CACHE_DIR / "presets_index.json"
        
        # Check cache
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                cached_time = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
                age_hours = (datetime.now() - cached_time).total_seconds() / 3600
                if age_hours < 1:
                    return (True, cached.get("presets", []))
            except Exception:
                pass
        
        # Fetch from GitHub
        try:
            request = urllib.request.Request(cls.PRESETS_INDEX_URL)
            request.add_header("User-Agent", "Loofi-Fedora-Tweaks/5.5")
            
            with urllib.request.urlopen(request, timeout=15) as response:
                presets = json.loads(response.read().decode())
                
                # Cache result
                try:
                    with open(cache_file, "w") as f:
                        json.dump({
                            "cached_at": datetime.now().isoformat(),
                            "presets": presets
                        }, f)
                except Exception:
                    pass
                
                return (True, presets)
        
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Return empty list if repo doesn't exist yet
                return (True, [])
            return (False, f"Failed to fetch presets: HTTP {e.code}")
        except Exception as e:
            # Try returning cache even if stale
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        cached = json.load(f)
                    return (True, cached.get("presets", []))
                except Exception:
                    pass
            return (False, f"Failed to fetch presets: {str(e)}")
    
    @classmethod
    def download_preset(cls, preset_id: str) -> tuple:
        """
        Download a specific community preset.
        
        Args:
            preset_id: ID of the preset to download.
        
        Returns:
            (success: bool, preset_or_message: dict|str)
        """
        try:
            url = f"{cls.PRESETS_REPO}/presets/{preset_id}.json"
            request = urllib.request.Request(url)
            request.add_header("User-Agent", "Loofi-Fedora-Tweaks/5.5")
            
            with urllib.request.urlopen(request, timeout=15) as response:
                preset = json.loads(response.read().decode())
                return (True, preset)
        
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return (False, f"Preset '{preset_id}' not found.")
            return (False, f"Download failed: HTTP {e.code}")
        except Exception as e:
            return (False, f"Download failed: {str(e)}")
    
    @classmethod
    def is_online(cls) -> bool:
        """Quick check if we have internet connectivity."""
        try:
            urllib.request.urlopen("https://github.com", timeout=5)
            return True
        except Exception:
            return False
