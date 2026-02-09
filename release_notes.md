# Release Notes — v20.0.2-2 "Synapse" (RPM Hotfix)

## KDE Top-Bar Hotfix

This RPM hotfix addresses a top title/header rendering glitch seen on Fedora KDE Plasma (Wayland/X11) after recent UI polish.

---

### Headline Fixes

#### KDE Top Chrome Stability
- Main window now explicitly enforces native window decorations (no frameless/custom title hints)
- Prevents client-area visuals from appearing to overlap into the title/top chrome region
- Preserves native drag/resize behavior and native window buttons

#### Regression Guard
- Added a lightweight UI geometry sanity test:
  - `tests/test_main_window_geometry.py`
  - Asserts `centralWidget().geometry().y() >= 0`
  - Confirms first visible root widget is not clipped (`y() >= 0`)

---

### Also Included (from v20.0.2)

#### Tab Scroller Fixes
- Scroll buttons enabled on all top sub-tab bars
- Non-expanding tabs with elided labels to prevent overflow
- Scroll buttons styled across modern, light, and classic themes

#### Dependency Updates
- Requirements pinned to the latest stable versions for PyQt6, requests, fastapi, uvicorn, PyJWT, bcrypt, httpx, python-multipart

---

### Notes

- UI smoke tests run successfully after installing PyJWT (15 passed, 22 skipped)
- Visual verification recommended on a machine with OpenGL/Qt drivers

---

### Tests

- **15 UI smoke tests passed**, 22 skipped (headless environment)

---

### Summary

- Fixes KDE top-bar/title-area overlap artifacts safely via native window flags
- Adds regression coverage for main-window client-area geometry
- Fixes top sub-tab usability regressions
- Refreshes core dependencies to their latest versions