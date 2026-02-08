"""
Factory reset and backup management.
Part of v14.0 "Horizon Update".
"""
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass
from typing import List

from utils.containers import Result

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks")
BACKUP_DIR = os.path.join(CONFIG_DIR, "backups")


@dataclass
class BackupInfo:
    """Information about a configuration backup."""
    name: str
    path: str
    created_at: float
    size_bytes: int


class FactoryReset:
    """Manage configuration backups and factory reset."""

    @staticmethod
    def create_backup(name: str = "") -> Result:
        """
        Create a backup of all configuration files.

        Args:
            name: Optional backup name. Auto-generated if empty.

        Returns:
            Result with backup path in data.
        """
        if not name:
            name = time.strftime("backup_%Y%m%d_%H%M%S")

        backup_path = os.path.join(BACKUP_DIR, name)

        try:
            os.makedirs(backup_path, exist_ok=True)

            # Copy all JSON config files
            copied = 0
            if os.path.isdir(CONFIG_DIR):
                for filename in os.listdir(CONFIG_DIR):
                    if filename.endswith(".json"):
                        src = os.path.join(CONFIG_DIR, filename)
                        dst = os.path.join(backup_path, filename)
                        if os.path.isfile(src):
                            shutil.copy2(src, dst)
                            copied += 1

            # Also copy the notifications file if present
            notif_file = os.path.join(CONFIG_DIR, "notifications.json")
            if os.path.isfile(notif_file):
                shutil.copy2(notif_file, os.path.join(backup_path, "notifications.json"))

            # Save a manifest
            manifest = {
                "name": name,
                "created_at": time.time(),
                "files_copied": copied,
                "version": "unknown",
            }
            try:
                from version import __version__
                manifest["version"] = __version__
            except ImportError:
                pass

            with open(os.path.join(backup_path, "manifest.json"), "w") as f:
                json.dump(manifest, f, indent=2)

            return Result(
                success=True,
                message=f"Backup created: {name} ({copied} files)",
                data=backup_path,
            )

        except OSError as exc:
            logger.error("Failed to create backup: %s", exc)
            return Result(success=False, message=f"Backup failed: {exc}")

    @staticmethod
    def list_backups() -> List[BackupInfo]:
        """List all available configuration backups."""
        backups = []

        if not os.path.isdir(BACKUP_DIR):
            return backups

        for entry in os.listdir(BACKUP_DIR):
            entry_path = os.path.join(BACKUP_DIR, entry)
            if not os.path.isdir(entry_path):
                continue

            manifest_path = os.path.join(entry_path, "manifest.json")
            created_at = os.path.getmtime(entry_path)
            size = sum(
                os.path.getsize(os.path.join(entry_path, f))
                for f in os.listdir(entry_path)
                if os.path.isfile(os.path.join(entry_path, f))
            )

            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    created_at = manifest.get("created_at", created_at)
                except (OSError, json.JSONDecodeError):
                    pass

            backups.append(BackupInfo(
                name=entry,
                path=entry_path,
                created_at=created_at,
                size_bytes=size,
            ))

        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    @staticmethod
    def restore_backup(name: str) -> Result:
        """
        Restore configuration from a named backup.

        Args:
            name: The backup name to restore from.

        Returns:
            Result indicating success or failure.
        """
        backup_path = os.path.join(BACKUP_DIR, name)

        if not os.path.isdir(backup_path):
            return Result(success=False, message=f"Backup not found: {name}")

        try:
            restored = 0
            for filename in os.listdir(backup_path):
                if filename == "manifest.json":
                    continue
                if filename.endswith(".json"):
                    src = os.path.join(backup_path, filename)
                    dst = os.path.join(CONFIG_DIR, filename)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                        restored += 1

            return Result(
                success=True,
                message=f"Restored {restored} files from backup '{name}'.",
            )

        except OSError as exc:
            logger.error("Failed to restore backup: %s", exc)
            return Result(success=False, message=f"Restore failed: {exc}")

    @staticmethod
    def delete_backup(name: str) -> Result:
        """Delete a named backup."""
        backup_path = os.path.join(BACKUP_DIR, name)

        if not os.path.isdir(backup_path):
            return Result(success=False, message=f"Backup not found: {name}")

        try:
            shutil.rmtree(backup_path)
            return Result(success=True, message=f"Backup '{name}' deleted.")
        except OSError as exc:
            return Result(success=False, message=f"Delete failed: {exc}")

    @staticmethod
    def reset_config(keep_plugins: bool = True) -> Result:
        """
        Factory reset: delete all config files and return to defaults.

        Args:
            keep_plugins: If True, preserve installed plugins.

        Returns:
            Result indicating success or failure.
        """
        try:
            # Auto-backup before reset
            FactoryReset.create_backup("pre_reset_auto")

            deleted = 0
            if os.path.isdir(CONFIG_DIR):
                for filename in os.listdir(CONFIG_DIR):
                    filepath = os.path.join(CONFIG_DIR, filename)
                    if os.path.isfile(filepath) and filename.endswith(".json"):
                        os.remove(filepath)
                        deleted += 1

                # Optionally keep plugins directory
                if not keep_plugins:
                    plugins_dir = os.path.join(CONFIG_DIR, "plugins")
                    if os.path.isdir(plugins_dir):
                        shutil.rmtree(plugins_dir)

            # Remove first-run marker to re-trigger wizard
            first_run = os.path.join(CONFIG_DIR, "first_run_complete")
            if os.path.exists(first_run):
                os.remove(first_run)

            return Result(
                success=True,
                message=f"Factory reset complete. Deleted {deleted} config files. "
                        "Restart the application to see changes.",
            )

        except OSError as exc:
            logger.error("Factory reset failed: %s", exc)
            return Result(success=False, message=f"Reset failed: {exc}")
