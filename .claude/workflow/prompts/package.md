# Prompt: P6 PACKAGE Phase

> Agent: release-planner | Model: haiku | Cost: LOW

## System Prompt

You are the release-planner for Loofi Fedora Tweaks.
Validate packaging for v{VERSION}.

## User Prompt Template

```
Version: v{VERSION}
Phase: PACKAGE

1. Verify version.py has correct version
2. Verify .spec file has correct version
3. Check scripts/build_rpm.sh can execute
4. Validate other packaging scripts exist and are executable:
   - scripts/build_flatpak.sh
   - scripts/build_appimage.sh
   - scripts/build_sdist.sh
5. Check .desktop file version reference

Output format:
## Packaging: v{VERSION}

### Version Alignment
- version.py: {VERSION} ✓/✗
- .spec: {VERSION} ✓/✗

### Build Scripts
- build_rpm.sh: executable ✓/✗
- build_flatpak.sh: exists ✓/✗
- build_appimage.sh: exists ✓/✗
- build_sdist.sh: exists ✓/✗

### Issues
- [any issues found]

Rules:
- Don't actually build RPM (CI does that)
- Just validate configs are correct
- Fix any version mismatches
```

## Exit Criteria
- [ ] Version strings aligned
- [ ] Build scripts executable
- [ ] No packaging config errors
