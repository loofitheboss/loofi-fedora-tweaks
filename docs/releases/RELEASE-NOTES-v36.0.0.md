# v36.0.0 "Horizon" — Release Notes

**Release date**: Unreleased
**Codename**: Horizon
**Focus**: Testing & CI Hardening

---

## What's New

v36.0.0 "Horizon" is a stabilization release focused on testing infrastructure, CI pipeline reliability, and build system improvements.

### CI Pipeline Hardening

- Fixed test assertions to match timeout-enforced subprocess calls introduced in v35.0.0
- Synchronized `pyproject.toml` version with `version.py` and `.spec` to prevent sdist build mismatches
- Added KDE SDK installation step for Flatpak builds in CI
- Improved overall CI reliability and reduced false failures

### Build System Improvements

- Source distribution (sdist) now builds correctly with consistent version across all metadata files
- Flatpak build pipeline updated with proper SDK dependency resolution

---

## Upgrade Notes

Standard upgrade from v35.0.0 — no breaking changes or migration steps required.

```bash
# RPM upgrade
sudo dnf upgrade loofi-fedora-tweaks

# Or from source
git pull && ./run.sh
```

---

## Known Issues

None at this time.
