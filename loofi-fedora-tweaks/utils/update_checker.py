"""
App update checker - fetches latest release from GitHub API.
Part of v14.0 "Horizon Update".
"""
import hashlib
import json
import logging
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

GITHUB_REPO = "loofitheboss/loofi-fedora-tweaks"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

ERR_NO_UPDATE = "no_update_available"
ERR_NO_ASSET = "no_supported_asset"
ERR_DOWNLOAD_FAILED = "download_failed"
ERR_CHECKSUM_MISMATCH = "checksum_mismatch"
ERR_SIGNATURE_FAILED = "signature_verification_failed"
ERR_NETWORK = "network_unavailable"


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    release_notes: str
    download_url: str
    is_newer: bool
    assets: List["UpdateAsset"] = field(default_factory=list)
    selected_asset: Optional["UpdateAsset"] = None
    offline: bool = False
    source: str = "network"


@dataclass
class UpdateAsset:
    """Downloadable release asset metadata."""
    name: str
    download_url: str
    size: int = 0
    content_type: str = ""
    checksum_sha256: str = ""
    signature_url: Optional[str] = None


@dataclass
class VerifyResult:
    """Result of artifact verification."""
    ok: bool
    method: str
    error: Optional[str] = None


@dataclass
class DownloadResult:
    """Result of downloading an update asset."""
    ok: bool
    file_path: Optional[str] = None
    bytes_written: int = 0
    error: Optional[str] = None


@dataclass
class AutoUpdateResult:
    """Result of end-to-end update orchestration."""
    success: bool
    stage: str
    update_info: Optional[UpdateInfo] = None
    selected_asset: Optional[UpdateAsset] = None
    download: Optional[DownloadResult] = None
    verify: Optional[VerifyResult] = None
    offline: bool = False
    source: str = "network"
    error: Optional[str] = None


