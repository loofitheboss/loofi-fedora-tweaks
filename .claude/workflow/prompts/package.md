# Prompt: P6 PACKAGE Phase (State-File)

> Agent: release-planner | Model: GPT-4o-mini | Cost: LABOR-LIGHT

ROLE: Packaging Verifier
INPUT: `loofi-fedora-tweaks/version.py` + `loofi-fedora-tweaks.spec` + `pyproject.toml` + AGENTS.md (conventions)
GOAL: Verify package metadata and scripts are release-ready.

INSTRUCTIONS:
1. Validate version alignment between:
   - `version.py`: `__version__` field
   - `loofi-fedora-tweaks.spec`: `Version:` field
   - `pyproject.toml`: `version` field
2. Read AGENTS.md for version sync rules (critical rule #7).
3. Confirm packaging scripts exist and are executable:
   - `scripts/build_rpm.sh`
   - `scripts/build_flatpak.sh`
   - `scripts/build_sdist.sh`
4. Report mismatches and fix safe metadata inconsistencies.
5. Write concise packaging status summary.

VERSION SYNC RULE (from AGENTS.md):
- All three files MUST have matching version numbers
- Use `scripts/bump_version.py` for safe version updates
- `build_rpm.sh` reads version dynamically from `version.py`

CHECKS:
- [ ] version.py `__version__` matches target version
- [ ] .spec `Version:` matches target version
- [ ] pyproject.toml `version` matches target version
- [ ] Packaging scripts are executable
- [ ] No blocking package metadata errors

RULES:
- Validate only; do not require root privileges.
- Preserve existing packaging conventions.
- Report discrepancies clearly.

EXIT CRITERIA:
- [ ] Version strings aligned across all three files
- [ ] Packaging scripts validated
- [ ] No blocking package metadata errors
- [ ] Packaging status summary written
