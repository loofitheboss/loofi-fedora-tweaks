````skill
---
name: package
description: Build and verify distribution packages (RPM, Flatpak, AppImage, sdist) for the current version.
---

# Package Phase (P6)

## Steps
1. Verify version alignment:
   ```bash
   python -c "import sys; sys.path.insert(0,'loofi-fedora-tweaks'); from version import __version__; print(__version__)"
   grep '^Version:' loofi-fedora-tweaks.spec | awk '{print $2}'
   ```
2. Lint check:
   ```bash
   flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
   ```
3. Full test suite:
   ```bash
   PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --tb=short
   ```
4. Build RPM:
   ```bash
   bash scripts/build_rpm.sh
   ls rpmbuild/RPMS/noarch/
   ```
5. Build sdist:
   ```bash
   bash scripts/build_sdist.sh
   ```
6. Generate workflow reports:
   ```bash
   python3 scripts/generate_workflow_reports.py
   ```
7. Generate project stats:
   ```bash
   python3 scripts/project_stats.py
   ```

## Optional Builds
- Flatpak: `bash scripts/build_flatpak.sh` (requires flatpak-builder)
- AppImage: `bash scripts/build_appimage.sh`

## Verification
- RPM installs cleanly in a Fedora container
- Version string in built package matches source
- No missing files in RPM spec %files section

## Rules
- Must complete P5 (Document) before starting P6
- All build scripts must be executable (`chmod +x`)
- Include workflow reports in commit: `git add .workflow/reports/`
- Reference `.github/workflow/prompts/package.md` for full prompt

````
