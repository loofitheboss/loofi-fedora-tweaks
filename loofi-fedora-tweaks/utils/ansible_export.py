"""
Ansible playbook export utilities.
Part of v8.0 "Replicator" update.

Generates standard Ansible playbooks from current system configuration,
allowing users to replicate their setup on any Fedora machine.
"""

import json
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path
from datetime import datetime


@dataclass
class Result:
    """Operation result with message."""
    success: bool
    message: str
    data: Optional[dict] = None


class AnsibleExporter:
    """
    Exports current system state to Ansible playbook.

    This is the killer feature of v8.0 - users can replicate their
    entire Loofi configuration on any Fedora machine without needing
    Loofi itself.
    """

    @classmethod
    def _get_installed_packages(cls) -> list[str]:
        """Get list of user-installed packages."""
        try:
            result = subprocess.run(
                ["dnf", "repoquery", "--userinstalled", "--qf", "%{name}"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                packages = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
                # Filter out kernel packages and base system
                excluded_prefixes = ("kernel", "glibc", "systemd", "dnf", "rpm", "fedora-")
                return [p for p in packages if not any(p.startswith(x) for x in excluded_prefixes)]
            return []
        except Exception:
            return []

    @classmethod
    def _get_flatpak_apps(cls) -> list[str]:
        """Get list of installed Flatpak apps."""
        if not shutil.which("flatpak"):
            return []

        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return [a.strip() for a in result.stdout.strip().split("\n") if a.strip()]
            return []
        except Exception:
            return []

    @classmethod
    def _get_gnome_settings(cls) -> dict[str, Any]:
        """Get relevant GNOME/GTK settings."""
        settings: dict[str, Any] = {}

        if not shutil.which("gsettings"):
            return settings

        # Key settings to capture
        gsettings_keys = [
            ("org.gnome.desktop.interface", "gtk-theme"),
            ("org.gnome.desktop.interface", "icon-theme"),
            ("org.gnome.desktop.interface", "cursor-theme"),
            ("org.gnome.desktop.interface", "color-scheme"),
            ("org.gnome.desktop.interface", "font-name"),
            ("org.gnome.desktop.interface", "monospace-font-name"),
            ("org.gnome.desktop.wm.preferences", "button-layout"),
        ]

        for schema, key in gsettings_keys:
            try:
                result = subprocess.run(
                    ["gsettings", "get", schema, key],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    value = result.stdout.strip().strip("'")
                    settings[f"{schema}/{key}"] = value
            except Exception:
                pass

        return settings

    @classmethod
    def _get_enabled_repos(cls) -> list[str]:
        """Get list of enabled third-party repos."""
        try:
            result = subprocess.run(
                ["dnf", "repolist", "--enabled", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                repos = []
                for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if parts:
                            repo = parts[0]
                            # Only include non-default repos
                            if not repo.startswith(("fedora", "updates")):
                                repos.append(repo)
                return repos
            return []
        except Exception:
            return []

    @classmethod
    def generate_playbook(
        cls,
        include_packages: bool = True,
        include_flatpaks: bool = True,
        include_settings: bool = True,
        include_repos: bool = True,
        playbook_name: str = "Loofi Fedora Configuration"
    ) -> str:
        """
        Generate an Ansible playbook from current system state.

        Args:
            include_packages: Include DNF packages
            include_flatpaks: Include Flatpak apps
            include_settings: Include GNOME/GTK settings
            include_repos: Include third-party repos
            playbook_name: Name for the playbook

        Returns:
            YAML playbook as string.
        """
        tasks = []
        vars_section: dict[str, Any] = {}

        # Header comment with disclaimer
        header = f"""---
# ╔════════════════════════════════════════════════════════════════════════════╗
# ║ GENERATED BY LOOFI FEDORA TWEAKS - REVIEW BEFORE EXECUTION                 ║
# ║                                                                            ║
# ║ ⚠️  WARNING: This playbook was auto-generated from a live system.          ║
# ║     Always review the tasks below before running on any machine.           ║
# ║     Running blindly may install unwanted packages or change settings.      ║
# ╚════════════════════════════════════════════════════════════════════════════╝
#
# {playbook_name}
# Generated by Loofi Fedora Tweaks v8.0
# Date: {datetime.now().isoformat()}
#
# Usage:
#   1. REVIEW this file carefully before proceeding
#   2. Install Ansible: sudo dnf install ansible
#   3. Run: ansible-playbook site.yml --ask-become-pass
#
# This playbook replicates your Loofi configuration on any Fedora system.

"""

        # Packages
        if include_packages:
            packages = cls._get_installed_packages()
            if packages:
                vars_section["user_packages"] = packages[:100]  # Limit to 100
                tasks.append({
                    "name": "Install user packages",
                    "become": True,
                    "ansible.builtin.dnf": {
                        "name": "{{ user_packages }}",
                        "state": "present"
                    }
                })

        # Flatpaks
        if include_flatpaks:
            flatpaks = cls._get_flatpak_apps()
            if flatpaks:
                vars_section["flatpak_apps"] = flatpaks
                tasks.append({
                    "name": "Enable Flathub",
                    "become": True,
                    "community.general.flatpak_remote": {
                        "name": "flathub",
                        "flatpakrepo_url": "https://flathub.org/repo/flathub.flatpakrepo",
                        "state": "present"
                    }
                })
                tasks.append({
                    "name": "Install Flatpak apps",
                    "become": True,
                    "community.general.flatpak": {
                        "name": "{{ item }}",
                        "state": "present"
                    },
                    "loop": "{{ flatpak_apps }}"
                })

        # GNOME Settings
        if include_settings:
            settings = cls._get_gnome_settings()
            if settings:
                vars_section["gnome_settings"] = settings
                for key, value in settings.items():
                    schema, setting = key.rsplit("/", 1)
                    tasks.append({
                        "name": f"Set {setting}",
                        "community.general.dconf": {
                            "key": f"/{schema.replace('.', '/')}/{setting}",
                            "value": f"'{value}'"
                        }
                    })

        # Build playbook structure
        playbook = [{
            "name": playbook_name,
            "hosts": "localhost",
            "connection": "local",
            "vars": vars_section,
            "tasks": tasks
        }]

        # Convert to YAML (manual formatting for readability)
        import yaml  # type: ignore[import-untyped]
        try:
            yaml_content: str = yaml.dump(playbook, default_flow_style=False, sort_keys=False,
                                     allow_unicode=True, width=120)
        except ImportError:
            # Fallback to json if yaml not available
            yaml_content = json.dumps(playbook, indent=2)

        return header + yaml_content

    @classmethod
    def save_playbook(cls, path: Optional[Path] = None, **kwargs) -> Result:
        """
        Generate and save playbook to file.

        Args:
            path: Output path (default: ~/loofi-playbook/site.yml)
            **kwargs: Arguments passed to generate_playbook

        Returns:
            Result with path to created file.
        """
        if path is None:
            playbook_dir = Path.home() / "loofi-playbook"
            playbook_dir.mkdir(exist_ok=True)
            path = playbook_dir / "site.yml"
        else:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

        try:
            content = cls.generate_playbook(**kwargs)
            with open(path, "w") as f:
                f.write(content)

            # Also create a README
            readme_path = path.parent / "README.md"
            readme = f"""# Loofi Fedora Configuration Playbook

Generated by Loofi Fedora Tweaks v8.0 on {datetime.now().strftime('%Y-%m-%d')}.

## Requirements

- Fedora (or compatible RHEL-based distro)
- Ansible (`sudo dnf install ansible`)
- community.general collection (`ansible-galaxy collection install community.general`)

## Usage

```bash
cd {path.parent}
ansible-playbook site.yml --ask-become-pass
```

## What's Included

- User-installed DNF packages
- Flatpak applications
- GNOME/GTK theme settings

## Customization

Edit `site.yml` to add or remove packages, apps, or settings before running.
"""
            with open(readme_path, "w") as f:
                f.write(readme)

            return Result(
                True,
                f"Playbook saved to: {path}",
                {"path": str(path), "readme": str(readme_path)}
            )

        except Exception as e:
            return Result(False, f"Failed to save playbook: {e}")

    @classmethod
    def validate_playbook(cls, path: Path) -> Result:
        """
        Validate a playbook with ansible-lint if available.

        Args:
            path: Path to playbook file.

        Returns:
            Result with validation output.
        """
        if not shutil.which("ansible-lint"):
            # Try basic YAML validation
            try:
                import yaml
                with open(path) as f:
                    yaml.safe_load(f)
                return Result(True, "YAML syntax is valid (ansible-lint not installed)")
            except yaml.YAMLError as e:
                return Result(False, f"YAML syntax error: {e}")
            except ImportError:
                return Result(True, "Unable to validate (yaml/ansible-lint not available)")

        try:
            result = subprocess.run(
                ["ansible-lint", str(path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return Result(True, "Playbook passed ansible-lint validation")
            else:
                return Result(False, f"Validation issues:\n{result.stdout}")

        except Exception as e:
            return Result(False, f"Validation failed: {e}")
