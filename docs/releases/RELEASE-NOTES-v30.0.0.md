# Release Notes — Loofi Fedora Tweaks v30.0.0

> **Codename**: Distribution & Reliability
> **Release date**: 2026-02-13
> **Status**: Draft

## Highlights
- Added packaging scripts for Flatpak, AppImage, and sdist outputs.
- Improved update and marketplace reliability with cache-aware offline behavior.
- Hardened concurrency behavior in rate limiter and auto-tuner history operations.
- Raised CI quality gates and added packaging jobs.

## Distribution Packaging
- Flatpak: `scripts/build_flatpak.sh` (+ root wrapper `build_flatpak.sh`), output in `dist/flatpak/`.
- AppImage: `scripts/build_appimage.sh`, output in `dist/appimage/`.
- Source dist: `scripts/build_sdist.sh` + `pyproject.toml`, output in `dist/`.

## Reliability Improvements
- `utils/update_checker.py`: structured asset metadata, download pipeline, checksum/signature fail-closed verification, and cache-aware offline fallback.
- `utils/plugin_marketplace.py`: offline/cache-first behavior with explicit result metadata.
- `utils/rate_limiter.py`: event-based wait logic to avoid busy-wait loops.
- `utils/auto_tuner.py`: synchronized history read/write paths for concurrent safety.

## CI / Quality Gates
- `.github/workflows/ci.yml` now enforces:
  - blocking `mypy` and `bandit`
  - coverage threshold `--cov-fail-under=75`
  - packaging jobs for Flatpak, AppImage, and sdist

## Validation
- Targeted v30 reliability/packaging tests pass:
  - `tests/test_packaging_scripts.py`
  - `tests/test_update_checker.py`
  - `tests/test_plugin_marketplace_cdn.py`
  - `tests/test_rate_limiter.py`
  - `tests/test_auto_tuner.py`

## Known Limitations
- Packaging scripts require host tools to be pre-installed and available in `PATH`.
- Signature verification behavior depends on available signature/public-key artifacts.
