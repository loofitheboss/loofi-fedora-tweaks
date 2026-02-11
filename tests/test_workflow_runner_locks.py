"""Tests for scripts/workflow_runner.py lock and routing helpers."""

import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_writer_lock_denies_concurrent_owner(tmp_path):
    module = _load_module("workflow_runner_lock_test", Path("scripts/workflow_runner.py"))
    module.WRITER_LOCK_FILE = tmp_path / ".writer-lock.json"

    now = module.utc_now()
    lock_data = {
        "assistant": "codex",
        "owner": "alice",
        "version": "v26.0",
        "phase": "build",
        "acquired_at": module.isoformat_utc(now),
        "expires_at": module.isoformat_utc(now + timedelta(minutes=30)),
    }
    module.WRITER_LOCK_FILE.write_text(json.dumps(lock_data), encoding="utf-8")

    ok, reason = module.ensure_writer_lock(
        version_tag="v26.0",
        phase="test",
        assistant="claude",
        owner="bob",
        ttl_minutes=60,
        dry_run=False,
    )

    assert not ok
    assert "writer lock is held by" in reason


def test_model_router_toml_overrides_defaults(tmp_path):
    module = _load_module("workflow_runner_router_test", Path("scripts/workflow_runner.py"))
    router_file = tmp_path / "model-router.toml"
    router_file.write_text(
        """
[phases]
plan = "gpt-5.3-codex"
design = "gpt-5.3-codex"
build = "gpt-4o"
test = "gpt-4o"
doc = "gpt-4o-mini"
package = "gpt-4o-mini"
release = "gpt-4o-mini"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    module.MODEL_ROUTER_FILE = router_file
    models = module.load_phase_models()

    assert models["doc"] == "gpt-4o-mini"
    assert models["package"] == "gpt-4o-mini"
    assert models["release"] == "gpt-4o-mini"


def test_task_contract_validation_fails_for_missing_fields(tmp_path):
    module = _load_module("workflow_runner_contract_test", Path("scripts/workflow_runner.py"))
    tasks_file = tmp_path / "tasks-v26.0.md"
    tasks_file.write_text(
        """
- [ ] ID: TASK-001 | Files: `a.py` | Dep: - | Agent: backend-builder | Description: add feature
""".strip()
        + "\n",
        encoding="utf-8",
    )

    issues = module.validate_task_contract(tasks_file)

    assert issues
    assert any("Acceptance:" in item for item in issues)
