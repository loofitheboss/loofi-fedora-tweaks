# Loofi Serious Clean Icon Pack

This pack provides a professional line icon set that replaces emoji-driven UI labels with consistent semantic assets.

This README is mirrored in both icon roots:

- `assets/icons/`
- `loofi-fedora-tweaks/assets/icons/`

## Folder Layout

- `svg/` source icons (24x24 viewport)
- `png/16/` raster export at 16x16
- `png/20/` raster export at 20x20
- `png/24/` raster export at 24x24
- `png/32/` raster export at 32x32
- `icon-map.json` semantic name to asset map

## Style Rules

- Grid: all icons align to a 24x24 viewport.
- Stroke: consistent `2.0` stroke width, round joins, round caps.
- Visual language: flat line symbols with minimal detail for clarity at small sizes.
- Color: icons are neutral source assets. UI applies theme-aware tinting at runtime for an integrated look.
- Geometry: avoid decorative elements and keep enterprise/system-admin metaphors.

## Runtime Behavior

- Runtime lookup and tinting is centralized in `loofi-fedora-tweaks/ui/icon_pack.py`.
- Icon roots are searched in this order:
  - `assets/icons/`
  - `loofi-fedora-tweaks/assets/icons/`
- Semantic IDs resolve through `icon-map.json` with SVG-first loading and PNG fallback sizes (`16`, `20`, `24`, `32`).
- Sidebar/quick-actions integrations use 17px icon sizing with selection-aware tint variants in sidebar rows.

## Replacement Mapping

- Home navigation -> `home`
- Bell / notifications -> `notifications`
- Sidebar categories:
  - System -> `overview-dashboard`
  - Packages -> `packages-software`
  - Hardware -> `hardware-performance`
  - Network -> `network-connectivity`
  - Security -> `security-shield`
  - Appearance -> `appearance-theme`
  - Tools -> `developer-tools`
  - Maintenance -> `maintenance-health`
- Dashboard metric cards:
  - CPU -> `cpu-performance`
  - RAM -> `memory-ram`
  - Network -> `network-traffic`
  - Storage -> `storage-disk`
  - Status OK -> `status-ok`
  - Terminal -> `terminal-console`
- Action buttons:
  - Install -> `install`
  - Update -> `update`
  - Cleanup -> `cleanup`
  - Restart -> `restart`
  - Logs -> `logs`
