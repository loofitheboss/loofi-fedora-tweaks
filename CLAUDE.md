# Claude Code Instructions — Loofi Fedora Tweaks

## ROLE
You are Claude Code operating inside this repository.

This project contains dedicated Claude agents under:
- `.claude/agent-memory/`
- `.claude/agents/`

You MUST actively utilize them instead of doing everything yourself.

## TOKEN DISCIPLINE (CRITICAL)
- Be concise.
- No long explanations.
- Delegate tasks to appropriate agents.
- Do not re-explain roadmap each time.
- Use bullet lists and diffs.
- Batch work per version.

## AGENT UTILIZATION MODEL (MANDATORY)

For each release version, you must coordinate agents as follows:

1. **project-coordinator**
   - Break version scope into atomic tasks.
   - Ensure execution order.
   - Track completion checklist.

2. **architecture-advisor**
   - Review structural changes.
   - Approve refactors before implementation.
   - Prevent technical debt.

3. **backend-builder**
   - Implement system logic.
   - Subprocess execution layer.
   - Services layer.
   - Plugin architecture (v25).

4. **frontend-integration-builder**
   - UI layout fixes.
   - QSS scoping.
   - Widget hierarchy.
   - UX improvements.
   - No global unsafe styles.

5. **test-writer**
   - Add pytest tests.
   - Add UI sanity checks.
   - Prevent regression (layout + logic).

6. **release-planner**
   - Update version strings.
   - Update CHANGELOG.md.
   - Update README.md.
   - Ensure packaging metadata aligned.
   - Ensure RPM + Flatpak + AppImage + sdist scripts updated.
   - Prepare GitHub release notes.

7. **code-implementer**
   - Final integration pass.
   - Ensure lint/format clean.
   - Produce final diff.

**You MUST explicitly state which agent is being used when performing a task:**

Example:
```
[architecture-advisor] Reviewing layout margin architecture…
[backend-builder] Refactoring service layer…
```

## GLOBAL RELEASE RULES (NON-NEGOTIABLE)

For every version vX.Y.0:
- Code changes implemented.
- CHANGELOG.md updated (Keep-a-Changelog format).
- README updated.
- Version bumped everywhere.
- Packaging scripts validated:
  - `scripts/build_rpm.sh`
  - `scripts/build_flatpak.sh`
  - `scripts/build_appimage.sh`
  - `scripts/build_sdist.sh`
- GitHub release branch created: `release/vX.Y`
- Tag prepared: `vX.Y.0`
- Release notes drafted.
- No undocumented change allowed.

## OUTPUT FORMAT (STRICT)

For each version, output only:

1. **vX.Y.0 Checklist** (✅ / ⬜)
2. **Agent Execution Summary** (short bullets per agent)
3. **Changes** (max 10 bullets)
4. **Commands** (shell commands)
5. **Diff** (or file list if large)
6. **Release Notes** (max 8 bullets)

No essays.

## ROADMAP EXECUTION

### v21.0 — UX Stabilization & Layout Integrity

**Agents:**
- architecture-advisor → review window flags + layout margins + QSS scoping
- frontend-integration-builder → fix top bar glitch, remove unsafe global QSS
- test-writer → add geometry sanity test or debug flag
- release-planner → packaging + docs
- code-implementer → integration pass

**Goals:**
- Fix title/top-bar overlap.
- Scope QTabBar scroller styling.
- Enforce consistent root layout margins.
- Ensure HiDPI safe.
- No frameless hacks unless fully implemented.

### v22.0 — Usability & Workflow Enhancements

**Agents:**
- project-coordinator → define tweak search + status plan
- backend-builder → persistent preferences + reset logic
- frontend-integration-builder → search/filter UI + indicators
- test-writer → test tweak state transitions
- release-planner → docs + packaging

**Features:**
- Search/filter tweaks
- Applied status indicators
- Reset per group
- Confirm dialogs
- Persistent preferences

### v23.0 — Architecture Hardening

**Agents:**
- architecture-advisor → approve folder structure refactor
- backend-builder → service abstraction
- frontend-integration-builder → non-blocking UI
- test-writer → minimal pytest coverage
- release-planner → CI workflow addition

**Goals:**
- Introduce `ui/`, `core/`, `services/`, `utils/`
- Single subprocess wrapper
- QThread/QRunnable for long ops
- GitHub Actions: lint + test + RPM build

### v24.0 — Advanced Power Features

**Agents:**
- backend-builder → profiles + JSON export/import
- frontend-integration-builder → advanced mode toggle + log panel
- architecture-advisor → validate snapshot system
- test-writer → profile save/load tests
- release-planner → packaging polish

**Features:**
- Profiles
- JSON import/export
- Live log panel
- System snapshot before apply

### v25.0 — MAJOR: Plugin Architecture + UI Redesign

**Agents:**
- architecture-advisor → define plugin interface
- backend-builder → implement plugin loader
- frontend-integration-builder → redesign navigation (sidebar)
- test-writer → plugin registration tests
- release-planner → documentation overhaul
- code-implementer → final integration

**Goals:**
- Tweaks self-register as modules
- Dynamic loading
- Clear API boundary
- Compatibility detection engine
- Unified spacing system
- README rewrite
- Plugin dev guide
- CONTRIBUTING.md
