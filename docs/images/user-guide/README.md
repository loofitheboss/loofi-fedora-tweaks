# User Guide Screenshot Catalog

Canonical screenshot assets for user-facing docs.

**Last verified**: v41.0.0 "Coverage"

**Status**: 🔴 Screenshots require updating

Screenshots were last captured at v32.0.0 "Abyss" (9 months ago) and **need to be
recaptured** to reflect the current v41.0.0 UI:

- Theme refinements from v34-v39
- QSS objectName migration from v39
- New tab layouts from v37 (Extensions, Backup tabs)
- Updated dashboard widgets from v38-v40
- Coverage reporting UI from v41

**Automation Available**: Use `python scripts/capture_screenshots.py` for guided
manual capture process with detailed instructions and status checking.

## Current Files

- `home-dashboard.png` -- Overview/Home
- `system-monitor.png` -- Overview/System Monitor
- `maintenance-updates.png` -- Manage/Maintenance updates workflow
- `network-overview.png` -- Network tab overview
- `security-privacy.png` -- Security & Privacy tab
- `ai-lab-models.png` -- Developer/AI Lab models view
- `community-presets.png` -- Automation/Community presets view
- `community-marketplace.png` -- Automation/Community marketplace view
- `settings-appearance.png` -- Personalize/Settings appearance

## Referenced By

- `docs/USER_GUIDE.md`
- `docs/BEGINNER_QUICK_GUIDE.md`
- `docs/ADVANCED_ADMIN_GUIDE.md`
- `README.md`

## Quick Start

**Automated Guide**:
```bash
python scripts/capture_screenshots.py
```

This script provides:
- ✅ Step-by-step navigation instructions for each screenshot
- ✅ Status check of existing screenshots
- ✅ Post-processing commands for optimization
- ✅ Verification checklist

**Content Guidelines**: See [`../SCREENSHOT_CONTENT_GUIDE.md`](../SCREENSHOT_CONTENT_GUIDE.md) for
detailed specifications of what each screenshot should display.

## Manual Regeneration Instructions

If you prefer manual capture without the script:

1. **Launch the app**: 
   ```bash
   ./run.sh
   # OR
   PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py
   ```

2. **Window setup**:
   - Set consistent size: 1280x800 or 1440x900 (recommended)
   - Do NOT maximize window (for consistent sizing)
   - Use default dark theme (Abyss Dark / `modern.qss`)

3. **Screenshot tool**:
   - GNOME: Press PrtSc or use GNOME Screenshot
   - KDE: Spectacle (`spectacle -r` for region capture)
   - CLI: `scrot`, `flameshot`, or `import` (ImageMagick)

4. **Capture each tab** (see table below)

5. **Save with exact filename** to avoid breaking doc references

6. **Optimize images**:
   ```bash
   cd docs/images/user-guide/
   optipng -o5 *.png
   # OR
   pngcrush -brute *.png
   ```

7. **Verify rendering**:
   - Check file sizes: `ls -lh *.png` (should be < 200KB each)
   - Preview in markdown: `grip README.md` or GitHub preview
   - Test all documentation files render correctly

### Tabs to screenshot (priority order)

| Screenshot | Navigate To | Notes |
|------------|-------------|-------|
| `home-dashboard.png` | Overview > Home | Show health score, quick actions |
| `system-monitor.png` | Overview > System Monitor | Show CPU/RAM/process data |
| `maintenance-updates.png` | Manage > Maintenance > Updates | Show update workflow |
| `network-overview.png` | Network & Security > Network | Show connections view |
| `security-privacy.png` | Network & Security > Security | Show security score |
| `ai-lab-models.png` | Developer > AI Lab | Show models list |
| `community-presets.png` | Automation > Community | Show presets tab |
| `community-marketplace.png` | Automation > Community | Show marketplace tab |
| `settings-appearance.png` | Personalize > Settings | Show appearance options |

### Additional screenshots to consider for v41

- `extensions-tab.png` -- Manage > Extensions (new in v37)
- `backup-tab.png` -- Manage > Backup (new in v37)
- `diagnostics-tab.png` -- Developer > Diagnostics
- `agents-tab.png` -- Automation > Agents

## UI Changes Since v32 (When Screenshots Were Last Captured)

**v33-v36**: Base stabilization, no major UI changes

**v37 "Convergence"**:
- ✨ New **Extensions** tab under Manage
- ✨ New **Backup** tab under Manage
- Tab organization improvements

**v38 "Precision"**:
- Dashboard widgets redesign
- Better responsive layouts

**v39 "Prism"**:
- 🎨 QSS objectName migration (cleaner CSS targeting)
- Services layer integration (no direct UI impact)

**v40 "Foundation"**:
- Security hardening (UI prompts may look slightly different)
- Subprocess timeout enforcement

**v41 "Coverage"** (current):
- No UI changes (pure testing and CI release)

**Priority**: Screenshots should reflect v37+ changes, especially new tabs.

## Legacy Screenshots (May Need Removal)

The following screenshots exist in `docs/` root (not in `images/user-guide/`):

- `docs/boot_tab.png` (57KB) - May be outdated, check if still referenced
- `docs/dashboard.png` (36KB) - Likely superseded by `home-dashboard.png`
- `docs/marketplace.png` (64KB) - Likely superseded by `community-marketplace.png`

**Action needed**: 
1. Search codebase for references: `grep -r "boot_tab\|dashboard\.png\|marketplace\.png" docs/`
2. If unreferenced, consider moving to archive or removing
3. If referenced, update with new captures or redirect to user-guide images

## Logo and Icon Assets

Application branding assets in `loofi-fedora-tweaks/assets/`:

- `loofi-fedora-tweaks.png` (512x512, 162KB) - Main logo, referenced in README
- `icon.png` (512x512, 162KB) - App icon

**Status**: ✅ Logos are current and appropriate for v41.0.0

These are not screenshots but generated/designed assets. No update needed unless
rebranding is desired.
