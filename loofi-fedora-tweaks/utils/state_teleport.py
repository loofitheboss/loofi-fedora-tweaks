"""
State Teleport - Capture and restore development workspace state across devices.
Part of v12.0 "Sovereign Update".

Captures VS Code workspace, git state, terminal state, and environment,
then serializes into a portable teleport package for restoration on another device.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from utils.containers import Result
from utils.install_hints import build_install_hint
from utils.log import get_logger

logger = get_logger(__name__)

# Environment variable name patterns that must NEVER be captured
_SECRET_PATTERNS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL")

# File name patterns that are considered credential files
_CREDENTIAL_FILES = (
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials.json", "service-account.json",
    ".netrc", ".npmrc", ".pypirc",
    "id_rsa", "id_ed25519", "id_ecdsa",
)


@dataclass
class WorkspaceState:
    """Snapshot of a development workspace."""
    workspace_id: str
    timestamp: float
    hostname: str
    vscode_workspace: dict
    git_state: dict
    terminal_state: dict
    open_files: list
    environment: dict


@dataclass
class TeleportPackage:
    """Serialized workspace ready for transfer."""
    package_id: str
    source_device: str
    target_device: str
    workspace: WorkspaceState
    created_at: float
    size_bytes: int
    checksum: str


class StateTeleportManager:
    """Captures and restores development workspace state across devices."""

    CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
    PACKAGE_DIR = CONFIG_DIR / "teleport"

    # ==================== CAPTURE ====================

    @classmethod
    def capture_vscode_state(cls, workspace_path: str = None) -> dict:  # type: ignore[assignment]
        """Capture VS Code workspace state.

        Reads .vscode/ settings, detects extensions, and collects
        open editor paths.  Falls back gracefully if VS Code is not
        installed.

        Args:
            workspace_path: Optional explicit workspace path.

        Returns:
            dict with workspace_path, extensions, settings_json,
            and open_editors keys.
        """
        state = {
            "workspace_path": workspace_path or "",
            "extensions": [],
            "settings_json": {},
            "open_editors": [],
        }

        # Resolve workspace path
        if not workspace_path:
            workspace_path = os.getcwd()
            state["workspace_path"] = workspace_path

        # Read .vscode/settings.json if present
        vscode_dir = os.path.join(workspace_path, ".vscode")
        settings_path = os.path.join(vscode_dir, "settings.json")
        if os.path.isfile(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as fh:
                    state["settings_json"] = json.load(fh)
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not parse .vscode/settings.json")

        # List installed extensions via `code --list-extensions`
        if shutil.which("code"):
            try:
                result = subprocess.run(
                    ["code", "--list-extensions"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0:
                    state["extensions"] = [
                        ext.strip()
                        for ext in result.stdout.strip().split("\n")
                        if ext.strip()
                    ]
            except (subprocess.TimeoutExpired, OSError):
                logger.warning("Failed to list VS Code extensions")

        # Detect open editors from VS Code state DB (best effort)
        # The real state DB is SQLite-based; here we just record
        # recently modified files as a lightweight proxy.
        try:
            recent = []
            for entry in os.listdir(workspace_path):
                full = os.path.join(workspace_path, entry)
                if os.path.isfile(full) and not entry.startswith("."):
                    recent.append(entry)
            state["open_editors"] = sorted(recent)[:20]
        except OSError:
            pass

        return state

    @classmethod
    def capture_git_state(cls, repo_path: str) -> dict:
        """Capture git repository state.

        Args:
            repo_path: Path to the git repository root.

        Returns:
            dict with branch, remote_url, status, last_commit_hash,
            stash_count, and unpushed_count.
        """
        state = {
            "branch": "",
            "remote_url": "",
            "status": "unknown",
            "last_commit_hash": "",
            "stash_count": 0,
            "unpushed_count": 0,
        }

        if not shutil.which("git"):
            return state

        def _git(*args: str) -> Optional[str]:
            try:
                result = subprocess.run(
                    ["git", "-C", repo_path] + list(args),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, OSError):
                pass
            return None

        # Current branch
        branch = _git("rev-parse", "--abbrev-ref", "HEAD")
        if branch:
            state["branch"] = branch

        # Remote URL (origin)
        remote = _git("remote", "get-url", "origin")
        if remote:
            state["remote_url"] = remote

        # Working tree status
        status_output = _git("status", "--porcelain")
        if status_output is not None:
            state["status"] = "dirty" if status_output else "clean"

        # Last commit hash
        commit_hash = _git("rev-parse", "HEAD")
        if commit_hash:
            state["last_commit_hash"] = commit_hash

        # Stash count
        stash_list = _git("stash", "list")
        if stash_list:
            state["stash_count"] = len(stash_list.strip().split("\n"))

        # Unpushed commits
        if state["branch"]:
            unpushed = _git(
                "rev-list", "--count",
                f"origin/{state['branch']}..HEAD",
            )
            if unpushed and unpushed.isdigit():
                state["unpushed_count"] = int(unpushed)

        return state

    @classmethod
    def capture_terminal_state(cls) -> dict:
        """Capture current terminal / shell state.

        Returns:
            dict with cwd, shell, and recent_history (last 20 commands).
        """
        state = {
            "cwd": os.getcwd(),
            "shell": "",
            "recent_history": [],
        }

        # Detect shell
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            state["shell"] = "zsh"
            history_file = os.path.expanduser("~/.zsh_history")
        elif "fish" in shell:
            state["shell"] = "fish"
            history_file = os.path.expanduser(
                "~/.local/share/fish/fish_history"
            )
        else:
            state["shell"] = "bash"
            history_file = os.path.expanduser("~/.bash_history")

        # Read last 20 history entries
        if os.path.isfile(history_file):
            try:
                with open(history_file, "r", encoding="utf-8",
                          errors="replace") as fh:
                    lines = fh.readlines()
                # Get last 20 non-empty lines
                history = [
                    line.strip() for line in lines if line.strip()
                ][-20:]
                state["recent_history"] = history
            except OSError:
                logger.warning("Could not read shell history file")

        return state

    @classmethod
    def _filter_environment(cls) -> dict:
        """Capture safe environment variables.

        Filters out PATH and any variable whose name contains
        secret-related keywords.
        """
        safe_env = {}
        for key, value in os.environ.items():
            if key == "PATH":
                continue
            if any(pat in key.upper() for pat in _SECRET_PATTERNS):
                continue
            safe_env[key] = value
        return safe_env

    @classmethod
    def _filter_open_files(cls, files: list) -> list:
        """Remove credential / secret files from an open files list."""
        filtered = []
        for filepath in files:
            basename = os.path.basename(filepath)
            if basename.lower() in (cf.lower() for cf in _CREDENTIAL_FILES):
                continue
            # Also skip dotenv variants
            if basename.startswith(".env"):
                continue
            filtered.append(filepath)
        return filtered

    @classmethod
    def capture_full_state(cls, workspace_path: str = None) -> WorkspaceState:  # type: ignore[assignment]
        """Capture a full workspace snapshot combining all sub-captures.

        Args:
            workspace_path: Optional workspace root. Defaults to CWD.

        Returns:
            A complete WorkspaceState dataclass instance.
        """
        ws_path = workspace_path or os.getcwd()

        vscode_state = cls.capture_vscode_state(ws_path)
        git_state = cls.capture_git_state(ws_path)
        terminal_state = cls.capture_terminal_state()
        environment = cls._filter_environment()

        # Collect open files from VS Code editors
        open_files = [
            os.path.join(ws_path, f)
            for f in vscode_state.get("open_editors", [])
        ]
        open_files = cls._filter_open_files(open_files)

        return WorkspaceState(
            workspace_id=str(uuid.uuid4()),
            timestamp=time.time(),
            hostname=platform.node(),
            vscode_workspace=vscode_state,
            git_state=git_state,
            terminal_state=terminal_state,
            open_files=open_files,
            environment=environment,
        )

    # ==================== SERIALIZATION ====================

    @classmethod
    def serialize_state(cls, state: WorkspaceState) -> bytes:
        """Serialize a WorkspaceState to UTF-8 JSON bytes.

        Args:
            state: The workspace state to serialize.

        Returns:
            UTF-8 encoded JSON bytes.
        """
        data = asdict(state)
        return json.dumps(data, indent=2, default=str).encode("utf-8")

    @classmethod
    def deserialize_state(cls, data: bytes) -> WorkspaceState:
        """Deserialize bytes back to a WorkspaceState.

        Args:
            data: UTF-8 JSON bytes.

        Returns:
            Reconstructed WorkspaceState instance.

        Raises:
            ValueError: If the data is corrupt or missing required fields.
        """
        try:
            raw = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"Corrupt teleport data: {exc}") from exc

        required = {
            "workspace_id", "timestamp", "hostname",
            "vscode_workspace", "git_state", "terminal_state",
            "open_files", "environment",
        }
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"Missing fields in teleport data: {missing}")

        return WorkspaceState(
            workspace_id=raw["workspace_id"],
            timestamp=float(raw["timestamp"]),
            hostname=raw["hostname"],
            vscode_workspace=raw["vscode_workspace"],
            git_state=raw["git_state"],
            terminal_state=raw["terminal_state"],
            open_files=raw["open_files"],
            environment=raw["environment"],
        )

    @classmethod
    def create_teleport_package(
        cls,
        state: WorkspaceState,
        target_device: str,
    ) -> TeleportPackage:
        """Create a TeleportPackage from a WorkspaceState.

        Args:
            state: Captured workspace state.
            target_device: Name/identifier of the target device.

        Returns:
            A TeleportPackage ready for transfer.
        """
        serialized = cls.serialize_state(state)
        checksum = hashlib.sha256(serialized).hexdigest()

        return TeleportPackage(
            package_id=str(uuid.uuid4()),
            source_device=state.hostname,
            target_device=target_device,
            workspace=state,
            created_at=time.time(),
            size_bytes=len(serialized),
            checksum=checksum,
        )

    # ==================== RESTORE ====================

    @classmethod
    def restore_vscode_state(cls, vscode_state: dict) -> Result:
        """Restore VS Code workspace state.

        Opens VS Code at the captured workspace path.

        Args:
            vscode_state: The vscode_workspace dict from a WorkspaceState.

        Returns:
            Result indicating success or failure.
        """
        ws_path = vscode_state.get("workspace_path", "")
        if not ws_path:
            return Result(False, "No workspace path in VS Code state.")

        if not shutil.which("code"):
            return Result(
                False,
                f"VS Code is not installed. {build_install_hint('code')}",
            )

        try:
            subprocess.run(
                ["code", ws_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return Result(
                True,
                f"VS Code opened at {ws_path}",
                data={"workspace_path": ws_path},
            )
        except subprocess.TimeoutExpired:
            return Result(False, "Timed out opening VS Code.")
        except OSError as exc:
            return Result(False, f"Failed to open VS Code: {exc}")

    @classmethod
    def restore_git_state(cls, git_state: dict, repo_path: str) -> Result:
        """Restore git state by checking out the captured branch.

        Warns if there are local changes rather than forcing.

        Args:
            git_state: The git_state dict from a WorkspaceState.
            repo_path: Path to the local repository.

        Returns:
            Result indicating success or failure.
        """
        branch = git_state.get("branch", "")
        if not branch:
            return Result(False, "No branch information in git state.")

        if not shutil.which("git"):
            return Result(False, "Git is not installed.")

        # Check for local changes first
        try:
            status_result = subprocess.run(
                ["git", "-C", repo_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if status_result.returncode == 0 and status_result.stdout.strip():
                return Result(
                    False,
                    f"Local changes detected in {repo_path}. "
                    "Please commit or stash before restoring git state.",
                    data={"dirty": True, "branch": branch},
                )
        except (subprocess.TimeoutExpired, OSError):
            pass

        # Checkout the target branch
        try:
            checkout = subprocess.run(
                ["git", "-C", repo_path, "checkout", branch],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if checkout.returncode == 0:
                return Result(
                    True,
                    f"Checked out branch '{branch}' in {repo_path}",
                    data={"branch": branch},
                )
            else:
                error = checkout.stderr.strip() or checkout.stdout.strip()
                return Result(
                    False,
                    f"Failed to checkout branch '{branch}': {error}",
                )
        except subprocess.TimeoutExpired:
            return Result(False, "Git checkout timed out.")
        except OSError as exc:
            return Result(False, f"Git checkout failed: {exc}")

    @classmethod
    def apply_teleport(cls, package: TeleportPackage) -> Result:
        """Apply a full teleport: restore git state, open VS Code.

        Args:
            package: The TeleportPackage to apply.

        Returns:
            Result indicating overall success or failure.
        """
        workspace = package.workspace
        messages = []
        overall_success = True

        # Restore git state
        ws_path = workspace.vscode_workspace.get("workspace_path", "")
        if ws_path and workspace.git_state.get("branch"):
            git_result = cls.restore_git_state(
                workspace.git_state, ws_path
            )
            messages.append(git_result.message)
            if not git_result.success:
                overall_success = False

        # Restore VS Code state
        if workspace.vscode_workspace.get("workspace_path"):
            vscode_result = cls.restore_vscode_state(
                workspace.vscode_workspace
            )
            messages.append(vscode_result.message)
            if not vscode_result.success:
                overall_success = False

        summary = "; ".join(messages) if messages else "Nothing to restore."
        return Result(overall_success, summary)

    # ==================== FILE I/O ====================

    @classmethod
    def get_package_dir(cls) -> str:
        """Return the teleport package storage directory.

        Creates the directory if it does not exist.

        Returns:
            Absolute path string to the teleport directory.
        """
        cls.PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
        return str(cls.PACKAGE_DIR)

    @classmethod
    def save_package_to_file(
        cls,
        package: TeleportPackage,
        path: str,
    ) -> Result:
        """Save a TeleportPackage to a JSON file.

        Args:
            package: The package to save.
            path: Destination file path.

        Returns:
            Result indicating success or failure.
        """
        try:
            data = {
                "package_id": package.package_id,
                "source_device": package.source_device,
                "target_device": package.target_device,
                "workspace": asdict(package.workspace),
                "created_at": package.created_at,
                "size_bytes": package.size_bytes,
                "checksum": package.checksum,
            }
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            return Result(True, f"Package saved to {path}")
        except OSError as exc:
            return Result(False, f"Failed to save package: {exc}")

    @classmethod
    def load_package_from_file(cls, path: str) -> TeleportPackage:
        """Load a TeleportPackage from a JSON file.

        Args:
            path: Source file path.

        Returns:
            Reconstructed TeleportPackage.

        Raises:
            ValueError: If the file is corrupt or missing required data.
            FileNotFoundError: If the file doesn't exist.
        """
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        required = {
            "package_id", "source_device", "target_device",
            "workspace", "created_at", "size_bytes", "checksum",
        }
        missing = required - set(raw.keys())
        if missing:
            raise ValueError(f"Missing fields in package file: {missing}")

        ws_raw = raw["workspace"]
        workspace = WorkspaceState(
            workspace_id=ws_raw["workspace_id"],
            timestamp=float(ws_raw["timestamp"]),
            hostname=ws_raw["hostname"],
            vscode_workspace=ws_raw["vscode_workspace"],
            git_state=ws_raw["git_state"],
            terminal_state=ws_raw["terminal_state"],
            open_files=ws_raw["open_files"],
            environment=ws_raw["environment"],
        )

        return TeleportPackage(
            package_id=raw["package_id"],
            source_device=raw["source_device"],
            target_device=raw["target_device"],
            workspace=workspace,
            created_at=float(raw["created_at"]),
            size_bytes=int(raw["size_bytes"]),
            checksum=raw["checksum"],
        )

    @classmethod
    def list_saved_packages(cls) -> list:
        """List saved teleport packages (metadata only).

        Returns:
            List of dicts with package_id, source_device, target_device,
            created_at, and size_bytes.  Does not include full workspace data.
        """
        pkg_dir = cls.get_package_dir()
        packages = []

        for filename in os.listdir(pkg_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(pkg_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                packages.append({
                    "package_id": raw.get("package_id", ""),
                    "source_device": raw.get("source_device", ""),
                    "target_device": raw.get("target_device", ""),
                    "created_at": raw.get("created_at", 0),
                    "size_bytes": raw.get("size_bytes", 0),
                    "filename": filename,
                })
            except (json.JSONDecodeError, OSError):
                logger.warning("Skipping corrupt package file: %s", filename)

        return packages
