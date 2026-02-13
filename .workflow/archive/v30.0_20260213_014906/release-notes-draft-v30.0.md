# Release Notes Draft — v30.0.0

## Highlights
- Added distribution packaging paths for Flatpak, AppImage, and Python source distribution (sdist).
- Expanded update reliability with structured release metadata, asset download support, and integrity verification.
- Added explicit offline-mode behavior for update checks and plugin marketplace access.
- Improved concurrency reliability in rate limiting and auto-tuner history operations.
- Hardened CI quality gates (type, security, coverage, packaging jobs).

## New Distribution Options
- Flatpak build flow:
  - script: `scripts/build_flatpak.sh`
  - output: bundle + local repo artifacts under `dist/flatpak/`
- AppImage build flow:
  - script: `scripts/build_appimage.sh`
  - output: versioned `.AppImage` artifact under `dist/appimage/`
- Source distribution build flow:
  - script: `scripts/build_sdist.sh`
  - output: source tarball under `dist/`

## Update & Marketplace Reliability
- Update checker now supports a full auto-update pipeline:
  - release discovery
  - downloadable asset selection
  - download handoff
  - integrity/signature verification before install handoff
- Offline handling improvements:
  - update and marketplace operations now return stable offline-aware results
  - cache-first fallback behavior when network is unavailable
  - network errors no longer surface as unhandled exceptions in supported flows

## Stability Improvements
- Rate limiter coordination improved to reduce busy-waiting and tighten timeout behavior under concurrency.
- Auto-tuner history operations are synchronized to avoid concurrent read/write races and partial state writes.

## CI / Quality Gates
- `mypy` and `bandit` checks are blocking (no `continue-on-error`).
- Test coverage threshold raised to 75%.
- Packaging jobs added to CI for Flatpak/AppImage/sdist validation.

## Verification Steps (Draft)
1. Run packaging scripts locally:
   - `bash scripts/build_flatpak.sh`
   - `bash scripts/build_appimage.sh`
   - `bash scripts/build_sdist.sh`
2. Run tests:
   - `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov-fail-under=75`
3. Confirm CI workflow:
   - packaging jobs run
   - mypy/bandit are blocking
   - coverage gate enforces 75%

## Compatibility Notes
- Existing public utility entry points remain available.
- Offline behavior is additive and designed to preserve current call sites while improving error handling.
- No UI tab contract changes are expected in this release scope.

## Known Limitations (Draft)
- Packaging scripts depend on host build tools being installed and available in `PATH`.
- Signature verification behavior depends on configured key/signature source availability.

## Upgrade / Operator Notes
- Integrators should update CI expectations for stricter quality gates.
- Packaging consumers can migrate to script-based artifact generation for reproducible outputs.
