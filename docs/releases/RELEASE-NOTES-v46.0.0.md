# Release Notes -- v46.0.0 "Navigator"

**Release Date:** 2026-02-17
**Codename:** Navigator
**Theme:** Category clarity and navigation consistency

## Summary

v46.0.0 focuses on sidebar and discovery clarity without changing core runtime behavior.
The release standardizes tab grouping under a technical category model, aligns command palette grouping, and removes category drift/orphan labels.

## Highlights

- Unified navigation taxonomy across sidebar and command palette
- Registry/category alignment cleanup for all tab metadata
- Updated tab-reference and architecture documentation to reflect current structure
- Semantic icon-pack rollout with theme-aware tinting for clearer light/dark readability

## Changes

### Changed

- Reorganized tab categories and ordering for clearer discoverability
- Updated command palette category labels to match sidebar taxonomy
- Updated category-oriented metadata tests for affected tabs
- Replaced emoji-style icon references in navigation flows with semantic icon IDs routed through `ui/icon_pack.py`
- Added selection-aware sidebar icon tint variants and normalized icon sizing (`17x17`) for tighter visual integration

### Added

- New release notes file for v46.0.0
- Bundled icon-pack assets in both runtime locations:
  - `assets/icons/`
  - `loofi-fedora-tweaks/assets/icons/`

### Fixed

- Eliminated orphan category names not present in plugin registry ordering

## Stats

- **Tests:** 5901 passed, 35 skipped, 0 failed
- **Lint:** 0 errors
- **Coverage:** Existing project baseline unchanged by metadata-only changes

## Upgrade Notes

No upgrade migration steps required.
