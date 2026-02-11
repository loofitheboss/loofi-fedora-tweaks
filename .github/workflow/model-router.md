# Model Router (Brain vs Labor)

> Route by decision complexity, not by phase habit.
> Source of truth for automation is `.github/workflow/model-router.toml`.

## Tiers
| Tier | Model | Use When |
|---|---|---|
| BRAIN | GPT-5.3 Codex | Planning, architecture, dependency/risk decisions |
| LABOR | GPT-4o | Implementation, tests, integration changes |
| LABOR-LIGHT | GPT-4o-mini | Documentation, packaging text, release notes |

## Phase Mapping
| Phase | Default Model | Reason |
|---|---|---|
| P1 Plan | GPT-5.3 Codex | Bad plans are expensive to recover from |
| P2 Design | GPT-5.3 Codex | Architectural mistakes cascade across tasks |
| P3 Build | GPT-4o | Strong coding quality at lower cost |
| P4 Test | GPT-4o | Good balance for mock-heavy test authoring |
| P5 Doc | GPT-4o-mini | Low-risk text generation |
| P6 Package | GPT-4o-mini | Mostly checklist/metadata validation |
| P7 Release | GPT-4o-mini | Procedural release execution |

## Hard Routing Rules
- P3 implement reads only: `arch-vXX.md` + `tasks-vXX.md` + directly affected code files.
- P3 implement does not read ROADMAP.md.
- Promote LABOR -> BRAIN only for blockers that require architecture changes.
- Never run docs/package/release on BRAIN tier unless explicitly required.
- No implicit model fallback to expensive tiers.

## Cost Control
- Prefer artifact diffs over chat history transfer.
- Keep prompts stable; vary only version and artifact file names.
- Use one phase = one fresh context.
