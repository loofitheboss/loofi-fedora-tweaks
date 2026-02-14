# CI/CD Pipeline

Continuous Integration and Deployment pipeline for Loofi Fedora Tweaks.

---

## Pipeline Overview

Every push to `master` and every pull request runs through automated pipelines:

| Pipeline | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI** | `.github/workflows/ci.yml` | Push/PR | Lint, typecheck, test, security, packaging |
| **Auto Release** | `.github/workflows/auto-release.yml` | Push to master | Full release: validate → build → tag → publish |
| **PR Security Bot** | `.github/workflows/pr-security-bot.yml` | PR | Security scans (Bandit, pip-audit, Trivy, secrets) |
| **Publish Wiki** | `.github/workflows/publish-wiki.yml` | Wiki changes | Auto-publish wiki pages |

---

## CI Pipeline (`.github/workflows/ci.yml`)

Runs on every **push** and **pull request**.

### Pipeline Steps

```
1. Lint (flake8)
   ↓
2. Type Check (mypy)
   ↓
3. Test (pytest)
   ↓
4. Security Scan (bandit)
   ↓
5. Packaging (build RPM in Fedora 43 container)
```

### Jobs

#### 1. Lint

```yaml
- name: Lint with flake8
  run: |
    flake8 loofi-fedora-tweaks/ --max-line-length=150 \
      --ignore=E501,W503,E402,E722
```

**Rules:**
- Max line length: 150
- Ignored: E501, W503, E402, E722

#### 2. Type Check

```yaml
- name: Type check with mypy
  run: |
    mypy loofi-fedora-tweaks/ --ignore-missing-imports \
      --no-error-summary --warn-return-any
```

**Goal**: 0 type errors (achieved in v33.0.0)

#### 3. Test

```yaml
- name: Run tests
  run: |
    PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v
```

**Requirements:**
- 4349+ tests passing
- 75%+ coverage
- 0 failures

#### 4. Security Scan

```yaml
- name: Security scan with bandit
  run: |
    bandit -r loofi-fedora-tweaks/ -ll -ii \
      --skip B103,B104,B108,B310,B404,B603,B602
```

**Skipped rules:**
- B404, B603, B602 — subprocess patterns (safe via PrivilegedCommand)
- B103, B104, B108, B310 — intentional patterns

#### 5. Packaging

```yaml
- name: Build RPM
  run: |
    bash scripts/build_rpm.sh
```

Runs in **Fedora 43 container** to ensure package builds correctly.

---

## Auto Release Pipeline (`.github/workflows/auto-release.yml`)

Runs on **push to master** with automatic tagging and release publishing.

### Pipeline Flow

```
Push to master
  ↓
Validate (version alignment, packaging scripts)
  ↓
Parallel Gates:
  - Adapter Drift Check
  - Lint
  - Type Check
  - Test
  - Security
  - Docs Gate
  ↓
Build (RPM in Fedora 43 container)
  ↓
Auto Tag (create vX.Y.Z tag if missing)
  ↓
Release (publish GitHub Release with RPM artifact)
```

### Jobs

#### 1. Validate

Checks:
- Version sync across `version.py`, `.spec`, and `pyproject.toml`
- Packaging scripts exist and are executable
- CHANGELOG has unreleased section

#### 2. Parallel Gates

Six jobs run in parallel:

| Job | Purpose |
|-----|---------|
| **adapter_drift** | Check AI adapter file sync |
| **lint** | flake8 code quality check |
| **typecheck** | mypy type validation |
| **test** | Full test suite (4349+ tests) |
| **security** | Bandit security scan |
| **docs_gate** | Validate documentation |

All must pass before proceeding to build.

#### 3. Build

Builds RPM package in Fedora 43 container:

```yaml
- name: Build RPM
  run: bash scripts/build_rpm.sh
  
- name: Upload artifact
  uses: actions/upload-artifact@v4
  with:
    name: rpm-package
    path: rpmbuild/RPMS/noarch/*.rpm
```

#### 4. Auto Tag

Creates git tag if not already present:

```yaml
- name: Create tag
  if: steps.check_tag.outputs.tag_exists == 'false'
  run: |
    git tag v${{ needs.validate.outputs.version }}
    git push origin v${{ needs.validate.outputs.version }}
```

Tag format: `vX.Y.Z` (e.g., `v40.0.0`)

#### 5. Release

Publishes GitHub Release with:
- Release title: `vX.Y.Z "Codename"`
- Release notes from `docs/releases/RELEASE-NOTES-vX.Y.Z.md`
- RPM artifact attached

