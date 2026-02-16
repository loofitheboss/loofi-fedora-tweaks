"""Version alignment tests for release artifacts."""

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "loofi-fedora-tweaks" / "version.py"
PYPROJECT_FILE = ROOT / "pyproject.toml"
SPEC_FILE = ROOT / "loofi-fedora-tweaks.spec"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


def _extract_with_regex(path: Path, pattern: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"Unable to parse version from {path}")
    return match.group(1)


class TestVersionAlignment(unittest.TestCase):
    """Ensure version and codename metadata are aligned and well-formed."""

    def test_version_semver_format(self):
        from version import __version__

        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_codename_nonempty(self):
        from version import __version_codename__

        self.assertTrue(len(__version_codename__) > 0)

    def test_version_files_are_aligned(self):
        from version import __version__

        pyproject_version = _extract_with_regex(
            PYPROJECT_FILE,
            r'^version\s*=\s*"([^"]+)"',
        )
        spec_version = _extract_with_regex(
            SPEC_FILE,
            r"^Version:\s*([0-9]+\.[0-9]+\.[0-9]+)",
        )

        self.assertEqual(__version__, pyproject_version)
        self.assertEqual(__version__, spec_version)


if __name__ == "__main__":
    unittest.main()
