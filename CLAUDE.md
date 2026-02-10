# Claude Code Instructions — Loofi Fedora Tweaks

## ROLE
You are Claude Code operating inside this repository.
Delegate to agents. Follow the automated pipeline. Minimize token usage.

## KEY FILES (READ THESE, DON'T REPEAT THEIR CONTENT)
- `ROADMAP.md` — Version scope, status, deliverables, agent assignments
- `.claude/workflow/PIPELINE.md` — 7-phase automation pipeline (PLAN→RELEASE)
- `.claude/workflow/model-router.md` — Model selection for cost optimization
- `.claude/workflow/prompts/` — Standardized prompts per pipeline phase
- `.claude/agents/` — Agent definitions (7 agents)
- `.claude/agent-memory/` — Persistent agent context

## TOKEN DISCIPLINE (CRITICAL)
- Read context files once, reference by name after
- Bullet lists only. No paragraphs.
- Max 10 lines per response section
- Delegate to agents via Task tool — don't implement inline
- Never re-explain roadmap, architecture, or patterns

## AUTOMATED PIPELINE

Every version follows 7 phases. See `.claude/workflow/PIPELINE.md`.

```
PLAN → DESIGN → IMPLEMENT → TEST → DOCUMENT → PACKAGE → RELEASE
haiku   sonnet   variable   sonnet  haiku      haiku     haiku
```

### To start a version:
1. Read `ROADMAP.md` for the ACTIVE version
2. Execute phases P1-P7 sequentially
3. Use standardized prompts from `.claude/workflow/prompts/`
4. Route to correct model per `.claude/workflow/model-router.md`

### Agent-Phase mapping:
| Phase | Agent | Model |
|-------|-------|-------|
| P1 Plan | project-coordinator | haiku |
| P2 Design | architecture-advisor | sonnet |
| P3 Implement | backend-builder / frontend-integration-builder / code-implementer | sonnet/opus |
| P4 Test | test-writer | sonnet |
| P5 Document | release-planner | haiku |
| P6 Package | release-planner | haiku |
| P7 Release | release-planner | haiku |

## AGENT TAGS (MANDATORY)
Always prefix agent actions:
```
[architecture-advisor] Reviewing...
[backend-builder] Implementing...
```

## RELEASE RULES
For every vX.Y.0 — see `.claude/workflow/PIPELINE.md#release-checklist`.
No undocumented changes. All docs/version strings/packaging validated.

## OUTPUT FORMAT
1. **Checklist** (done/pending per phase)
2. **Agent Summary** (1 line per agent)
3. **Changes** (max 10 bullets)
4. **Commands** (shell)
5. **Files Changed** (list)

No essays. No filler.

## MODEL ROUTING (COST OPTIMIZATION)
See `.claude/workflow/model-router.md` for full rules.

**Quick reference:**
- **haiku**: docs, formatting, version bumps, git ops, checklists
- **sonnet**: logic, tests, UI, reviews, single-module refactors
- **opus**: multi-file architecture, debugging, plugin design, planning

**Target: 60% of work on haiku, 30% sonnet, 10% opus**

## CONTEXT COMPRESSION RULES
1. Agent memory persists — don't re-read known files
2. ROADMAP.md is truth — don't copy scope into prompts
3. Standard prompts cached — use them as-is with variable substitution
4. Batch file edits per agent session
5. Skip phases with no work (early exit)
