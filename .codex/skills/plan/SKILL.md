---
name: plan
description: Decompose an ACTIVE version from ROADMAP.md into atomic tasks with dependencies.
---

# Plan Phase (P1)

## Steps
1. Read `ROADMAP.md` — find the `[ACTIVE]` version
2. Read all deliverables listed for that version
3. Decompose into atomic tasks (max 15)
4. Assign each task: agent, layer, size (S/M/L), dependencies
5. Save to `.github/workflow/tasks-v{VERSION}.md`

## Output Format

```markdown
# Tasks for v{VERSION}

| # | Task | Agent | Layer | Size | Depends | Files | Done |
|---|------|-------|-------|------|---------|-------|------|
| 1 | ... | backend-builder | utils | S | - | utils/x.py | [ ] |
```

## Rules
- Each task: 1 agent, 1 layer, clear acceptance criteria
- Order by dependency (no cycles)
- Include test tasks paired with implementation tasks
- Include doc tasks (CHANGELOG, README, release notes)
- Reference `.github/workflow/prompts/plan.md` for full prompt
