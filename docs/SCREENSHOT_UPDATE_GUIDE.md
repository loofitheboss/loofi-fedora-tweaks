# Screenshot Update Guide for Loofi Fedora Tweaks v41.0.0

## Current Status

Screenshots in this repository were last captured at **v32.0.0 "Abyss"** (approximately 9 months ago). They need to be updated to reflect the current **v41.0.0 "Coverage"** release.

## What Changed Since v32

Between v32 and v41, several UI changes occurred:

| Version | Changes |
|---------|---------|
| v37 "Convergence" | ✨ New **Extensions** and **Backup** tabs |
| v38 "Precision" | Dashboard widget redesign, responsive layouts |
| v39 "Prism" | QSS objectName migration (cleaner styling) |
| v40 "Foundation" | Security UI improvements |
| v41 "Coverage" | No UI changes (testing release) |

**Bottom line**: Screenshots should show v37+ features (new tabs) and v38+ design improvements.

## Screenshot Inventory

### Priority 1 (Critical - Referenced in README.md)

These screenshots are visible on the main repository page and in user guides:

| File | Location | Tab Path | Status |
|------|----------|----------|--------|
| `home-dashboard.png` | docs/images/user-guide/ | Overview > Home | 🔴 Needs update |
| `system-monitor.png` | docs/images/user-guide/ | Overview > System Monitor | 🔴 Needs update |
| `maintenance-updates.png` | docs/images/user-guide/ | Manage > Maintenance | 🔴 Needs update |

### Priority 2 (Important - Referenced in USER_GUIDE.md)

| File | Location | Tab Path | Status |
|------|----------|----------|--------|
| `network-overview.png` | docs/images/user-guide/ | Network & Security > Network | 🔴 Needs update |
| `security-privacy.png` | docs/images/user-guide/ | Network & Security > Security | 🔴 Needs update |
| `ai-lab-models.png` | docs/images/user-guide/ | Developer > AI Lab | 🔴 Needs update |
| `community-presets.png` | docs/images/user-guide/ | Automation > Community | 🔴 Needs update |
| `community-marketplace.png` | docs/images/user-guide/ | Automation > Community | 🔴 Needs update |
| `settings-appearance.png` | docs/images/user-guide/ | Personalize > Settings | 🔴 Needs update |

### Priority 3 (Optional - New Features)

New tabs added in v37 that should have screenshots:

| File | Tab Path | Notes |
|------|----------|-------|
| `extensions-tab.png` | Manage > Extensions | New in v37 |
| `backup-tab.png` | Manage > Backup | New in v37 |
| `diagnostics-tab.png` | Developer > Diagnostics | Existing, not yet captured |
| `agents-tab.png` | Automation > Agents | Existing, not yet captured |

### Legacy Files (To Review)

These files exist but may be outdated or superseded:

| File | Location | Status |
|------|----------|--------|
| `boot_tab.png` | docs/ | ⚠️ Check if still referenced |
| `dashboard.png` | docs/ | ⚠️ Superseded by home-dashboard.png? |
| `marketplace.png` | docs/ | ⚠️ Superseded by community-marketplace.png? |

## How to Capture Screenshots

### Option 1: Automated Guide (Recommended)

Run the screenshot capture assistant:

```bash
cd /home/runner/work/loofi-fedora-tweaks/loofi-fedora-tweaks
python scripts/capture_screenshots.py
```

This provides:
- ✅ Status check of existing screenshots
- ✅ Step-by-step instructions for each capture
- ✅ Navigation path for each tab
- ✅ Post-processing commands
- ✅ Verification checklist

### Option 2: Manual Capture

1. **Setup**:
   ```bash
   # Launch app
   ./run.sh
   # OR from source
   PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py
   ```

2. **Window configuration**:
   - Size: 1280x800 or 1440x900 (not maximized)
   - Theme: Abyss Dark (default, check Settings > Appearance)

3. **For each screenshot**:
   - Navigate to the tab path (e.g., "Overview > Home")
   - Wait for content to load completely
   - Capture using your preferred tool:
     - GNOME: PrtSc or GNOME Screenshot
     - KDE: Spectacle (`spectacle -r`)
     - CLI: `scrot -s`, `flameshot gui`, or `import` (ImageMagick)
   - Save with the exact filename from the tables above
   - Save to: `docs/images/user-guide/FILENAME.png`

4. **Optimize**:
   ```bash
   cd docs/images/user-guide/
   optipng -o5 *.png
   # OR
   pngcrush -brute *.png
   ```

5. **Verify**:
   ```bash
   # Check file sizes (should be < 200KB each)
   ls -lh docs/images/user-guide/*.png
   
   # Test rendering in docs
   grip README.md
   grip docs/USER_GUIDE.md
   ```

## Screenshot Guidelines

### Technical Requirements

- **Format**: PNG (lossless)
- **Size**: Target < 200KB after optimization
- **Dimensions**: Consistent width (1280 or 1440 preferred)
- **DPI**: 72-96 DPI (web standard)
- **Color**: RGB (not CMYK)

### Visual Guidelines

- **Theme**: Use Abyss Dark (the default dark theme)
- **Window**: Not maximized, consistent size across all screenshots
- **Content**: Show actual data, not just empty states where possible
- **Focus**: Ensure the relevant tab content is visible and clear
- **Cursors**: Avoid capturing mouse cursors unless demonstrating interaction
- **Privacy**: Do not include personal information (real hostnames, IPs, etc.)

### Naming Convention

Use exact filenames from the inventory tables. Format: `lowercase-with-hyphens.png`

Examples:
- ✅ `home-dashboard.png`
- ✅ `community-marketplace.png`
- ❌ `Home_Dashboard.png`
- ❌ `community marketplace.png`

## Post-Capture Checklist

After capturing all screenshots:

- [ ] All 9 priority 1-2 screenshots captured
- [ ] Images optimized (`optipng` or `pngcrush`)
- [ ] File sizes verified (< 200KB each)
- [ ] Consistent dimensions verified
- [ ] Documentation renders correctly:
  - [ ] README.md (3 screenshots)
  - [ ] docs/USER_GUIDE.md (8 screenshots)
  - [ ] docs/BEGINNER_QUICK_GUIDE.md (1 screenshot)
  - [ ] docs/ADVANCED_ADMIN_GUIDE.md (5 screenshots)
- [ ] Legacy files in `docs/` reviewed and cleaned up
- [ ] Commit message: "docs: update screenshots to v41.0.0"

## Updating This Guide

When screenshots are successfully updated:

1. Update `docs/images/user-guide/README.md`:
   - Change status from "🔴 Needs update" to "✅ Current"
   - Update "Last verified" date
   
2. Update this file's status tables

3. Archive this guide if all screenshots are current

## Alternative: Screenshot Automation (Future)

For fully automated screenshot capture in CI:

- Use PyAutoGUI or similar automation
- Requires Xvfb or similar virtual display
- Can be added to CI pipeline for release builds
- See: `scripts/capture_screenshots.py --auto` (not yet implemented)

## Questions?

- Check the screenshot README: `docs/images/user-guide/README.md`
- Run the assistant: `python scripts/capture_screenshots.py`
- Review docs: `docs/USER_GUIDE.md` for context on each tab

## Logo and Icon Files

These are **not** screenshots but designed assets (no update needed):

- `loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png` (512x512, 162KB)
- `loofi-fedora-tweaks/assets/icon.png` (512x512, 162KB)

Status: ✅ Current for v41.0.0

These only need updating if there's a rebranding initiative.
