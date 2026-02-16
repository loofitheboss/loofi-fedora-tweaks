"""Tests for scripts/check_stabilization_rules.py."""

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


def test_detects_missing_timeout():
    module = _load_module(
        "check_stabilization_rules_timeout_test",
        Path("scripts/check_stabilization_rules.py"),
    )

    source = "import subprocess\nsubprocess.run(['echo', 'ok'])\n"
    violations = module.analyze_source(source, "loofi-fedora-tweaks/utils/example.py")

    assert any(v.rule == "missing-timeout" for v in violations)


def test_detects_ui_subprocess_usage():
    module = _load_module(
        "check_stabilization_rules_ui_test",
        Path("scripts/check_stabilization_rules.py"),
    )

    source = "import subprocess\nsubprocess.run(['echo', 'ok'], timeout=1)\n"
    violations = module.analyze_source(source, "loofi-fedora-tweaks/ui/example_tab.py")

    assert any(v.rule == "ui-subprocess" for v in violations)


def test_detects_hardcoded_dnf_in_subprocess_and_command_worker():
    module = _load_module(
        "check_stabilization_rules_dnf_test",
        Path("scripts/check_stabilization_rules.py"),
    )

    subprocess_source = "import subprocess\nsubprocess.run(['dnf', 'check-update'], timeout=10)\n"
    worker_source = "from core.workers.command_worker import CommandWorker\nCommandWorker('pkexec', ['dnf', 'update', '-y'])\n"

    v1 = module.analyze_source(subprocess_source, "loofi-fedora-tweaks/utils/a.py")
    v2 = module.analyze_source(worker_source, "loofi-fedora-tweaks/services/package/service.py")

    assert any(v.rule == "hardcoded-dnf" for v in v1)
    assert any(v.rule == "hardcoded-dnf" for v in v2)


def test_broad_exception_allowlist_respected():
    module = _load_module(
        "check_stabilization_rules_broad_test",
        Path("scripts/check_stabilization_rules.py"),
    )

    # This one is allowlisted in script constants
    allowed_source = """
class BaseWorker:
    def run(self):
        try:
            return 1
        except Exception:
            return 0
"""
    blocked_source = """
def perform():
    try:
        return 1
    except Exception:
        return 0
"""

    allowed = module.analyze_source(
        allowed_source, "loofi-fedora-tweaks/core/workers/base_worker.py"
    )
    blocked = module.analyze_source(
        blocked_source, "loofi-fedora-tweaks/utils/not_allowlisted.py"
    )

    assert not any(v.rule == "broad-exception" for v in allowed)
    assert any(v.rule == "broad-exception" for v in blocked)


def test_cli_returns_nonzero_when_violations(tmp_path):
    module = _load_module(
        "check_stabilization_rules_cli_test",
        Path("scripts/check_stabilization_rules.py"),
    )

    bad = tmp_path / "bad.py"
    bad.write_text("import subprocess\nsubprocess.run(['echo'])\n", encoding="utf-8")

    exit_code = module.main([str(bad)])
    assert exit_code == 1
