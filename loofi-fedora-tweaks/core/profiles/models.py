"""Profile schema models for v24.0 profile storage and transport."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

SCHEMA_VERSION = 1


def _sanitize_key(value: str) -> str:
    """Sanitize profile keys to filesystem-safe lower_snake_case."""
    key = (value or "").strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    key = key.replace("..", "")
    key = "".join(ch for ch in key if ch.isalnum() or ch in ("_", "-"))
    return key.lower() or "unnamed_profile"


@dataclass
class ProfileRecord:
    """A normalized profile record."""

    key: str
    name: str
    description: str = ""
    icon: str = "\U0001f527"
    builtin: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        self.key = _sanitize_key(self.key)
        self.name = (self.name or "").strip()
        if not self.key:
            raise ValueError("Profile key cannot be empty")
        if not self.name:
            raise ValueError("Profile name cannot be empty")
        if not isinstance(self.settings, dict):
            raise ValueError("Profile settings must be a dictionary")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile for API/UI usage."""
        return {
            "schema_version": self.schema_version,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "builtin": self.builtin,
            "settings": self.settings,
        }

    def to_file_dict(self) -> Dict[str, Any]:
        """Serialize profile for on-disk custom profile files."""
        return {
            "schema_version": self.schema_version,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_key: str = "") -> "ProfileRecord":
        """Create a profile from current or legacy dictionaries."""
        if not isinstance(data, dict):
            raise ValueError("Profile payload must be a dictionary")

        payload = data.get("profile", data)
        if not isinstance(payload, dict):
            raise ValueError("Profile payload must be a dictionary")

        raw_key = payload.get("key") or default_key or payload.get("name", "")
        key = _sanitize_key(str(raw_key))
        name = str(payload.get("name") or key)

        return cls(
            key=key,
            name=name,
            description=str(payload.get("description", "")),
            icon=str(payload.get("icon", "\U0001f527")),
            builtin=bool(payload.get("builtin", False)),
            settings=payload.get("settings") or {},
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )


@dataclass
class ProfileBundle:
    """A versioned collection of profiles for import/export."""

    profiles: List[ProfileRecord] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize bundle to JSON-compatible dict."""
        return {
            "schema_version": self.schema_version,
            "kind": "profile_bundle",
            "profiles": [profile.to_dict() for profile in self.profiles],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileBundle":
        """Create bundle from exported payload or legacy list payload."""
        if not isinstance(data, dict):
            raise ValueError("Bundle payload must be a dictionary")

        raw_profiles = data.get("profiles")
        if raw_profiles is None and "profile_bundle" in data:
            raw_profiles = data.get("profile_bundle")
        if not isinstance(raw_profiles, list):
            raise ValueError("Bundle payload must contain a 'profiles' list")

        profiles: List[ProfileRecord] = []
        for item in raw_profiles:
            if not isinstance(item, dict):
                raise ValueError("Each profile entry in bundle must be a dictionary")
            profiles.append(ProfileRecord.from_dict(item))

        return cls(
            profiles=profiles,
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
        )
