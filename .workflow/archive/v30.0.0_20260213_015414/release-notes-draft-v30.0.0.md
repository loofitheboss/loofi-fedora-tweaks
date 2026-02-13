# Release Notes Draft — v30.0.0

## Summary
v30.0.0 focuses on distribution reliability and runtime resilience: hardened Flatpak/AppImage/sdist packaging, end-to-end self-update orchestration, offline-aware marketplace/update behavior, thread-safety fixes, and stricter CI/release quality gates.

## Highlights
- Packaging scripts now fail fast on missing dependencies/assets and produce deterministic, versioned artifacts for Flatpak, AppImage, and sdist outputs.
- New CLI self-update flow wires release detection, artifact selection by install channel, download, and verification into one structured path.
- Update and marketplace offline modes now return explicit `offline/source` metadata with cache-aware fallbacks and stable error mapping.
- Concurrency robustness improved in rate limiting and auto-tuner history handling to prevent race conditions under parallel callers.
- CI and auto-release pipelines now enforce strict type/security gates and repository coverage threshold at 75%.

## User-Visible Changes
- New command:
  - `loofi self-update check`
  - `loofi self-update run --channel auto`
- Packaging outputs:
  - `dist/flatpak/loofi-fedora-tweaks-v<version>.flatpak`
  - `dist/appimage/loofi-fedora-tweaks-v<version>-x86_64.AppImage`
  - `dist/loofi_fedora_tweaks-<version>.tar.gz`

## Reliability and Safety
- Offline network failures prefer cache when available and return deterministic metadata fields.
- Update verification explicitly supports checksum and signature failure handling.
- Threaded operations in limiter/history paths are validated with concurrency-focused regression tests.

## CI/Release Quality Gates
- `mypy` and `bandit` run as hard gates (no soft-fail bypasses).
- Coverage requirement in CI/release pipelines set to `--cov-fail-under=75`.
- Distribution jobs for Flatpak/AppImage/sdist remain active in pipelines.

## Validation Commands
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_packaging_scripts.py -v`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_update_checker.py -v`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_plugin_marketplace.py -v`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_rate_limiter.py tests/test_auto_tuner.py -v`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov=loofi-fedora-tweaks --cov-fail-under=75`

## Upgrade Notes
- No manual migration expected for existing users.
- Automation/users consuming workflow outcomes should account for stricter CI gate behavior.

## Files Expected to Be Updated During Implementation
- `scripts/build_flatpak.sh`
- `scripts/build_appimage.sh`
- `scripts/build_sdist.sh`
- `pyproject.toml`
- `loofi-fedora-tweaks/utils/update_checker.py`
- `loofi-fedora-tweaks/utils/plugin_marketplace.py`
- `loofi-fedora-tweaks/utils/rate_limiter.py`
- `loofi-fedora-tweaks/utils/auto_tuner.py`
- `loofi-fedora-tweaks/cli/main.py`
- `.github/workflows/ci.yml`
- `.github/workflows/auto-release.yml`
- test files listed in task plan
