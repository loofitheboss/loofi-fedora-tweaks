# Automated Workflow Pipeline

> This defines the 7-phase pipeline that every version goes through.
> Agents follow this pipeline automatically when given a version target.

## Pipeline Overview

```
PLAN → DESIGN → IMPLEMENT → TEST → DOCUMENT → PACKAGE → RELEASE
 P1      P2        P3        P4      P5         P6       P7
```

Each phase has: entry criteria, agent assignment, exit criteria, and a standard prompt.

---

## P1: PLAN

**Agent:** project-coordinator (model: haiku)
**Cost tier:** LOW

**Entry:** Version status changed to ACTIVE in ROADMAP.md
**Action:**
1. Read ROADMAP.md for version scope
2. Decompose into atomic tasks with dependencies
3. Write task list to `.claude/workflow/tasks-vXX.md`
4. Identify files to create/modify per task

**Exit:** Task list approved, all tasks have acceptance criteria
**Prompt:** See `prompts/plan.md`

---

## P2: DESIGN

**Agent:** architecture-advisor (model: sonnet)
**Cost tier:** MEDIUM

**Entry:** Task list exists for version
**Action:**
1. Review proposed changes against existing architecture
2. Flag structural risks or pattern violations
3. Approve or request changes to task plan
4. Record decisions in agent memory

**Exit:** Architecture approved, no blocking concerns
**Prompt:** See `prompts/design.md`

---

## P3: IMPLEMENT

**Agents:** backend-builder + frontend-integration-builder + code-implementer
**Model routing:**
- Simple/mechanical changes: haiku
- Business logic: sonnet
- Complex architecture: opus

**Cost tier:** VARIABLE (see model-router.md)

**Entry:** Architecture approved
**Action:**
1. Execute tasks in dependency order
2. backend-builder: utils/, core/, services/
3. frontend-integration-builder: ui/, assets/
4. code-implementer: integration pass, lint/format
5. Each task: implement → verify → mark done

**Exit:** All implementation tasks complete, code compiles
**Prompt:** See `prompts/implement.md`

---

## P4: TEST

**Agent:** test-writer (model: sonnet)
**Cost tier:** MEDIUM

**Entry:** Implementation complete
**Action:**
1. Write/update tests for all changed code
2. Run full test suite
3. Verify coverage >= 80%
4. Fix any failures (loop back to P3 if needed)

**Exit:** All tests pass, coverage met
**Prompt:** See `prompts/test.md`

---

## P5: DOCUMENT

**Agent:** release-planner (model: haiku)
**Cost tier:** LOW

**Entry:** Tests passing
**Action:**
1. Update CHANGELOG.md (Keep-a-Changelog format)
2. Update README.md (features, version, screenshots)
3. Write RELEASE-NOTES-vXX.md
4. Update any affected docs
5. Verify version strings consistent

**Exit:** All docs updated, version strings aligned
**Prompt:** See `prompts/document.md`

---

## P6: PACKAGE

**Agent:** release-planner (model: haiku)
**Cost tier:** LOW

**Entry:** Docs complete
**Action:**
1. Bump version in version.py + .spec
2. Run `scripts/build_rpm.sh` (verify)
3. Validate other packaging scripts
4. Update DEPLOYMENT-CHECKLIST.md if needed

**Exit:** Package builds successfully
**Prompt:** See `prompts/package.md`

---

## P7: RELEASE

**Agent:** release-planner (model: haiku)
**Cost tier:** LOW

**Entry:** Package validated
**Action:**
1. Create release branch: `release/vXX.Y`
2. Create tag: `vXX.Y.0`
3. Push tag (triggers release.yml workflow)
4. Verify GitHub Release created with artifacts
5. Update ROADMAP.md: version → DONE

**Exit:** GitHub Release live with RPM artifact
**Prompt:** See `prompts/release.md`

---

## Release Checklist

Standard checklist for every version. Copy to issue/PR.

```markdown
## vX.Y.0 Release Checklist

### Code
- [ ] All tasks implemented
- [ ] Architecture reviewed and approved
- [ ] Lint clean (flake8)
- [ ] Type check clean (mypy)
- [ ] Security scan clean (bandit)

### Tests
- [ ] All tests pass
- [ ] Coverage >= 80%
- [ ] No regressions

### Documentation
- [ ] CHANGELOG.md updated
- [ ] README.md updated
- [ ] RELEASE-NOTES-vX.Y.0.md written
- [ ] Version strings aligned (version.py, .spec)

### Packaging
- [ ] RPM builds successfully
- [ ] scripts/build_rpm.sh works
- [ ] scripts/build_flatpak.sh validated (or marked N/A)

### Release
- [ ] Release branch created
- [ ] Tag pushed
- [ ] GitHub Release created
- [ ] RPM artifact attached
- [ ] ROADMAP.md updated (ACTIVE → DONE)
```

---

## Quick Reference: Cost by Phase

| Phase | Agent | Model | Tokens (est.) | Cost |
|-------|-------|-------|---------------|------|
| P1 Plan | project-coordinator | haiku | ~2K | $ |
| P2 Design | architecture-advisor | sonnet | ~5K | $$ |
| P3 Implement | mixed | variable | ~15K | $$-$$$ |
| P4 Test | test-writer | sonnet | ~8K | $$ |
| P5 Document | release-planner | haiku | ~2K | $ |
| P6 Package | release-planner | haiku | ~1K | $ |
| P7 Release | release-planner | haiku | ~1K | $ |

**Total per version:** ~34K tokens average
**Cost optimization:** 4 of 7 phases use haiku = ~60% cost reduction vs all-opus
