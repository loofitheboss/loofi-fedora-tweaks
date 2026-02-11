"""Tests for scripts/sync_ai_adapters.py helper functions."""

import importlib.util
import sys
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_sync_file_detects_drift_and_writes(tmp_path):
    module = _load_module("sync_ai_adapters_test", Path("scripts/sync_ai_adapters.py"))

    source = tmp_path / "source.md"
    target = tmp_path / "target.md"
    source.write_text("canonical\n", encoding="utf-8")
    target.write_text("stale\n", encoding="utf-8")

    mapping = module.FileMapping(source=source, target=target)
    diffs: list[str] = []

    module.sync_file(mapping, check=False, diffs=diffs)

    assert diffs
    assert target.read_text(encoding="utf-8") == "canonical\n"


def test_sync_directory_detects_stale_files_in_check_mode(tmp_path):
    module = _load_module("sync_ai_adapters_dir_test", Path("scripts/sync_ai_adapters.py"))

    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    (source_dir / "a.md").write_text("a\n", encoding="utf-8")
    (target_dir / "a.md").write_text("a\n", encoding="utf-8")
    (target_dir / "obsolete.md").write_text("old\n", encoding="utf-8")

    mapping = module.DirMapping(source=source_dir, target=target_dir)
    diffs: list[str] = []

    module.sync_directory(mapping, check=True, diffs=diffs)

    assert any("stale adapter file" in item for item in diffs)
    assert (target_dir / "obsolete.md").exists()