class UpdateChecker:
    """Check for application updates via GitHub releases API."""

    _cached_info: Optional[UpdateInfo] = None

    @staticmethod
    def parse_version(version_str: str) -> Tuple[int, ...]:
        """Parse a version string like '14.0.0' into a tuple of ints."""
        try:
            return tuple(int(p) for p in version_str.strip().lstrip("v").split("."))
        except (ValueError, AttributeError):
            return (0, 0, 0)

    @staticmethod
    def check_for_updates(timeout: int = 10, use_cache: bool = True) -> Optional[UpdateInfo]:
        """
        Check GitHub for the latest release.

        Returns UpdateInfo if check succeeds, None on failure.
        """
        from version import __version__

        try:
            req = urllib.request.Request(
                RELEASES_URL,
                headers={"Accept": "application/vnd.github.v3+json",
                         "User-Agent": "loofi-fedora-tweaks"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            latest_tag = data.get("tag_name", "")
            latest_version = latest_tag.lstrip("v")
            release_notes = data.get("body", "")
            html_url = data.get("html_url", "")
            assets = [
                UpdateAsset(
                    name=str(asset.get("name", "") or ""),
                    download_url=str(
                        asset.get("browser_download_url", "") or ""),
                    size=int(asset.get("size", 0) or 0),
                    content_type=str(asset.get("content_type", "") or ""),
                )
                for asset in (data.get("assets") or [])
                if asset.get("browser_download_url")
            ]
            selected_asset = UpdateChecker.select_download_asset(assets)

            current_tuple = UpdateChecker.parse_version(__version__)
            latest_tuple = UpdateChecker.parse_version(latest_version)

            info = UpdateInfo(
                current_version=__version__,
                latest_version=latest_version,
                release_notes=release_notes,
                download_url=html_url,
                is_newer=latest_tuple > current_tuple,
                assets=assets,
                selected_asset=selected_asset,
                offline=False,
                source="network",
            )
            if use_cache:
                UpdateChecker._cached_info = info
            return info

        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                OSError, KeyError, ValueError) as exc:
            logger.debug("Update check failed: %s", exc)
            if use_cache and UpdateChecker._cached_info is not None:
                cached = UpdateChecker._cached_info
                return UpdateInfo(
                    current_version=cached.current_version,
                    latest_version=cached.latest_version,
                    release_notes=cached.release_notes,
                    download_url=cached.download_url,
                    is_newer=cached.is_newer,
                    assets=list(cached.assets),
                    selected_asset=cached.selected_asset,
                    offline=True,
                    source="cache",
                )
            return None

    @staticmethod
    def select_download_asset(
        assets: List[UpdateAsset],
        preferred_ext: Tuple[str, ...] = (
            ".rpm", ".flatpak", ".AppImage", ".tar.gz"),
    ) -> Optional[UpdateAsset]:
        """Select a preferred asset based on extension ordering."""
        if not assets:
            return None

        lowered = tuple(ext.lower() for ext in preferred_ext)
        for ext in lowered:
            for asset in assets:
                if asset.name.lower().endswith(ext):
                    return asset
        return assets[0]

    @staticmethod
    def resolve_artifact_preference(
        package_manager: str,
        explicit_channel: str = "auto",
    ) -> Tuple[str, ...]:
        """Resolve asset extension preference order for current system/update channel."""
        default_dnf = (".rpm", ".flatpak", ".AppImage", ".tar.gz")
        default_ostree = (".flatpak", ".AppImage", ".rpm", ".tar.gz")

        if explicit_channel == "rpm":
            return default_dnf
        if explicit_channel == "flatpak":
            return (".flatpak", ".rpm", ".AppImage", ".tar.gz")
        if explicit_channel == "appimage":
            return (".AppImage", ".flatpak", ".rpm", ".tar.gz")

        return default_ostree if package_manager == "rpm-ostree" else default_dnf

    @staticmethod
    def run_auto_update(
        artifact_preference: Tuple[str, ...],
        target_dir: str,
        timeout: int = 30,
        use_cache: bool = True,
        expected_sha256: str = "",
        signature_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
    ) -> AutoUpdateResult:
        """Run full update flow: check, select, download, verify."""
        info = UpdateChecker.check_for_updates(
            timeout=timeout, use_cache=use_cache)
        if info is None:
            return AutoUpdateResult(success=False, stage="check", error=ERR_NETWORK, offline=True, source="network")

        base_result: dict[str, Any] = {
            "update_info": info,
            "offline": info.offline,
            "source": info.source,
        }

        if not info.is_newer:
            return AutoUpdateResult(success=False, stage="check", error=ERR_NO_UPDATE, **base_result)

        selected_asset = UpdateChecker.select_download_asset(
            info.assets, preferred_ext=artifact_preference)
        if selected_asset is None:
            return AutoUpdateResult(success=False, stage="select", error=ERR_NO_ASSET, **base_result)

        download_result = UpdateChecker.download_update(
            selected_asset, target_dir, timeout=timeout)
        if not download_result.ok or not download_result.file_path:
            return AutoUpdateResult(
                success=False,
                stage="download",
                selected_asset=selected_asset,
                download=download_result,
                error=ERR_DOWNLOAD_FAILED,
                **base_result,
            )

        verify_result = UpdateChecker.verify_download(
            file_path=download_result.file_path,
            expected_sha256=expected_sha256,
            signature_path=signature_path,
            public_key_path=public_key_path,
        )
        if not verify_result.ok:
            if verify_result.method == "sha256":
                mapped_error = ERR_CHECKSUM_MISMATCH
            elif verify_result.method == "signature":
                mapped_error = ERR_SIGNATURE_FAILED
            else:
                mapped_error = verify_result.error or ERR_SIGNATURE_FAILED

            return AutoUpdateResult(
                success=False,
                stage="verify",
                selected_asset=selected_asset,
                download=download_result,
                verify=verify_result,
                error=mapped_error,
                **base_result,
            )

        return AutoUpdateResult(
            success=True,
            stage="complete",
            selected_asset=selected_asset,
            download=download_result,
            verify=verify_result,
            error=None,
            **base_result,
        )

    @staticmethod
    def download_update(asset: UpdateAsset, target_dir: str, timeout: int = 30) -> DownloadResult:
        """Download a release asset to target directory."""
        try:
            os.makedirs(target_dir, exist_ok=True)
            destination = Path(target_dir) / asset.name
            req = urllib.request.Request(
                asset.download_url,
                headers={"User-Agent": "loofi-fedora-tweaks"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            destination.write_bytes(data)
            return DownloadResult(ok=True, file_path=str(destination), bytes_written=len(data))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            return DownloadResult(ok=False, error=str(exc))

    @staticmethod
    def verify_download(
        file_path: str,
        expected_sha256: str = "",
        signature_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
    ) -> VerifyResult:
        """Verify downloaded artifact checksum and optional signature."""
        if not os.path.exists(file_path):
            return VerifyResult(ok=False, method="none", error="Downloaded file does not exist")

        method = "none"
        if expected_sha256:
            method = "sha256"
            digest = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
            if digest.lower() != expected_sha256.lower():
                return VerifyResult(ok=False, method=method, error="SHA256 checksum mismatch")

        if signature_path or public_key_path:
            method = "signature"
            if not signature_path or not os.path.exists(signature_path):
                return VerifyResult(ok=False, method=method, error="Missing signature file")
            if public_key_path and not os.path.exists(public_key_path):
                return VerifyResult(ok=False, method=method, error="Missing public key file")

            command = ["gpg", "--verify", signature_path, file_path]
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, check=False)
            except OSError as exc:
                return VerifyResult(ok=False, method=method, error=f"Signature verification failed: {exc}")

            if result.returncode != 0:
                error_text = result.stderr.strip() or "Signature verification failed"
                return VerifyResult(ok=False, method=method, error=error_text)

        return VerifyResult(ok=True, method=method)
