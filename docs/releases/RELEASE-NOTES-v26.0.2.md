# Loofi Fedora Tweaks v26.0.2 — Status Bar UI Hotfix

**Release Date:** 2026-02-12  
**Codename:** Status Bar UI Hotfix  
**Type:** Patch hotfix

---

## Fixed

- Fixed bottom status bar rendering artifacts where shortcut hint and version labels appeared with opaque rectangular backgrounds.
- Added explicit transparent label styling for status bar labels in both themes:
  - `loofi-fedora-tweaks/assets/modern.qss`
  - `loofi-fedora-tweaks/assets/light.qss`

---

## Validation

- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_tab_margins.py -q`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_ui_smoke.py -q`
- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_clarity_update.py -q`

---

## Notes

- No behavioral changes outside status-bar visuals.
- No breaking changes.
