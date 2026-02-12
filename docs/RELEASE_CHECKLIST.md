# Release Checklist

Use this before tagging a new release.

## Version Bump

1. Update version in three files (must stay in sync):
   - `loofi-fedora-tweaks/version.py` — `__version__` and `__version_codename__`
   - `loofi-fedora-tweaks.spec` — `Version:`
   - `build_rpm.sh` — `VERSION=`

## Documentation

2. Update `CHANGELOG.md` with full feature list.
3. Update versioned release notes in `docs/releases/` and keep legacy notes in sync if still used.
4. Update `README.md` — version badges, What's New section, CLI commands, test count.
5. Update `docs/USER_GUIDE.md` — new feature sections, CLI reference, version header.
6. Update `docs/CONTRIBUTING.md` — project structure, test counts.
7. Update `docs/TROUBLESHOOTING.md` — add troubleshooting for new features.
8. Update `docs/PLUGIN_SDK.md` — bump `min_app_version` examples if needed.

## Testing

9. Run full test suite:
   ```bash
   PYTHONPATH=loofi-fedora-tweaks python3 -m pytest tests/ -v
   ```
10. Verify all new tests pass.

## Build

11. Build RPM locally:
    ```bash
    bash scripts/build_rpm.sh
    ```
12. Verify RPM exists in `rpmbuild/RPMS/noarch/`.

## Smoke Test

13. Test CLI commands:
    ```bash
    loofi --version
    loofi doctor
    loofi plugins list
    loofi tuner analyze
    loofi snapshot backends
    loofi logs errors
    ```

## Release

14. Commit all changes:
    ```bash
    git add -A && git commit -m "Release vX.Y.Z Codename"
    ```
15. Create annotated tag:
    ```bash
    git tag -a vX.Y.Z -m "vX.Y.Z Codename - summary"
    ```
16. Push to origin (triggers CI release workflow):
    ```bash
    git push origin master --tags
    ```
17. Wait for CI to create GitHub release, then update with full notes:
    ```bash
    gh release edit vX.Y.Z --title 'vX.Y.Z "Codename"' --latest --notes "..."
    ```
18. Verify release:
    ```bash
    gh release list --limit 3
    ```
