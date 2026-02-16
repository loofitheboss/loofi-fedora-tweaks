# Release Checklist

Use this checklist before bumping a version. The CI pipeline handles tagging and publishing automatically.

---

## 0. Version Bump (Automated)

Run the bump script — it handles files, scaffolding, and warnings:

```bash
python3 scripts/bump_version.py 41.0.0 --codename "Scaffold"

# Preview first:
python3 scripts/bump_version.py 41.0.0 --codename "Scaffold" --dry-run
```

The script cascades across **7 targets**:

| # | Target | Field |
|---|--------|-------|
| 1 | `loofi-fedora-tweaks/version.py` | `__version__`, `__version_codename__` |
| 2 | `loofi-fedora-tweaks.spec` | `Version:` |
| 3 | `pyproject.toml` | `version` |
| 4 | `.workflow/specs/.race-lock.json` | `target_version` |
| 5 | `.project-stats.json` | regenerated via `project_stats.py` |
| 6 | AI adapter templates | re-rendered via `sync_ai_adapters.py` |
| 7 | `docs/releases/RELEASE-NOTES-vX.Y.Z.md` | scaffolded if missing |

It also **scans `tests/` for hardcoded version strings** and warns if any are found.

Quick verify (after bump):

```bash
python3 -c "import sys; sys.path.insert(0,'loofi-fedora-tweaks'); from version import __version__; print(__version__)"
grep '^Version:' loofi-fedora-tweaks.spec | awk '{print $2}'
grep '^version' pyproject.toml
```

---

## 1. Documentation

After running the bump script, fill in the scaffolded files:

- [ ] `docs/releases/RELEASE-NOTES-vX.Y.Z.md` — Fill in the TODO placeholders
- [ ] `CHANGELOG.md` — New version entry at top
- [ ] `README.md` — Update "What Is New" section, version badge, test count
- [ ] `ROADMAP.md` — Mark version as DONE, add NEXT placeholder
- [ ] `docs/USER_GUIDE.md` — Update if behavior changed
- [ ] `docs/TROUBLESHOOTING.md` — Update if new failure modes added

---

## 2. Pre-Push Validation

Run locally before pushing:

```bash
# Release docs gate (same check CI runs)
python3 scripts/check_release_docs.py

# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203

# Adapter sync check
python3 scripts/sync_ai_adapters.py --check

# Tests (subset — full suite runs in CI)
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -x --tb=short -q
```

The `check_release_docs.py` script validates:

| Check | What it verifies |
|-------|------------------|
| Version sync | `version.py` == `.spec` == `pyproject.toml` |
| CHANGELOG | Entry `## [X.Y.Z]` exists in `CHANGELOG.md` |
| README | `README.md` exists and is non-empty |
| Release notes | `docs/releases/RELEASE-NOTES-vX.Y.Z.md` exists and is non-empty |
| Stale tests | No `tests/test_*.py` files hardcode the current version or codename |

---

## 3. Push to Master

The **Auto Release Pipeline** runs automatically on every push to `master`:

```
push to master
  -> validate (version alignment + packaging scripts)
  -> adapter_drift, lint, typecheck, test, security, docs_gate (parallel)
  -> build (RPM in Fedora 43 container)
  -> auto_tag (creates vX.Y.Z tag if missing)
  -> release (publishes GitHub Release with RPM artifact)
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

## 4. Post-Release Verification

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

## 5. Manual Release (Fallback)

Use only if the automated pipeline can't handle a specific scenario:

```bash
# Trigger manual release via GitHub Actions
gh workflow run auto-release.yml -f version=X.Y.Z

# Or dry run first
gh workflow run auto-release.yml -f version=X.Y.Z -f dry_run=true
```

---

## Anti-Patterns (Do Not)

These patterns caused CI failures in v40.0.0 and are now caught automatically:

| Anti-Pattern | Why It Breaks | Automated Guard |
|-------------|---------------|-----------------|
| Hardcoded version in tests (`assertEqual(__version__, "40.0.0")`) | Fails on every bump | `check_release_docs.py` stale test scan + `bump_version.py` warning |
| Missing release notes | `docs_gate` CI job fails | `bump_version.py` scaffolds automatically |
| `pyproject.toml` version drift | Version mismatch | `bump_version.py` updates it + `check_release_docs.py` validates |
| Per-release test files (`test_v38_clarity.py`) | Hardcode old version, break on bump | Don't create them; use version-agnostic assertions |

### Safe version test patterns

```python
# GOOD: version-agnostic assertions that survive bumps
def test_version_is_nonempty(self):
    from version import __version__
    self.assertTrue(len(__version__) > 0)

def test_version_format(self):
    from version import __version__
    parts = __version__.split(".")
    self.assertEqual(len(parts), 3)
    for part in parts:
        self.assertTrue(part.isdigit())

# BAD: breaks on every version bump
def test_version_is_current(self):
    self.assertEqual(__version__, "40.0.0")  # stale next release!
```

---

## CI Pipeline Architecture

### auto-release.yml (Full Release)

```
validate -----------------------------------------+
adapter_drift --+                                  |
lint -----------+                                  |
typecheck* -----+  (parallel gates)    +--> build --> auto_tag --> release
docs_gate ------+                      |
test* ----------+                      |
security -------+----------------------+

* = continue-on-error (soft gate)
```

### ci.yml (PR/Push Checks)

Runs on every push/PR. Same gates as auto-release minus build/tag/release.
Includes additional packaging jobs: `package_flatpak`, `package_appimage`, `package_sdist`.

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Release not published | GITHUB_TOKEN tags don't trigger new runs | Pipeline handles this -- release runs on same push as auto_tag |
| Build skipped | Hard gate failed (lint, validate, adapter_drift, docs_gate) | Fix the failing gate and push again |
| Duplicate release attempt | Multiple pushes for same version | Pipeline checks if release exists first and skips |
| Version mismatch | `version.py` != `.spec` != `pyproject.toml` | Run `bump_version.py` (handles all three) |
| docs_gate fails | Missing release notes or stale test assertions | Run `bump_version.py` (scaffolds notes, warns on stale tests) |
