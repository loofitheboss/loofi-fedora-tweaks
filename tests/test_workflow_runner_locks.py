"""Tests for scripts/workflow_runner.py lock and routing helpers."""

import importlib.util
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, f"Failed to load spec from {path}"
    assert spec.loader is not None, f"Spec has no loader for {path}"
    module = importlib.util.module_from_spec(spec)
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


def test_task_contract_validation_accepts_valid_entries(tmp_path):
    module = _load_module("workflow_runner_contract_valid_test", Path("scripts/workflow_runner.py"))
    tasks_file = tmp_path / "tasks-v28.0.0.md"
    tasks_file.write_text(
        """
- [ ] ID: TASK-001 | Files: `a.py` | Dep: - | Agent: backend-builder | Description: add feature
  Acceptance: feature implemented
  Docs: none
  Tests: `tests/test_a.py`
""".strip()
        + "\n",
        encoding="utf-8",
    )

    issues = module.validate_task_contract(tasks_file)

    assert issues == []


def test_validate_race_returns_blocked_when_lock_missing(tmp_path):
    module = _load_module("workflow_runner_race_missing_test", Path("scripts/workflow_runner.py"))
    module.LOCK_FILE = tmp_path / ".race-lock.json"

    ok, reason = module.validate_race("v28.0.0")

    assert not ok
    assert "no active race lock found" in reason


def test_validate_race_detects_version_mismatch(tmp_path):
    module = _load_module("workflow_runner_race_mismatch_test", Path("scripts/workflow_runner.py"))
    module.LOCK_FILE = tmp_path / ".race-lock.json"
    module.LOCK_FILE.write_text(
        json.dumps(
            {
                "version": "v27.0.0",
                "started_at": "20260212_000000",
                "status": "active",
            }
        ),
        encoding="utf-8",
    )

    ok, reason = module.validate_race("v28.0.0")

    assert not ok
    assert "race version mismatch" in reason


def test_validate_race_passes_for_matching_version(tmp_path):
    module = _load_module("workflow_runner_race_ok_test", Path("scripts/workflow_runner.py"))
    module.LOCK_FILE = tmp_path / ".race-lock.json"
    module.LOCK_FILE.write_text(
        json.dumps(
            {
                "version": "v28.0.0",
                "started_at": "20260212_000000",
                "status": "active",
            }
        ),
        encoding="utf-8",
    )

    ok, reason = module.validate_race("v28.0.0")

    assert ok
    assert reason == "ok"


def test_task_contract_validation_fails_for_missing_artifact(tmp_path):
    module = _load_module("workflow_runner_contract_missing_artifact_test", Path("scripts/workflow_runner.py"))
    missing_file = tmp_path / "tasks-v28.0.0.md"

    issues = module.validate_task_contract(missing_file)

    assert issues == [f"missing task artifact: {missing_file}"]


def test_task_contract_validation_fails_when_no_task_entries(tmp_path):
    module = _load_module("workflow_runner_contract_no_entries_test", Path("scripts/workflow_runner.py"))
    tasks_file = tmp_path / "tasks-v28.0.0.md"
    tasks_file.write_text("# Tasks\n", encoding="utf-8")

    issues = module.validate_task_contract(tasks_file)

    assert issues == ["task artifact has no task entries with ID field"]


@patch("shutil.which", return_value=None)
def test_run_agent_fails_when_codex_missing(mock_which, tmp_path):
    module = _load_module("workflow_runner_run_agent_missing_codex_test", Path("scripts/workflow_runner.py"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Prompt body", encoding="utf-8")
    input_file = tmp_path / "input.md"
    input_file.write_text("input", encoding="utf-8")

    code, metadata = module.run_agent(
        phase_name="P4 TEST",
        model="gpt-4o",
        inputs=[input_file],
        prompt_file=prompt_file,
        instruction="Write test report",
        dry_run=False,
        assistant="codex",
        mode="write",
        review_output=None,
    )

    assert mock_which.called
    assert code == 127
    assert metadata["status"] == "error"
    assert "codex" in metadata["error"]


@patch("subprocess.run")
@patch("shutil.which", return_value="/usr/bin/codex")
def test_run_agent_review_mode_writes_report(mock_which, mock_run, tmp_path):
    module = _load_module("workflow_runner_run_agent_review_test", Path("scripts/workflow_runner.py"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Prompt body", encoding="utf-8")
    input_file = tmp_path / "input.md"
    input_file.write_text("input", encoding="utf-8")
    review_output = tmp_path / "reviews" / "v28.0.0-test.md"

    mock_run.return_value = subprocess.CompletedProcess(
        args=["codex"],
        returncode=0,
        stdout="review output",
        stderr="",
    )

    code, metadata = module.run_agent(
        phase_name="P4 TEST",
        model="gpt-4o",
        inputs=[input_file],
        prompt_file=prompt_file,
        instruction="Write test report",
        dry_run=False,
        assistant="codex",
        mode="review",
        review_output=review_output,
    )

    assert mock_which.called
    mock_run.assert_called_once()
    assert code == 0
    assert metadata["status"] == "success"
    assert metadata["review_output"] == str(review_output)
    assert review_output.exists()
    assert "review output" in review_output.read_text(encoding="utf-8")
