# Release Checklist

Use this checklist before bumping a version. The CI pipeline handles tagging and publishing automatically.

---

## 1. Version Alignment

Update version in **all three files** (must match):

1. `loofi-fedora-tweaks/version.py` — `__version__`, `__version_codename__`
2. `loofi-fedora-tweaks.spec` — `Version:`
3. `pyproject.toml` — `version` field

Quick verify:

```bash
python3 -c "import sys; sys.path.insert(0,'loofi-fedora-tweaks'); from version import __version__; print(__version__)"
grep '^Version:' loofi-fedora-tweaks.spec | awk '{print $2}'
grep '^version' pyproject.toml
```

---

## 2. Documentation

- [ ] `CHANGELOG.md` — New version entry at top
- [ ] `docs/releases/RELEASE-NOTES-vX.Y.Z.md` — Detailed release notes
- [ ] `README.md` — Update "What Is New" section, version badge, test count
- [ ] `ROADMAP.md` — Mark version as DONE, add NEXT placeholder
- [ ] `docs/USER_GUIDE.md` — Update if behavior changed
- [ ] `docs/TROUBLESHOOTING.md` — Update if new failure modes added

---

## 3. Pre-Push Validation

Run locally before pushing:

```bash
# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722

# Adapter sync check
python3 scripts/sync_ai_adapters.py --check

# Tests (subset — full suite runs in CI)
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -x --tb=short -q

# Release docs validation
python3 scripts/check_release_docs.py
```

---

## 4. Push to Master

The **Auto Release Pipeline** runs automatically on every push to `master`:

```
push to master
  → validate (version alignment + packaging scripts)
  → adapter_drift, lint, typecheck, test, security, docs_gate (parallel)
  → build (RPM in Fedora 43 container)
  → auto_tag (creates vX.Y.Z tag if missing)
  → release (publishes GitHub Release with RPM artifact)
```

### Key behaviors

- **Auto-tag**: Creates `vX.Y.Z` tag from `version.py` if it doesn't exist
- **Idempotent release**: Skips publish if release already exists for that tag
- **Non-blocking gates**: `typecheck` and `test` use `continue-on-error: true` (soft gates)
- **Hard gates**: `validate`, `adapter_drift`, `lint`, `docs_gate` must pass for build to proceed

### If the pipeline fails

1. Check the [Actions page](https://github.com/loofitheboss/loofi-fedora-tweaks/actions/workflows/auto-release.yml) for the failing job
2. Fix the issue locally and push again — the pipeline is idempotent
3. If the tag already exists but release failed, the release job will create it on next push

---

## 5. Post-Release Verification

After the pipeline completes:

```bash
# Check release exists
gh release view vX.Y.Z

# Check RPM artifact is attached
gh release view vX.Y.Z --json assets -q '.assets[].name'

# Verify tag points to correct commit
git log --oneline -1 vX.Y.Z
```

Or check the [releases page](https://github.com/loofitheboss/loofi-fedora-tweaks/releases).

---

## 6. Manual Release (Fallback)

Use only if the automated pipeline can't handle a specific scenario:

```bash
# Trigger manual release via GitHub Actions
gh workflow run auto-release.yml -f version=X.Y.Z

# Or dry run first
gh workflow run auto-release.yml -f version=X.Y.Z -f dry_run=true
```

---

## CI Pipeline Architecture

### auto-release.yml (Full Release)

```
validate ─────────────────────────────┐
adapter_drift ─┐                      │
lint ──────────┤                      │
typecheck* ────┤  (parallel gates)    ├── build ── auto_tag ── release
docs_gate ─────┤                      │
test* ─────────┤                      │
security ──────┘                      │
                                      │
* = continue-on-error (soft gate)     │
```

### ci.yml (PR/Push Checks)

Runs on every push/PR. Same gates as auto-release minus build/tag/release.
Includes additional packaging jobs: `package_flatpak`, `package_appimage`, `package_sdist`.

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Release not published | GITHUB_TOKEN tags don't trigger new runs | Pipeline handles this — release runs on same push as auto_tag |
| Build skipped | Hard gate failed (lint, validate, adapter_drift, docs_gate) | Fix the failing gate and push again |
| Duplicate release attempt | Multiple pushes for same version | Pipeline checks if release exists first and skips |
| Version mismatch | `version.py` ≠ `.spec` ≠ `pyproject.toml` | Update all three files to match |
