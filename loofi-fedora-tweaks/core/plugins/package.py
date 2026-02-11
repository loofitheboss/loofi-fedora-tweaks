"""
core.plugins.package — .loofi-plugin archive format specification.

Defines the structure for external plugin distribution via signed,
versioned archives (.loofi-plugin files).

Archive Format:
    File extension: .loofi-plugin
    Compression: tar.gz
    Structure:
        my-plugin-1.0.0.loofi-plugin (tar.gz)
        ├── plugin.json          # Manifest (required)
        ├── plugin.py            # Entry point (required)
        ├── requirements.txt     # Python dependencies (optional)
        ├── assets/              # Icons, images, etc. (optional)
        ├── CHECKSUMS.sha256     # SHA256 checksums of all files (required)
        └── SIGNATURE.asc        # GPG signature of CHECKSUMS (optional)

Manifest Schema (plugin.json):
    {
        "id": "my-plugin",               # Unique identifier (slug)
        "name": "My Plugin",             # Display name
        "version": "1.0.0",              # Semantic version
        "description": "...",            # Short description
        "author": "Author Name",         # Plugin author
        "author_email": "...",           # Contact (optional)
        "license": "MIT",                # License (optional)
        "homepage": "https://...",       # Project homepage (optional)
        "permissions": ["network"],      # Requested permissions
        "requires": ["other>=2.0"],      # Plugin dependencies (optional)
        "min_app_version": "25.0.0",     # Minimum Loofi version
        "entry_point": "plugin.py",      # Python module to load
        "icon": "🔌",                    # Unicode emoji or path
        "category": "System",            # Sidebar category (optional)
        "order": 500                     # Sort order (optional)
    }

Permissions:
    - network: Internet access
    - filesystem: Read/write user files
    - sudo: Privileged operations (requires user approval)
    - clipboard: Access system clipboard
    - notifications: Send desktop notifications

Security:
    - CHECKSUMS.sha256: Contains SHA256 hash of every file in archive
    - SIGNATURE.asc: Optional GPG signature of CHECKSUMS file
    - Archive verification happens before extraction
    - Untrusted plugins run in restricted sandbox (future)

Usage:
    from core.plugins.package import PluginPackage, PluginManifest
    
    # Parse manifest from JSON
    manifest = PluginManifest.from_json(json_str)
    
    # Load package from archive file
    package = PluginPackage.from_file("my-plugin-1.0.0.loofi-plugin")
    print(package.manifest.name)
    
    # Create new package (for plugin authors)
    package = PluginPackage.create(
        manifest=manifest,
        plugin_code=plugin_py_content,
        assets={"icon.png": icon_bytes}
    )
    package.save("output.loofi-plugin")
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json
import hashlib
import tarfile
import io

from utils.log import get_logger

logger = get_logger(__name__)


# Valid permission types
VALID_PERMISSIONS = {
    "network",       # Internet access
    "filesystem",    # Read/write user files
    "sudo",          # Privileged operations (pkexec)
    "clipboard",     # System clipboard access
    "notifications", # Desktop notifications
}


@dataclass
class PluginManifest:
    """
    Plugin manifest data (parsed from plugin.json).
    
    Attributes:
        id: Unique plugin identifier (slug, alphanumeric + hyphens)
        name: Human-readable display name
        version: Semantic version string (e.g., "1.0.0")
        description: Brief description (max 200 chars recommended)
        author: Author name
        entry_point: Python module filename (e.g., "plugin.py")
        icon: Unicode emoji or asset path (default: 🔌)
        permissions: List of requested permissions
        requires: List of plugin dependencies (format: "id>=version")
        min_app_version: Minimum required Loofi version
        author_email: Author contact email (optional)
        license: License identifier (e.g., "MIT", "GPL-3.0")
        homepage: Project homepage URL
        category: Sidebar category (e.g., "System", "Community")
        order: Sort order within category (default: 500 for external)
    """
    
    id: str
    name: str
    version: str
    description: str
    author: str
    entry_point: str = "plugin.py"
    icon: str = "🔌"
    permissions: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    min_app_version: str = "25.0.0"
    author_email: str = ""
    license: str = ""
    homepage: str = ""
    category: str = "Community"
    order: int = 500
    
    def __post_init__(self):
        """Validate manifest fields after initialization."""
        # Validate ID (alphanumeric + hyphens only)
        if not self.id or not all(c.isalnum() or c == "-" for c in self.id):
            raise ValueError(
                f"Invalid plugin ID '{self.id}': must contain only "
                "alphanumeric characters and hyphens"
            )
        
        # Validate version (basic semver check)
        if not self.version or not self._is_valid_semver(self.version):
            raise ValueError(
                f"Invalid version '{self.version}': must be semantic version "
                "(e.g., '1.0.0')"
            )
        
        # Validate permissions
        invalid_perms = set(self.permissions) - VALID_PERMISSIONS
        if invalid_perms:
            raise ValueError(
                f"Invalid permissions {invalid_perms}: must be one of "
                f"{VALID_PERMISSIONS}"
            )
        
        # Validate entry point
        if not self.entry_point.endswith(".py"):
            raise ValueError(
                f"Invalid entry_point '{self.entry_point}': must be a .py file"
            )
    
    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        """Check if version string is valid semantic version."""
        parts = version.split(".")
        if len(parts) < 2 or len(parts) > 3:
            return False
        try:
            for part in parts:
                int(part)  # Must be numeric
            return True
        except ValueError:
            return False
    
    @classmethod
    def from_json(cls, json_str: str) -> "PluginManifest":
        """
        Parse manifest from JSON string.
        
        Args:
            json_str: JSON content of plugin.json
        
        Returns:
            PluginManifest instance
        
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in plugin.json: {e}") from e
        
        # Check required fields
        required = {"id", "name", "version", "description", "author"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields in plugin.json: {missing}")
        
        # Build manifest with defaults for optional fields
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            entry_point=data.get("entry_point", "plugin.py"),
            icon=data.get("icon", "🔌"),
            permissions=data.get("permissions", []),
            requires=data.get("requires", []),
            min_app_version=data.get("min_app_version", "25.0.0"),
            author_email=data.get("author_email", ""),
            license=data.get("license", ""),
            homepage=data.get("homepage", ""),
            category=data.get("category", "Community"),
            order=data.get("order", 500),
        )
    
    def to_json(self) -> str:
        """
        Serialize manifest to JSON string.
        
        Returns:
            Pretty-printed JSON string
        """
        data = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "entry_point": self.entry_point,
            "icon": self.icon,
            "permissions": self.permissions,
            "requires": self.requires,
            "min_app_version": self.min_app_version,
        }
        
        # Add optional fields if present
        if self.author_email:
            data["author_email"] = self.author_email
        if self.license:
            data["license"] = self.license
        if self.homepage:
            data["homepage"] = self.homepage
        if self.category != "Community":
            data["category"] = self.category
        if self.order != 500:
            data["order"] = self.order
        
        return json.dumps(data, indent=2)


