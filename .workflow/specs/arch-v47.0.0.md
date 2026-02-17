# Architecture Spec - v47.0.0 "Experience"

## Design Rationale

v47.0.0 is a UX experience release. The objective is to introduce experience-level
awareness, actionable feedback patterns, health drill-down views, and guided tour
capabilities to improve first-run and ongoing user experience.

## Scope

1. UX experience levels — surface complexity appropriate to user expertise.
2. Actionable feedback — replace passive status messages with guided next-step prompts.
3. Health drill-down — expand health score into per-category detail views.
4. Guided tour — first-run walkthrough highlighting key features.

## Key Decisions

### Experience Levels

User-selectable experience level (beginner/intermediate/advanced) stored in
`~/.config/loofi-fedora-tweaks/profile.json`. UI surfaces appropriate detail and
terminology based on level. Default: beginner.

### Actionable Feedback

Status messages include structured next-step suggestions. Error messages provide
`hint` and `recoverable` attributes from `utils/errors.py` to guide resolution.

### Health Drill-Down

Health score tab expands from single-number summary to per-category breakdown.
Each category links to the relevant tab for remediation.

### Guided Tour

First-run wizard extended with optional feature walkthrough. Tour state persisted
in profile to avoid re-showing.

### Release Gate Integrity

Workflow release gate requires versioned task and architecture specs.
This v47 architecture spec and task spec are included to satisfy pipeline contract checks.

## Risks and Mitigations

- Risk: experience level adds complexity to UI rendering.
  Mitigation: implemented as metadata filter on existing widgets, no new widget trees.

- Risk: guided tour blocks user workflow on first run.
  Mitigation: tour is optional and skippable from first dialog.

- Risk: release pipeline fails on missing workflow spec artifacts.
  Mitigation: added `.workflow/specs/tasks-v47.0.0.md` and this file.

## Validation

- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --tb=short`
- `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203`
- Auto-release `pipeline_gate` passes with v47 workflow spec files present.
