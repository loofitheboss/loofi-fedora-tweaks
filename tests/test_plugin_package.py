"""Tests for core/plugins/package.py — PluginManifest and PluginPackage.

Covers manifest validation, from_json, to_json, PluginPackage.create,
save, from_file, verify, and checksum helpers.
"""

import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from core.plugins.package import PluginManifest, PluginPackage

# ── Helpers ────────────────────────────────────────────────────────

def _valid_manifest_kwargs(**overrides):
    """Return kwargs for a valid PluginManifest."""
    base = dict(
        id="test-plugin",
        name="Test Plugin",
        version="1.0.0",
        description="A test plugin",
        author="Test Author",
        entry_point="plugin.py",
    )
    base.update(overrides)
    return base


def _valid_json(**overrides):
    """Return valid manifest JSON string."""
    base = {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "Test Author",
    }
    base.update(overrides)
    return json.dumps(base)


# ── PluginManifest validation ──────────────────────────────────────

class TestPluginManifestValidation(unittest.TestCase):

    def test_valid_manifest(self):
        m = PluginManifest(**_valid_manifest_kwargs())
        self.assertEqual(m.id, "test-plugin")
        self.assertEqual(m.version, "1.0.0")  # fixture-version

    def test_invalid_id_empty(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(id=""))

    def test_invalid_id_special_chars(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(id="test@plugin!"))

    def test_invalid_id_spaces(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(id="test plugin"))

    def test_invalid_version_empty(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(version=""))

    def test_invalid_version_not_semver(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(version="abc"))

    def test_invalid_version_single_number(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(version="1"))

    def test_valid_version_two_parts(self):
        m = PluginManifest(**_valid_manifest_kwargs(version="1.0"))
        self.assertEqual(m.version, "1.0")

    def test_valid_version_three_parts(self):
        m = PluginManifest(**_valid_manifest_kwargs(version="2.3.4"))
        self.assertEqual(m.version, "2.3.4")

    def test_invalid_version_four_parts(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(version="1.2.3.4"))

    def test_invalid_permissions(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(permissions=["invalid-perm"]))

    def test_valid_permissions(self):
        m = PluginManifest(**_valid_manifest_kwargs(
            permissions=["network", "filesystem", "clipboard"]
        ))
        self.assertEqual(len(m.permissions), 3)

    def test_invalid_entry_point(self):
        with self.assertRaises(ValueError):
            PluginManifest(**_valid_manifest_kwargs(entry_point="plugin.js"))

    def test_valid_entry_point_subdir(self):
        m = PluginManifest(**_valid_manifest_kwargs(entry_point="src/main.py"))
        self.assertEqual(m.entry_point, "src/main.py")


# ── PluginManifest.from_json ──────────────────────────────────────

class TestPluginManifestFromJson(unittest.TestCase):

    def test_valid_json(self):
        m = PluginManifest.from_json(_valid_json())
        self.assertEqual(m.id, "test-plugin")
        self.assertEqual(m.name, "Test Plugin")

    def test_with_optional_fields(self):
        m = PluginManifest.from_json(_valid_json(
            author_email="test@example.com",
            license="MIT",
            homepage="https://example.com",
            category="System",
            order=100,
            permissions=["network"],
        ))
        self.assertEqual(m.author_email, "test@example.com")
        self.assertEqual(m.license, "MIT")
        self.assertEqual(m.category, "System")
        self.assertEqual(m.order, 100)

    def test_missing_required_field(self):
        data = {"id": "test", "name": "Test"}  # missing version, description, author
        with self.assertRaises(ValueError) as ctx:
            PluginManifest.from_json(json.dumps(data))
        self.assertIn("Missing required fields", str(ctx.exception))

    def test_invalid_json_syntax(self):
        with self.assertRaises(ValueError) as ctx:
            PluginManifest.from_json("{invalid json")
        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_defaults_applied(self):
        m = PluginManifest.from_json(_valid_json())
        self.assertEqual(m.entry_point, "plugin.py")
        self.assertEqual(m.icon, "🔌")
        self.assertEqual(m.category, "Community")
        self.assertEqual(m.order, 500)
        self.assertEqual(m.permissions, [])
        self.assertEqual(m.requires, [])


# ── PluginManifest.to_json ────────────────────────────────────────

class TestPluginManifestToJson(unittest.TestCase):

    def test_roundtrip(self):
        original = PluginManifest(**_valid_manifest_kwargs())
        json_str = original.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["id"], "test-plugin")
        self.assertEqual(parsed["version"], "1.0.0")  # fixture-version

    def test_optional_fields_included_when_set(self):
        m = PluginManifest(**_valid_manifest_kwargs(
            author_email="a@b.com",
            license="MIT",
            homepage="https://x.com",
            category="System",
            order=100,
        ))
        data = json.loads(m.to_json())
        self.assertEqual(data["author_email"], "a@b.com")
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(data["homepage"], "https://x.com")
        self.assertEqual(data["category"], "System")
        self.assertEqual(data["order"], 100)

    def test_optional_fields_omitted_when_default(self):
        m = PluginManifest(**_valid_manifest_kwargs())
        data = json.loads(m.to_json())
        self.assertNotIn("author_email", data)
        self.assertNotIn("license", data)
        self.assertNotIn("homepage", data)
        self.assertNotIn("category", data)  # default "Community" omitted
        self.assertNotIn("order", data)     # default 500 omitted


