# Contributing to Loofi Fedora Tweaks

Thanks for contributing.

This guide focuses on how to make safe, reviewable changes that match project conventions.

---

## Development Setup

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run from source:

```bash
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py
```

CLI mode:

```bash
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py --cli info
```

---

## Project Architecture (Current)

High-level layout:

- `loofi-fedora-tweaks/ui/` - PyQt6 tabs and window components
- `loofi-fedora-tweaks/utils/` - business logic and command operations
- `loofi-fedora-tweaks/core/plugins/` - plugin registry/loader/compat layer
- `loofi-fedora-tweaks/cli/main.py` - CLI entrypoint
- `loofi-fedora-tweaks/services/` - service layer components
- `tests/` - unit tests with mocks

The UI is plugin-driven: tab metadata, registration, and compatibility are sourced from plugin interfaces.

---

## Critical Engineering Rules

1. Never use `sudo` in application command execution paths; use `pkexec` via command helpers.
2. Never hardcode `dnf`; use package manager detection (`dnf` vs `rpm-ostree`).
3. Never call subprocesses directly from UI tabs; put system logic in `utils/`.
4. Always unpack operation tuples before `subprocess.run()`.
5. Keep version values synchronized across `version.py` and `.spec`.

---

## Coding Standards

- Prefer existing patterns over new abstractions.
- Keep changes minimal and targeted.
- New UI tabs should follow `BaseTab` and plugin metadata conventions.
- Keep user-visible strings translatable (`self.tr("...")`) in UI code.
- Avoid introducing root-required tests or environment-coupled behavior.

---

## Testing Requirements

Run tests before opening a PR:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov-fail-under=80
```

Testing expectations:

- Mock all system calls (`subprocess`, filesystem, command discovery).
- Cover both success and failure paths.
- Prefer `@patch` decorators in unittest-style tests.

---

## Lint and Build

Lint:

```bash
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
```

Build RPM:

```bash
bash scripts/build_rpm.sh
```

---

## Pull Request Workflow

1. Create a topic branch from `master`.
2. Keep commits scoped (for example docs-only or tests-only).
3. Update docs for behavioral changes (`README`, user guide, release notes/changelog as needed).
4. Include test evidence in the PR description.
5. Link related issues.

Recommended commit style:

- `fix: ...`
- `feat: ...`
- `docs: ...`
- `test: ...`

---

## Reporting Bugs and Requesting Features

Use GitHub issues:

- Bugs: include reproduction steps, expected/actual behavior, logs, environment.
- Features: include user problem, proposed UX/CLI behavior, and constraints.

Issue tracker: <https://github.com/loofitheboss/loofi-fedora-tweaks/issues>
