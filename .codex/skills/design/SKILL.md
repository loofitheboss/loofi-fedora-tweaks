---
name: design
description: Create or update architecture specs for the ACTIVE version before implementation.
---

# Design Phase (P2)

## Steps
1. Read `ROADMAP.md` — find the `[ACTIVE]` version
2. Read `.workflow/specs/tasks-v{VERSION}.md` for planned features
3. Read `ARCHITECTURE.md` for existing patterns and layer rules
4. For each major feature, decide:
   - Which layer(s) are affected (utils, ui, cli, core, services)
   - New modules vs. extending existing
   - Data structures / dataclasses needed
   - Error types to add
   - Atomic Fedora / privilege escalation implications
5. Save to `.workflow/specs/arch-v{VERSION}.md`

## Output Format

```markdown
# Architecture Spec — v{VERSION}

## Overview
One-line version scope.

## Design Decisions

### D1: {Feature Name}
- **Layer**: utils / ui / cli
- **New files**: `utils/new_thing.py`, `ui/new_thing_tab.py`
- **Modified files**: `ui/main_window.py` (lazy loader registration)
- **Data model**: Describe dataclass or return type
- **Pattern**: Which existing pattern to follow
- **Risks**: Atomic compatibility, privilege needs, test complexity
```

## Rules
- Must complete before P3 (Build) — enforced by workflow_runner phase ordering
- Reference existing modules for pattern consistency
- Every new util must have a paired test plan
- Every new UI tab needs BaseTab inheritance plan
- Reference `.github/workflow/prompts/design.md` for full prompt