# ── PluginManifest._is_valid_semver ───────────────────────────────

class TestIsValidSemver(unittest.TestCase):

    def test_valid_two_part(self):
        self.assertTrue(PluginManifest._is_valid_semver("1.0"))

    def test_valid_three_part(self):
        self.assertTrue(PluginManifest._is_valid_semver("10.20.30"))

    def test_invalid_single(self):
        self.assertFalse(PluginManifest._is_valid_semver("1"))

    def test_invalid_four_parts(self):
        self.assertFalse(PluginManifest._is_valid_semver("1.2.3.4"))

    def test_invalid_alpha(self):
        self.assertFalse(PluginManifest._is_valid_semver("1.0.beta"))

    def test_empty(self):
        self.assertFalse(PluginManifest._is_valid_semver(""))


# ── PluginPackage.create ──────────────────────────────────────────

class TestPluginPackageCreate(unittest.TestCase):

    def test_create_basic(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "print('hello')")
        self.assertEqual(pkg.manifest.id, "test-plugin")
        self.assertIn("plugin.json", pkg.files)
        self.assertIn("plugin.py", pkg.files)
        self.assertIn("CHECKSUMS.sha256", pkg.files)
        self.assertTrue(len(pkg.checksums) > 0)

    def test_create_with_assets(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        assets = {"icon.png": b"\x89PNG", "readme.md": b"# Hello"}
        pkg = PluginPackage.create(manifest, "x = 1", assets=assets)
        self.assertIn("assets/icon.png", pkg.files)
        self.assertIn("assets/readme.md", pkg.files)

    def test_create_with_subdir_assets(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        assets = {"data/config.yaml": b"key: val"}
        pkg = PluginPackage.create(manifest, "x = 1", assets=assets)
        # Subdirs should be kept as-is
        self.assertIn("data/config.yaml", pkg.files)

    def test_create_checksums_exclude_itself(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "x = 1")
        # CHECKSUMS.sha256 and SIGNATURE.asc should not be in checksums dict
        self.assertNotIn("CHECKSUMS.sha256", pkg.checksums)
        self.assertNotIn("SIGNATURE.asc", pkg.checksums)


# ── PluginPackage.save ────────────────────────────────────────────

class TestPluginPackageSave(unittest.TestCase):

    def test_save_creates_archive(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "print('hi')")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.loofi-plugin")
            pkg.save(path)
            self.assertTrue(os.path.exists(path))
            # Verify it's a valid tar.gz
            with tarfile.open(path, "r:gz") as tar:
                names = tar.getnames()
                self.assertIn("plugin.json", names)
                self.assertIn("plugin.py", names)

    def test_save_adds_extension(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "x = 1")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            pkg.save(path)
            expected = os.path.join(tmpdir, "test.loofi-plugin")
            self.assertTrue(os.path.exists(expected))


# ── PluginPackage.from_file ───────────────────────────────────────

class TestPluginPackageFromFile(unittest.TestCase):

    def _create_archive(self, tmpdir, files_dict, name="test.loofi-plugin"):
        """Helper to create a tar.gz archive with given files."""
        path = os.path.join(tmpdir, name)
        with tarfile.open(path, "w:gz") as tar:
            for fname, content in files_dict.items():
                info = tarfile.TarInfo(name=fname)
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
        return path

    def test_load_valid_package(self):
        manifest_json = _valid_json()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "plugin.json": manifest_json.encode(),
                "plugin.py": b"print('hello')",
            })
            pkg = PluginPackage.from_file(path)
            self.assertEqual(pkg.manifest.id, "test-plugin")
            self.assertEqual(pkg.archive_path, Path(path))

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            PluginPackage.from_file("/tmp/nonexistent.loofi-plugin")

    def test_missing_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "other.py": b"x = 1",
            })
            with self.assertRaises(ValueError) as ctx:
                PluginPackage.from_file(path)
            self.assertIn("missing required file: plugin.json", str(ctx.exception))

    def test_invalid_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "plugin.json": b"{invalid json",
                "plugin.py": b"x = 1",
            })
            with self.assertRaises(ValueError) as ctx:
                PluginPackage.from_file(path)
            self.assertIn("Invalid plugin.json", str(ctx.exception))

    def test_missing_entry_point(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "plugin.json": _valid_json().encode(),
                # Missing plugin.py (the entry point)
            })
            with self.assertRaises(ValueError) as ctx:
                PluginPackage.from_file(path)
            self.assertIn("missing entry point", str(ctx.exception))

    def test_invalid_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.loofi-plugin")
            with open(path, "wb") as f:
                f.write(b"this is not a tar.gz")
            with self.assertRaises(ValueError) as ctx:
                PluginPackage.from_file(path)
            self.assertIn("Failed to extract", str(ctx.exception))

    def test_with_checksums(self):
        code = b"x = 1"
        manifest_json = _valid_json().encode()
        checksums_content = (
            hashlib.sha256(manifest_json).hexdigest() + "  plugin.json\n" +
            hashlib.sha256(code).hexdigest() + "  plugin.py\n"
        ).encode()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "plugin.json": manifest_json,
                "plugin.py": code,
                "CHECKSUMS.sha256": checksums_content,
            })
            pkg = PluginPackage.from_file(path)
            self.assertEqual(len(pkg.checksums), 2)

    def test_with_signature(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "plugin.json": _valid_json().encode(),
                "plugin.py": b"x = 1",
                "SIGNATURE.asc": b"-----BEGIN PGP SIGNATURE-----\ntest\n-----END PGP SIGNATURE-----",
            })
            pkg = PluginPackage.from_file(path)
            self.assertIn("BEGIN PGP SIGNATURE", pkg.signature)

    def test_wrong_extension_warning(self):
        """Non-.loofi-plugin extension still loads (with a warning)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._create_archive(tmpdir, {
                "plugin.json": _valid_json().encode(),
                "plugin.py": b"x = 1",
            }, name="test.tar.gz")
            pkg = PluginPackage.from_file(path)
            self.assertEqual(pkg.manifest.id, "test-plugin")


# ── PluginPackage.verify ──────────────────────────────────────────

class TestPluginPackageVerify(unittest.TestCase):

    def test_verify_valid_checksums(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "print('ok')")
        self.assertTrue(pkg.verify())

    def test_verify_no_checksums(self):
        """No checksums should return True (skip verification)."""
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage(manifest=manifest, files={"plugin.py": b"x"}, checksums={})
        self.assertTrue(pkg.verify())

    def test_verify_mismatch(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "print('ok')")
        # Corrupt a file
        pkg.files["plugin.py"] = b"corrupted content"
        self.assertFalse(pkg.verify())

    def test_verify_file_missing_from_archive(self):
        manifest = PluginManifest(**_valid_manifest_kwargs())
        pkg = PluginPackage.create(manifest, "x = 1")
        # Add a checksum for a nonexistent file
        pkg.checksums["missing.py"] = "abc123"
        self.assertFalse(pkg.verify())


# ── Checksum helpers ──────────────────────────────────────────────

class TestChecksumHelpers(unittest.TestCase):

    def test_compute_checksums(self):
        files = {
            "file1.py": b"content1",
            "file2.py": b"content2",
            "CHECKSUMS.sha256": b"excluded",
            "SIGNATURE.asc": b"also excluded",
        }
        checksums = PluginPackage._compute_checksums(files)
        self.assertIn("file1.py", checksums)
        self.assertIn("file2.py", checksums)
        self.assertNotIn("CHECKSUMS.sha256", checksums)
        self.assertNotIn("SIGNATURE.asc", checksums)
        self.assertEqual(checksums["file1.py"], hashlib.sha256(b"content1").hexdigest())

    def test_format_checksums(self):
        checksums = {"b.py": "hash_b", "a.py": "hash_a"}
        formatted = PluginPackage._format_checksums(checksums)
        lines = formatted.strip().split("\n")
        # Sorted by filename
        self.assertTrue(lines[0].startswith("hash_a"))
        self.assertTrue(lines[1].startswith("hash_b"))
        # sha256sum format: "hash  filename"
        self.assertIn("  a.py", lines[0])

    def test_parse_checksums(self):
        content = b"abc123  file1.py\ndef456  file2.py\n"
        checksums = PluginPackage._parse_checksums(content)
        self.assertEqual(checksums["file1.py"], "abc123")
        self.assertEqual(checksums["file2.py"], "def456")

    def test_parse_checksums_empty_lines(self):
        content = b"abc  file.py\n\n  \n"
        checksums = PluginPackage._parse_checksums(content)
        self.assertEqual(len(checksums), 1)


# ── Full roundtrip: create → save → from_file → verify ────────────

class TestPluginPackageRoundtrip(unittest.TestCase):

    def test_full_roundtrip(self):
        manifest = PluginManifest(**_valid_manifest_kwargs(
            permissions=["network"],
            author_email="test@test.com",
        ))
        original = PluginPackage.create(
            manifest, "print('hello world')",
            assets={"icon.txt": b"ICON"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "roundtrip.loofi-plugin")
            original.save(path)

            loaded = PluginPackage.from_file(path)
            self.assertEqual(loaded.manifest.id, "test-plugin")
            self.assertEqual(loaded.manifest.permissions, ["network"])
            self.assertTrue(loaded.verify())
            # Plugin code should be intact
            self.assertEqual(loaded.files["plugin.py"], b"print('hello world')")


if __name__ == '__main__':
    unittest.main()
