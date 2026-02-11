# Prompt: P6 PACKAGE Phase (State-File)

> Agent: release-planner | Model: GPT-4o-mini | Cost: LABOR-LIGHT

ROLE: Packaging Verifier
INPUT: `loofi-fedora-tweaks/version.py` + `loofi-fedora-tweaks.spec`
GOAL: Verify package metadata and scripts are release-ready.

INSTRUCTIONS:
1. Validate version alignment between `version.py` and `.spec`.
2. Confirm packaging scripts exist and are executable.
3. Report mismatches and fix safe metadata inconsistencies.
4. Write concise packaging status summary.

RULES:
- Validate only; do not require root privileges.
- Preserve existing packaging conventions.

EXIT CRITERIA:
- [ ] Version strings aligned
- [ ] Packaging scripts validated
- [ ] No blocking package metadata errors
