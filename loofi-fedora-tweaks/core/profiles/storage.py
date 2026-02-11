"""Filesystem-backed profile storage and import/export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.profiles.models import ProfileBundle, ProfileRecord


class ProfileStore:
    """Storage engine for built-in and custom profiles."""

    def __init__(self, profiles_dir: str, builtin_profiles: Optional[Dict[str, dict]] = None):
        self.profiles_dir = Path(profiles_dir)
        self.builtin_profiles = builtin_profiles or {}

    def list_profiles(self) -> List[ProfileRecord]:
        """Return normalized built-in and custom profiles."""
        profiles: List[ProfileRecord] = []

        for key, payload in self.builtin_profiles.items():
            profiles.append(
                ProfileRecord(
                    key=key,
                    name=payload.get("name", key),
                    description=payload.get("description", ""),
                    icon=payload.get("icon", "\U0001f527"),
                    builtin=True,
                    settings=payload.get("settings") or {},
                )
            )

        if self.profiles_dir.is_dir():
            for path in sorted(self.profiles_dir.glob("*.json")):
                record = self._read_custom_file(path)
                if record:
                    profiles.append(record)

        return profiles

    def get_profile(self, key: str) -> Optional[ProfileRecord]:
        """Get one profile by key."""
        for record in self.list_profiles():
            if record.key == key:
                return record
        return None

    def save_custom_profile(self, record: ProfileRecord, overwrite: bool = False) -> Tuple[bool, str, Optional[str]]:
        """Persist a custom profile record to disk."""
        if record.builtin or record.key in self.builtin_profiles:
            return False, "Cannot overwrite built-in profiles.", None

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        path = self.profiles_dir / f"{record.key}.json"

        if path.exists() and not overwrite:
            return False, f"Custom profile '{record.key}' already exists.", None

        try:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(record.to_file_dict(), fh, indent=4, ensure_ascii=False)
        except OSError as exc:
            return False, f"Failed to save profile: {exc}", None

        return True, f"Custom profile '{record.name}' saved.", str(path)

    def delete_custom_profile(self, key: str) -> Tuple[bool, str]:
        """Delete a custom profile by key."""
        if key in self.builtin_profiles:
            return False, "Cannot delete built-in profiles."

        path = self.profiles_dir / f"{key}.json"
        if not path.exists():
            return False, f"Custom profile '{key}' not found."

        try:
            path.unlink()
        except OSError as exc:
            return False, f"Failed to delete profile: {exc}"

        return True, f"Profile '{key}' deleted."

    def export_profile_data(self, key: str) -> Tuple[bool, str, dict]:
        """Export one profile as a versioned payload."""
        record = self.get_profile(key)
        if not record:
            return False, f"Profile '{key}' not found.", {}

        return True, "Profile exported.", {
            "schema_version": record.schema_version,
            "kind": "profile",
            "profile": record.to_dict(),
        }

    def import_profile_data(self, payload: dict, overwrite: bool = False) -> Tuple[bool, str, dict]:
        """Import one profile payload from dict."""
        try:
            record = ProfileRecord.from_dict(payload)
        except ValueError as exc:
            return False, f"Invalid profile payload: {exc}", {}

        if record.key in self.builtin_profiles:
            return False, "Cannot overwrite built-in profiles.", {"key": record.key}

        ok, message, path = self.save_custom_profile(record, overwrite=overwrite)
        return ok, message, {"key": record.key, "path": path}

    def export_bundle_data(self, include_builtins: bool = False) -> Tuple[bool, str, dict]:
        """Export all profiles as a bundle payload."""
        records = self.list_profiles()
        if not include_builtins:
            records = [r for r in records if not r.builtin]

        bundle = ProfileBundle(profiles=records)
        return True, "Bundle exported.", bundle.to_dict()

    def import_bundle_data(self, payload: dict, overwrite: bool = False) -> Tuple[bool, str, dict]:
        """Import a profile bundle payload."""
        try:
            bundle = ProfileBundle.from_dict(payload)
        except ValueError as exc:
            return False, f"Invalid bundle payload: {exc}", {}

        imported = []
        skipped = []
        errors = []

        for record in bundle.profiles:
            if record.key in self.builtin_profiles:
                skipped.append(record.key)
                continue
            ok, message, _path = self.save_custom_profile(record, overwrite=overwrite)
            if ok:
                imported.append(record.key)
            else:
                errors.append({"key": record.key, "message": message})

        success = len(errors) == 0
        message = "Bundle imported." if success else "Bundle imported with errors."
        return success, message, {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }

    def export_profile(self, key: str, path: str) -> Tuple[bool, str]:
        """Write one profile export payload to a file."""
        ok, message, payload = self.export_profile_data(key)
        if not ok:
            return False, message

        try:
            self._write_json(path, payload)
        except OSError as exc:
            return False, f"Failed to export profile: {exc}"

        return True, f"Profile '{key}' exported to {path}."

    def import_profile(self, path: str, overwrite: bool = False) -> Tuple[bool, str, dict]:
        """Read one profile payload from a file and import."""
        try:
            payload = self._read_json(path)
        except (OSError, ValueError) as exc:
            return False, f"Failed to read profile file: {exc}", {}

        return self.import_profile_data(payload, overwrite=overwrite)

    def export_bundle(self, path: str, include_builtins: bool = False) -> Tuple[bool, str]:
        """Write bundle payload to a file."""
        ok, message, payload = self.export_bundle_data(include_builtins=include_builtins)
        if not ok:
            return False, message

        try:
            self._write_json(path, payload)
        except OSError as exc:
            return False, f"Failed to export bundle: {exc}"

        return True, f"Bundle exported to {path}."

    def import_bundle(self, path: str, overwrite: bool = False) -> Tuple[bool, str, dict]:
        """Read bundle payload from file and import."""
        try:
            payload = self._read_json(path)
        except (OSError, ValueError) as exc:
            return False, f"Failed to read bundle file: {exc}", {}

        return self.import_bundle_data(payload, overwrite=overwrite)

    def _read_custom_file(self, path: Path) -> Optional[ProfileRecord]:
        try:
            payload = self._read_json(str(path))
            return ProfileRecord.from_dict(payload, default_key=path.stem)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _read_json(path: str) -> dict:
        with Path(path).open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    @staticmethod
    def _write_json(path: str, payload: dict):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
