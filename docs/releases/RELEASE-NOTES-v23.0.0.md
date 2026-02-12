# Release Notes v23.0.0 "Architecture Hardening"

Released: 2026-02-10

## Highlights

- Introduce `BaseActionExecutor` to standardize privileged and non-privileged action execution.
- Integrate `pkexec` execution flow in the core executor foundation.
- Centralize worker threading through `core/workers/BaseWorker` for consistent async behavior.
- Migrate system and hardware services into `services/system/` and `services/hardware/`.
- Add GitHub Actions CI workflow for automated project validation.

## Breaking Changes

- No breaking changes in public CLI/UI entry points.
- Internal imports should prefer `core/` and `services/` modules; legacy `utils/` paths remain shimmed.

## Installation

```bash
pkexec dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v23.0.0/loofi-fedora-tweaks-23.0.0-1.noarch.rpm
```

## Full Changelog

- See `CHANGELOG.md` for the complete list of changes.
