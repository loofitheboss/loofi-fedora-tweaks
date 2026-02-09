# Loofi Fedora Tweaks v21.0.0 "UX Stabilization & Layout Integrity"

## Release Highlights

v21.0.0 focuses on foundational layout fixes, HiDPI rendering safety, and theme consistency for stable cross-desktop behavior.

### What's Changed

- **Native Title Bar Enforcement**: Fixed window chrome overlay issues on KDE Plasma (Wayland/X11) by removing custom window hints and enforcing native decorations
- **QTabBar Scroller Styling**: Scoped scroller button styles to prevent theme conflicts, ensuring clean sub-tab navigation
- **Minimum Window Size**: Enforced 800x500 minimum dimensions with consistent 16px margins for proper content layout
- **HiDPI Rendering Safety**: Font-metrics-based sizing and `pt` units for DPI-independent layouts across all themes
- **Border Cleanup**: Set `documentMode()` on all QTabWidget instances for cleaner tab rendering
- **Layout Regression Tests**: Added test suite for main window geometry, title bar visibility, and client area placement
- **Theme-Aware Inline Styles**: Top-3 critical inline style fixes for light/dark theme compatibility
- **Frameless Mode Stub**: Feature flag added for future frameless window mode implementation

### Installation

**RPM (Fedora 43+)**
```bash
sudo dnf install https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v21.0.0/loofi-fedora-tweaks-21.0.0-1.noarch.rpm
```

**Build from Source**
```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
./build_rpm.sh
```

### Testing

All 1681 tests passing with new layout regression coverage.

```bash
PYTHONPATH=loofi-fedora-tweaks python3 -m pytest tests/ -v
```

---

**Full Changelog**: https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/CHANGELOG.md