```yaml
- name: Create Release
  uses: softprops/action-gh-release@v2
  with:
    tag_name: v${{ needs.validate.outputs.version }}
    name: v${{ needs.validate.outputs.version }} "${{ needs.validate.outputs.codename }}"
    body_path: docs/releases/RELEASE-NOTES-v${{ needs.validate.outputs.version }}.md
    files: rpmbuild/RPMS/noarch/*.rpm
```

---

## Manual Release

Use **workflow_dispatch** for manual control:

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release (e.g., 40.0.0)'
        required: true
      dry_run:
        description: 'Dry run (validate without publishing)'
        type: boolean
        default: false
```

### Trigger Manual Release

1. Go to **Actions** → **Auto Release** → **Run workflow**
2. Enter version number (e.g., `40.0.0`)
3. Set `dry_run: true` to validate without publishing
4. Click **Run workflow**

---

## PR Security Bot (`.github/workflows/pr-security-bot.yml`)

Runs on every **pull request** to master.

### Security Scans

| Tool | Purpose |
|------|---------|
| **Bandit** | Python SAST (Static Application Security Testing) |
| **pip-audit** | Check for known vulnerabilities in dependencies |
| **Trivy** | Container and filesystem vulnerability scanner |
| **detect-secrets** | Scan for accidentally committed secrets |

### Summary Comment

Bot posts a comment on the PR with:
- ✅ Scan results (pass/fail)
- 🔍 Findings count per tool
- 📊 Severity breakdown (critical, high, medium, low)
- 🔗 Links to full reports (artifacts)

**Example:**

```
🔒 Security Scan Results

✅ Bandit: 0 issues
✅ pip-audit: 0 vulnerabilities
✅ Trivy: 0 vulnerabilities
✅ detect-secrets: 0 secrets detected

Full reports available in workflow artifacts.
```

---

## Build Commands

### Build RPM

```bash
bash scripts/build_rpm.sh
```

**Output**: `rpmbuild/RPMS/noarch/loofi-fedora-tweaks-*.rpm`

### Build Flatpak

```bash
bash build_flatpak.sh
```

**Output**: `loofi-fedora-tweaks.flatpak`

### Build Source Distribution

```bash
python3 -m build --sdist
```

**Output**: `dist/loofi-fedora-tweaks-*.tar.gz`

### Build Wheel

```bash
python3 -m build --wheel
```

**Output**: `dist/loofi_fedora_tweaks-*.whl`

---

## Automated Workflows

### Bot Automation (`.github/workflows/bot-automation.yml`)

Auto-labels PRs and issues:

**PR Labels** (by file path):
- `ui/` → `ui`
- `utils/` → `utils`
- `cli/` → `cli`
- `tests/` → `tests`
- `docs/` → `documentation`
- `.github/` → `github-actions`

**Issue Labels** (by keywords):
- "bug", "error", "crash" → `bug`
- "feature", "enhancement" → `feature`
- "security", "vulnerability" → `security`
- "test", "testing" → `tests`

**Stale Cleanup**:
- Runs weekly on Mondays
- Marks issues/PRs stale after 60 days of inactivity
- Closes stale items after 7 more days

### Dependabot Auto-Merge (`.github/workflows/auto-merge-dependabot.yml`)

Auto-approves and auto-merges **patch-level** version updates:

- ✅ `1.2.3` → `1.2.4` (patch) — Auto-merged
- ❌ `1.2.0` → `1.3.0` (minor) — Manual review
- ❌ `1.0.0` → `2.0.0` (major) — Manual review

Runs weekly on Mondays.

### Coverage Gate (`.github/workflows/coverage-gate.yml`)

Posts coverage report as PR comment:

```
📊 Coverage Report

Overall: 74.2% (+0.3%)

Files with < 75% coverage:
- loofi-fedora-tweaks/utils/new_feature.py: 62.5%
- loofi-fedora-tweaks/ui/new_tab.py: 58.3%

[View full report]
```

### Changelog Auto-Update (`.github/workflows/changelog-update.yml`)

Automatically updates CHANGELOG.md on merge to master:
- Moves entries from `[Unreleased]` to `[vX.Y.Z]`
- Adds timestamp
- Commits and pushes update

---

## Local CI Simulation

Run all CI checks locally before pushing:

```bash
# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722

# Type check
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary

# Test
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v

# Security
bandit -r loofi-fedora-tweaks/ -ll -ii --skip B103,B104,B108,B310,B404,B603,B602

# Build
bash scripts/build_rpm.sh
```

---

## Deployment

Releases are published to:

1. **GitHub Releases**: https://github.com/loofitheboss/loofi-fedora-tweaks/releases
2. **RPM package**: Attached to GitHub Release
3. **Future**: Fedora COPR repository (planned)

---

## Next Steps

- [Testing](Testing) — Test suite guide
- [Contributing](Contributing) — PR workflow
- [Security Model](Security-Model) — Security scans explained
