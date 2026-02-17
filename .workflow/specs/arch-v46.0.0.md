# Architecture Spec - v46.0.0 "Navigator"

## Design Rationale

v46.0.0 is a navigation-clarity release. The objective is to improve discoverability by
using a single technical taxonomy across sidebar and command palette without changing
underlying feature behavior.

## Scope

1. Replace legacy/ambiguous sidebar category names with a stable technical model.
2. Ensure every tab metadata category maps to registry-defined categories.
3. Keep ordering deterministic and avoid orphan categories.
4. Align release artifacts and workflow specs so release pipelines remain deterministic.

## Key Decisions

### Taxonomy Standardization

The canonical categories are:
`System`, `Packages`, `Hardware`, `Network`, `Security`, `Appearance`, `Tools`, `Maintenance`.

`core/plugins/registry.py` is the source of truth for ordering and icons.

### Metadata-Only Navigation Refactor

Category changes are applied through `PluginMetadata` fields in tab modules only.
No feature logic, privilege behavior, or subprocess execution paths are modified.

### Command Palette Consistency

Command palette `category` labels are synchronized with sidebar taxonomy to reduce
cognitive switching between navigation surfaces.

### Release Gate Integrity

Workflow release gate requires versioned task and architecture specs.
This v46 task spec and architecture spec are included to satisfy pipeline contract checks.

## Risks and Mitigations

- Risk: category assertion tests fail due to renamed labels.
  Mitigation: updated affected test expectations and re-ran full suite.

- Risk: release pipeline fails on missing workflow spec artifacts.
  Mitigation: added `.workflow/specs/tasks-v46.0.0.md` and this file.

- Risk: UI discoverability regressions from re-grouping.
  Mitigation: kept behavior unchanged and validated search/favorites/breadcrumb flows.

## Validation

- `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -q --tb=short`
- `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203`
- Auto-release `pipeline_gate` passes with v46 workflow spec files present.
