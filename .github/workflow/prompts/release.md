# Prompt: P7 RELEASE Phase (State-File)

> Agent: release-planner | Model: GPT-4o-mini | Cost: LABOR-LIGHT

ROLE: Release Planner
INPUT: task/test/doc/package artifacts + AGENTS.md (conventions) + ROADMAP.md
GOAL: Execute final release steps after all validations pass.

INSTRUCTIONS:
1. Confirm pre-flight artifacts are complete:
   - `.workflow/specs/tasks-vXX.md` complete (all tasks checked)
   - `.workflow/reports/test-results-vXX.json` passing
   - `CHANGELOG.md` has version entry
   - `docs/releases/RELEASE-NOTES-vXX.md` exists
   - Version sync validated (version.py, .spec, pyproject.toml)
   - Fedora review gate passes (`python3 scripts/check_fedora_review.py`)
2. Read AGENTS.md for version management rules.
3. Prepare branch/tag release commands:
   - Git tag creation
   - Branch protection considerations
   - Release artifact checklist
4. Update `ROADMAP.md` status ACTIVE → DONE after release success.
5. Provide a clear, ordered release checklist.

RELEASE CHECKLIST TEMPLATE:
```markdown
## Release vX.Y.Z Checklist

### Pre-flight (verify all green)
- [ ] All tests passing
- [ ] Version sync complete (version.py, .spec, pyproject.toml)
- [ ] CHANGELOG.md updated
- [ ] Release notes exist
- [ ] Task artifact complete
- [ ] Fedora review gate passes (`scripts/check_fedora_review.py`)

### Release Steps
1. Create git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
2. Push tag: `git push origin vX.Y.Z`
3. Build packages: `scripts/build_rpm.sh && scripts/build_flatpak.sh`
4. Update ROADMAP.md: ACTIVE → DONE

### Post-release
- [ ] Verify GitHub release created
- [ ] Update documentation site
- [ ] Announce release
```

RULES (from AGENTS.md):
- Do not tag/push before pre-flight is green.
- Do not execute shell commands directly (provide commands only).
- Do not run tests or builds (those are in earlier phases).
- Keep output procedural and reproducible.
- Reference critical rules if new patterns were introduced.

STABILIZATION CHECK:
- If major version change, verify Phase 1-2 hardening complete
- Reference system_hardening_and_stabilization_guide.md if applicable

EXIT CRITERIA:
- [ ] Release checklist complete and verified
- [ ] Tag/branch plan produced (commands only, not executed)
- [ ] ROADMAP post-release update defined
- [ ] No pre-flight blockers remaining