@dataclass
class PluginPackage:
    """
    Represents a .loofi-plugin archive file.
    
    Attributes:
        manifest: Parsed plugin manifest
        archive_path: Path to the .loofi-plugin file (if loaded from disk)
        files: Dict mapping filename → file content bytes
        checksums: SHA256 checksums of all files
        signature: GPG signature of CHECKSUMS file (optional)
    """
    
    manifest: PluginManifest
    archive_path: Path | None = None
    files: dict[str, bytes] = field(default_factory=dict)
    checksums: dict[str, str] = field(default_factory=dict)
    signature: str = ""
    
    @classmethod
    def from_file(cls, path: str | Path) -> "PluginPackage":
        """
        Load plugin package from .loofi-plugin archive file.
        
        Args:
            path: Path to .loofi-plugin file
        
        Returns:
            PluginPackage instance
        
        Raises:
            FileNotFoundError: If archive file doesn't exist
            ValueError: If archive is invalid or corrupted
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Plugin archive not found: {path}")
        
        if not path.name.endswith(".loofi-plugin"):
            logger.warning(
                f"Archive '{path.name}' doesn't have .loofi-plugin extension"
            )
        
        files: dict[str, bytes] = {}
        
        try:
            with tarfile.open(path, "r:gz") as tar:
                # Extract all files
                for member in tar.getmembers():
                    if member.isfile():
                        extracted = tar.extractfile(member)
                        if extracted:
                            files[member.name] = extracted.read()
        except (tarfile.TarError, OSError) as e:
            raise ValueError(f"Failed to extract archive: {e}") from e
        
        # Verify required files
        if "plugin.json" not in files:
            raise ValueError("Archive missing required file: plugin.json")
        
        # Parse manifest
        try:
            manifest = PluginManifest.from_json(files["plugin.json"].decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid plugin.json: {e}") from e
        
        # Verify entry point exists
        if manifest.entry_point not in files:
            raise ValueError(
                f"Archive missing entry point file: {manifest.entry_point}"
            )
        
        # Load checksums if present
        checksums: dict[str, str] = {}
        if "CHECKSUMS.sha256" in files:
            checksums = cls._parse_checksums(files["CHECKSUMS.sha256"])
        
        # Load signature if present
        signature = ""
        if "SIGNATURE.asc" in files:
            signature = files["SIGNATURE.asc"].decode("utf-8")
        
        return cls(
            manifest=manifest,
            archive_path=path,
            files=files,
            checksums=checksums,
            signature=signature,
        )
    
    @classmethod
    def create(
        cls,
        manifest: PluginManifest,
        plugin_code: str,
        assets: dict[str, bytes] | None = None,
    ) -> "PluginPackage":
        """
        Create a new plugin package (for plugin authors).
        
        Args:
            manifest: Plugin manifest
            plugin_code: Python source code for entry point
            assets: Optional dict of asset filename → bytes
        
        Returns:
            PluginPackage ready to be saved
        """
        files: dict[str, bytes] = {}
        
        # Add manifest
        files["plugin.json"] = manifest.to_json().encode("utf-8")
        
        # Add plugin code
        files[manifest.entry_point] = plugin_code.encode("utf-8")
        
        # Add assets
        if assets:
            for filename, content in assets.items():
                if "/" in filename:  # Support subdirs like "assets/icon.png"
                    files[filename] = content
                else:
                    files[f"assets/{filename}"] = content
        
        # Compute checksums
        checksums = cls._compute_checksums(files)
        files["CHECKSUMS.sha256"] = cls._format_checksums(checksums).encode("utf-8")
        
        return cls(
            manifest=manifest,
            files=files,
            checksums=checksums,
        )
    
    def save(self, path: str | Path) -> None:
        """
        Save package to .loofi-plugin archive file.
        
        Args:
            path: Output path (will add .loofi-plugin extension if missing)
        
        Raises:
            OSError: If file cannot be written
        """
        path = Path(path)
        if not path.name.endswith(".loofi-plugin"):
            path = path.with_suffix(".loofi-plugin")
        
        try:
            with tarfile.open(path, "w:gz") as tar:
                for filename, content in self.files.items():
                    # Create TarInfo
                    info = tarfile.TarInfo(name=filename)
                    info.size = len(content)
                    
                    # Add to archive
                    tar.addfile(info, io.BytesIO(content))
            
            logger.info(f"Saved plugin package to {path}")
        except (tarfile.TarError, OSError) as e:
            raise OSError(f"Failed to save package: {e}") from e
    
    def verify(self) -> bool:
        """
        Verify package integrity by checking SHA256 checksums.
        
        Returns:
            True if all checksums match, False otherwise
        """
        if not self.checksums:
            logger.warning("No checksums found, skipping verification")
            return True
        
        for filename, expected_hash in self.checksums.items():
            if filename not in self.files:
                logger.error(f"File {filename} in checksums but not in archive")
                return False
            
            actual_hash = hashlib.sha256(self.files[filename]).hexdigest()
            if actual_hash != expected_hash:
                logger.error(
                    f"Checksum mismatch for {filename}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )
                return False
        
        logger.info("Package verification successful")
        return True
    
    @staticmethod
    def _compute_checksums(files: dict[str, bytes]) -> dict[str, str]:
        """Compute SHA256 checksums for all files."""
        checksums = {}
        for filename, content in files.items():
            if filename != "CHECKSUMS.sha256" and filename != "SIGNATURE.asc":
                checksums[filename] = hashlib.sha256(content).hexdigest()
        return checksums
    
    @staticmethod
    def _format_checksums(checksums: dict[str, str]) -> str:
        """Format checksums as text (sha256sum format)."""
        lines = []
        for filename in sorted(checksums.keys()):
            lines.append(f"{checksums[filename]}  {filename}")
        return "\n".join(lines) + "\n"
    
    @staticmethod
    def _parse_checksums(content: bytes) -> dict[str, str]:
        """Parse CHECKSUMS.sha256 file content."""
        checksums = {}
        for line in content.decode("utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                hash_val, filename = parts
                checksums[filename] = hash_val
        return checksums
