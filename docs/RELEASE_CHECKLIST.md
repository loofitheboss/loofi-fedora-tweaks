# Release Checklist

Use this before tagging a new release.

1. Update version in `loofi-fedora-tweaks/version.py`, `loofi-fedora-tweaks.spec`, and any install URLs.
2. Update `CHANGELOG.md` and `release_notes.md`.
3. Run tests:
   - `PYTHONPATH=loofi-fedora-tweaks python3 -m pytest tests/ -v`
4. Build RPM locally:
   - `./build_rpm.sh`
5. Smoke‑test the CLI:
   - `loofi --version`
   - `loofi doctor`
   - `loofi plugins list`
6. Tag and push:
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
