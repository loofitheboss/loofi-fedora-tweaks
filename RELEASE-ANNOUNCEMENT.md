# Loofi Fedora Tweaks v20.0.2-2 "Synapse" Release Announcement

## TL;DR

Loofi Fedora Tweaks v20.0.2-2 "Synapse" is now available! This hotfix focuses on a **KDE top-bar/title-area rendering glitch** while keeping all native window behavior intact.

**Install now:** `sudo dnf copr enable loofitheboss/loofi-fedora-tweaks && sudo dnf install loofi-fedora-tweaks`

**GitHub Release:** https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v20.0.2

---

## What's New in v20.0.2-2 "Synapse"

### 🪟 KDE Top-Bar Rendering Hotfix

Fixed a visual glitch where top client-area content could appear too close to or overlapping the window title/header region on some Fedora KDE Plasma setups (Wayland/X11).

- Main window now explicitly keeps native title-bar flags enabled
- No frameless/custom title-bar behavior is used for the main app window
- Native drag, resize, and system window buttons remain unchanged

### 🧪 Regression Guard Added

- New lightweight geometry sanity test: `tests/test_main_window_geometry.py`
- Verifies central widget and first visible root widget are positioned in valid client-space (`y() >= 0`)

---

### Previous v20.0.2 Improvements (still included)

### 🧭 Tab Navigation Usability Fix

Top sub-tabs are now usable even with many sections:

- Scroll buttons enabled for overflowed tab bars
- Non-expanding tabs keep the bar compact
- Long labels elide instead of pushing tabs off-screen
- Scroller buttons styled across all bundled themes

### 📦 Dependency Refresh

Pinned the Python dependencies to the latest stable versions:

- PyQt6 6.10.2
- requests 2.32.5
- fastapi 0.128.5
- uvicorn 0.40.0
- PyJWT 2.11.0
- bcrypt 5.0.0
- httpx 0.28.1
- python-multipart 0.0.22

### 📦 Installation & Usage

**Fedora 40/41 (via COPR):**
```bash
sudo dnf copr enable loofitheboss/loofi-fedora-tweaks
sudo dnf install loofi-fedora-tweaks
```

**GUI Mode (default):**
```bash
loofi-fedora-tweaks
```

**Headless Web API:**
```bash
loofi-fedora-tweaks --web
```

**Generate API Key:**
```bash
curl -X POST http://localhost:8000/api/key
# {"api_key": "loofi_<random_secure_key>"}
```

**Get JWT Token:**
```bash
curl -X POST http://localhost:8000/api/token -d "api_key=loofi_..."
# {"access_token": "eyJ...", "token_type": "bearer"}
```

**Execute System Action (with preview):**
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"command": "dnf", "args": ["clean", "all"], "preview": true}'
```

### ✅ Tests

- UI smoke suite: 15 passed, 22 skipped (headless)
- Visual verification recommended on hardware with OpenGL drivers

### 📊 Notes

This is a minor, compatibility-safe update focused on UI polish and dependency hygiene.

### 🔗 Links

- **GitHub Release**: https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v20.0.2
- **Full Changelog**: https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/CHANGELOG.md
- **Documentation**: https://github.com/loofitheboss/loofi-fedora-tweaks#readme
- **Report Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues

### 🎯 What's Next

- Further UI polish (breadcrumb refinements, notification panel tweaks)
- Remote management UX improvements

### 💬 Feedback Welcome!

We’d love your feedback on:
- Tab navigation usability improvements
- Theme styling for tab scrollers
- Any regressions you notice after the dependency refresh

Try it out and let us know what you think!

---

**Credits:**
- Developed with assistance from Claude Code (Anthropic)
- Built for the Fedora Linux community
- Open source under MIT License

**Maintainer:** Loofi ([@loofitheboss](https://github.com/loofitheboss))
