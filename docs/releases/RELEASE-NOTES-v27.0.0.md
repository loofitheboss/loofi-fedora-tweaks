# Loofi Fedora Tweaks v27.0.0 — Marketplace Enhancement

**Release Date:** 2026-02-12  
**Codename:** Marketplace Enhancement  
**Type:** Minor feature release

---

## Highlights

- Added CDN-first marketplace index loading with signed metadata support, cache usage, and fallback behavior.
- Added plugin ratings/reviews flows across API, CLI, and Community tab UX.
- Added verified publisher trust state and badge output in plugin listing/detail surfaces.
- Added opt-in plugin analytics pipeline with default-off consent and anonymized batched events.
- Added plugin hot-reload contracts and rollback-safe reload flow integration.
- Strengthened plugin isolation policy enforcement in sandbox-related execution paths.
- Updated Plugin SDK, roadmap, changelog, README, and package metadata for v27 alignment.

---

## Validation

- `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722`
- `python loofi-fedora-tweaks/main.py --version`

