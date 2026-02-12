# Loofi Fedora Tweaks v26.0.1 — Breadcrumb Bar UI Hotfix

**Release Date:** 2026-02-12  
**Codename:** Breadcrumb Bar UI Hotfix  
**Type:** Patch hotfix

---

## Fixed

- Fixed top breadcrumb bar rendering artifacts where `Category > Page > Description` labels appeared with opaque rectangular backgrounds.
- Added explicit transparent background styling for breadcrumb labels in both themes:
  - `loofi-fedora-tweaks/assets/modern.qss`
  - `loofi-fedora-tweaks/assets/light.qss`

---

## Validation

- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_tab_margins.py -q`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_ui_smoke.py -q`

---

## Notes

- No behavioral changes outside breadcrumb visuals.
- No breaking changes.
