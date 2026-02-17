# Architecture Spec - v45.0.0 "Housekeeping"

## Design Rationale

v45.0.0 is a stabilization-first release focused on operational safety, CI gate reliability,
and user guidance hardening. The architecture intent is to preserve behavior while removing
unsafe guidance and improving resilience under constrained runtime environments.

## Scope

1. Replace unsafe install and recovery hints with package-manager-aware, pkexec-safe guidance.
2. Narrow broad exception handling to explicit expected failure modes.
3. Harden runtime logging/storage paths to survive sandboxed or non-writable HOME setups.
4. Keep workflow/version artifacts aligned so CI release gates remain deterministic.

## Key Decisions

### Install Hint Normalization

A shared helper (`utils/install_hints.py`) is the source of truth for install hints.
UI and utils modules consume this helper instead of hardcoding package commands.

### Safe Guidance Enforcement

Lock-recovery and USBGuard guidance text no longer suggests unsafe `sudo` patterns.
Messages favor least-privilege operational instructions and non-destructive recovery steps.

### Exception Narrowing

`whats_new_dialog.mark_seen()` catches only explicit expected exception classes,
retaining fail-safe UX without broad `except Exception` behavior.

### Environment-Resilient Writes

Filesystem writes that may fail in restricted environments now support safe fallbacks
(e.g., `/tmp/loofi-fedora-tweaks/...`) so functionality and tests remain robust.

## Risks and Mitigations

- Risk: Message text changes can break assertion-heavy tests.
  Mitigation: Updated/added tests for backup, containers, teleport, usbguard, and error paths.

- Risk: Runtime import indirection can break mocks.
  Mitigation: `cmd_health_history` supports both `cli.main.HealthTimeline` and
  `utils.health_timeline.HealthTimeline` patch styles.

- Risk: CI release gate failure from missing workflow specs.
  Mitigation: v45 task spec and this v45 arch spec are both present and version-aligned.

## Validation

- Workflow contract checks:
  - `tests/test_workflow_fedora_review_contract.py`
  - `tests/test_workflow_runner_locks.py`
  - `tests/test_check_fedora_review.py`
  - `tests/test_release_doc_check.py`
  - `tests/test_version.py`

- Safety/lint/type gates:
  - `python3 scripts/check_stabilization_rules.py`
  - `flake8 loofi-fedora-tweaks/ --jobs=1 --max-line-length=150 --ignore=E501,W503,E402,E722,E203`
  - `mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary --warn-return-any`

- Fedora review gate:
  - `XDG_CACHE_HOME=/tmp HOME=/tmp python3 scripts/check_fedora_review.py`
