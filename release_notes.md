# Release Notes — v20.0.2 "Synapse"

## UI & Dependency Refresh

v20.0.2 "Synapse" focuses on usability fixes for tabbed navigation and refreshes core Python dependencies.

---

### Headline Features

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

- Fixes top sub-tab usability regressions
- Refreshes core dependencies to their latest versions