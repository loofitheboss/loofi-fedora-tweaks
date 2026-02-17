# Desktop & UI Skills

## Theme Management
- **QSS theming** — Modern dark/light themes via `assets/modern.qss`
- **System theme** — Detect and follow system color scheme
- **Custom styling** — Per-widget styling with `setObjectName()`

**Assets:** `assets/modern.qss`
**UI:** Settings Tab

## GNOME Shell Extensions
- **Extension discovery** — Browse available GNOME Shell extensions
- **Install/Remove** — Manage extension lifecycle
- **Enable/Disable** — Toggle extensions without removal
- **Update check** — Check for extension updates

**Modules:** `utils/extension_manager.py`
**UI:** Extensions Tab
**CLI:** `extension`

## Window Tiling
- **KWin tiling** — Configure KDE KWin tiling layouts
- **Tiling presets** — Quick-switch tiling configurations
- **Custom layouts** — Define custom window tiling grids

**Modules:** `utils/kwin_tiling.py`, `utils/tiling.py`
**UI:** Desktop Tab

## Display Configuration
- **Multi-monitor** — Configure multi-display layouts
- **Resolution** — Set display resolution and refresh rate
- **Wayland support** — Wayland-specific display utilities
- **Scaling** — Configure HiDPI display scaling

**Modules:** `utils/wayland_display.py`
**UI:** Desktop Tab
**CLI:** `display`

## Desktop Environment Detection
- **DE detection** — Identify GNOME, KDE, Xfce, etc.
- **Session type** — Detect Wayland vs X11
- **Feature availability** — Check DE-specific feature support

**Modules:** `utils/desktop_utils.py`

## Notification Center
- **Desktop notifications** — Send system notifications via D-Bus
- **Notification rules** — Configure notification filtering and grouping
- **History** — Browse notification history

**Modules:** `utils/notification_center.py`
**UI:** Settings Tab

## Audio Management
- **PulseAudio/PipeWire** — Manage audio server and devices
- **Audio restart** — Restart audio subsystem to fix issues
- **Device switching** — Switch default audio input/output

**Modules:** `utils/pulse.py`, `core/executor/operations.py` (TweakOps)
**UI:** Hardware Tab

## First-Run Wizard
- **Profile setup** — Guided initial configuration
- **Hardware detection** — Auto-detect and optimize for hardware
- **Profile persistence** — Save to `~/.config/loofi-fedora-tweaks/profile.json`

**Modules:** `ui/wizard.py`
