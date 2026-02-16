"""Contract tests for Fedora review workflow gates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
AUTO_RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "auto-release.yml"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ci_workflow_has_required_fedora_review_gate():
    text = _read_text(CI_WORKFLOW)

    assert "fedora_review:" in text
    assert "dnf install -y python3 fedora-review" in text
    assert "python3 scripts/check_fedora_review.py" in text


def test_auto_release_workflow_has_required_fedora_review_gate():
    text = _read_text(AUTO_RELEASE_WORKFLOW)

    assert "fedora_review:" in text
    assert "dnf install -y python3 fedora-review" in text
    assert "python3 scripts/check_fedora_review.py" in text


def test_auto_release_build_requires_fedora_review_gate_success():
    text = _read_text(AUTO_RELEASE_WORKFLOW)

    assert (
        "needs: [validate, adapter_drift, lint, typecheck, stabilization_rules, "
        "docs_gate, test, security, fedora_review]"
    ) in text
    assert "needs.fedora_review.result == 'success'" in text
