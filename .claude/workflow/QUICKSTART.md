# Workflow Quickstart

## One-Command Version Release

```bash
# Validate current state
./scripts/workflow-runner.sh 23.0.0 validate

# Run each phase with Claude Code
./scripts/workflow-runner.sh 23.0.0 plan
./scripts/workflow-runner.sh 23.0.0 design
./scripts/workflow-runner.sh 23.0.0 implement
./scripts/workflow-runner.sh 23.0.0 test
./scripts/workflow-runner.sh 23.0.0 document
./scripts/workflow-runner.sh 23.0.0 package
./scripts/workflow-runner.sh 23.0.0 release
```

## Or Use Claude Code Directly

### Start a new version
```
"Execute the automated pipeline for v23.0.0. Read ROADMAP.md and follow PIPELINE.md phases P1-P7."
```

### Resume from a specific phase
```
"Continue v23.0.0 from P4 TEST. Read .claude/workflow/tasks-v23.0.md for context."
```

### Single task
```
"[backend-builder] Implement task #3 from .claude/workflow/tasks-v23.0.md"
```

## OpenAI Codex Usage

Same prompts work. Reference the files:
```
Read ROADMAP.md for version scope.
Read .claude/workflow/prompts/implement.md for instructions.
Execute P3 IMPLEMENT for v23.0.0, task #3.
```

## Cost Optimization Checklist

- [ ] Using haiku/GPT-4o-mini for docs, formatting, git ops
- [ ] Using sonnet/GPT-4o for logic, tests, reviews
- [ ] Using opus/GPT-5.3 only for complex architecture
- [ ] Agent memory files populated (no re-reading)
- [ ] Standardized prompts used (cached by model)
- [ ] Phases with no work skipped
- [ ] File edits batched per agent session

## File Map

```
ROADMAP.md                           ← Version scope & status
CLAUDE.md                            ← Master instructions (concise)
.claude/workflow/
├── PIPELINE.md                      ← 7-phase pipeline definition
├── QUICKSTART.md                    ← This file
├── model-router.md                  ← Model selection strategy
├── tasks-v{XX}.md                   ← Generated task lists per version
└── prompts/
    ├── plan.md                      ← P1 prompt template
    ├── design.md                    ← P2 prompt template
    ├── implement.md                 ← P3 prompt template
    ├── test.md                      ← P4 prompt template
    ├── document.md                  ← P5 prompt template
    ├── package.md                   ← P6 prompt template
    └── release.md                   ← P7 prompt template
.claude/agents/                      ← Agent definitions
.claude/agent-memory/                ← Persistent agent context
.github/workflows/
├── ci.yml                           ← CI pipeline (lint, test, build)
├── release.yml                      ← Tag-triggered release
└── auto-release.yml                 ← Enhanced release with validation
scripts/
└── workflow-runner.sh               ← CLI for pipeline execution
```
