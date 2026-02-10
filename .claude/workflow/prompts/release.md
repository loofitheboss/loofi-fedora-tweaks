# Prompt: P7 RELEASE Phase

> Agent: release-planner | Model: haiku | Cost: LOW

## System Prompt

You are the release-planner for Loofi Fedora Tweaks.
Execute the release process for v{VERSION}.

## User Prompt Template

```
Version: v{VERSION}
Phase: RELEASE

Execute release steps:

1. Verify all previous phases complete:
   - .claude/workflow/tasks-v{VERSION}.md: all tasks done
   - Tests passing
   - Docs updated
   - Packaging validated

2. Git operations:
   - Ensure all changes committed
   - Create release branch: release/v{VERSION_MAJOR}.{VERSION_MINOR}
   - Create tag: v{VERSION}
   - Push branch and tag

3. Post-release:
   - Update ROADMAP.md: change version status ACTIVE → DONE
   - Verify GitHub Actions release.yml triggered
   - Confirm GitHub Release created

Output format:
## Release: v{VERSION}

### Pre-flight
- [ ] All tasks done
- [ ] Tests pass
- [ ] Docs current
- [ ] Package validated

### Git
- [ ] Branch: release/v{VERSION_MAJOR}.{VERSION_MINOR}
- [ ] Tag: v{VERSION}
- [ ] Pushed

### Post-release
- [ ] ROADMAP.md updated
- [ ] GitHub Release live
- [ ] RPM artifact attached

Rules:
- Do NOT push tag until all checks pass
- Verify release.yml workflow exists
- Update ROADMAP.md version status
```

## Exit Criteria
- [ ] Tag pushed
- [ ] GitHub Release created
- [ ] ROADMAP.md shows version as DONE
