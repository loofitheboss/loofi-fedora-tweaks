# Model Routing Strategy

> Route tasks to the cheapest model that can handle them well.
> Priority: cost-effective without losing quality or speed.

## Model Tiers

| Tier | Claude | OpenAI | Use For | Token Cost |
|------|--------|--------|---------|------------|
| FAST | Haiku | GPT-4o-mini | Docs, formatting, simple edits, checklists | $0.25/1M |
| BALANCED | Sonnet | GPT-4o | Business logic, tests, reviews, refactors | $3/1M |
| POWER | Opus 4.5 | GPT-5.3 Codex | Complex architecture, multi-file changes, debugging | $15/1M |

## Routing Rules

### Use FAST (Haiku / GPT-4o-mini) for:
- CHANGELOG.md updates
- README.md updates
- Release notes writing
- Version string bumps
- Formatting and linting fixes
- Simple file renames/moves
- Checklist generation
- Git operations (branch, tag, push)
- Documentation-only changes
- Package script validation (dry-run check)

### Use BALANCED (Sonnet / GPT-4o) for:
- New utility module implementation
- Test writing and updates
- UI component changes
- Architecture review (single-concern)
- Bug fixes with clear reproduction
- Code review
- Refactoring within a single module
- Service layer implementation
- CLI command additions

### Use POWER (Opus 4.5 / GPT-5.3 Codex) for:
- Multi-module architectural changes
- Plugin system design
- Cross-cutting refactors (>5 files)
- Complex debugging (unclear root cause)
- Initial project planning for new versions
- Design decisions with trade-offs
- Performance optimization
- Security-critical changes

## Agent-to-Model Mapping

| Agent | Default Model | Override When |
|-------|--------------|---------------|
| project-coordinator | haiku | Use sonnet for initial version planning |
| architecture-advisor | sonnet | Use opus for plugin/major redesign |
| backend-builder | sonnet | Use opus for executor/service layer |
| frontend-integration-builder | sonnet | Use haiku for QSS-only changes |
| test-writer | sonnet | Use haiku for simple mock additions |
| release-planner | haiku | Never needs upgrade |
| code-implementer | sonnet | Use opus for integration across >5 files |

## Cost Optimization Techniques

### 1. Context Compression
- Agent memory files persist context — don't re-explain project structure
- ROADMAP.md is the single source of truth — don't repeat scope in prompts
- Use bullet lists, not paragraphs
- Max 10 lines per agent response summary

### 2. Task Batching
- Group related file edits into single agent calls
- Don't spawn a new agent for each file — batch per-layer
- Example: backend-builder handles ALL utils/ changes in one session

### 3. Early Exit
- If a phase has no work (e.g., no packaging changes needed), skip it
- If tests already pass, skip P4
- If docs are already current, skip P5

### 4. Prompt Caching
- Standard prompts in `prompts/` are reused — models cache them
- Don't add version-specific context to the system prompt
- Pass version-specific scope as user messages

### 5. Memory Reuse
- Agent memory in `.claude/agent-memory/` carries forward
- Don't re-read files the agent already knows about
- Trust agent memory for file locations, patterns, conventions

## Example: v22.0 Cost Estimate

| Phase | Model | Est. Tokens | Est. Cost |
|-------|-------|-------------|-----------|
| Plan | haiku | 2,000 | $0.001 |
| Design | sonnet | 4,000 | $0.012 |
| Implement (backend) | sonnet | 8,000 | $0.024 |
| Implement (frontend) | sonnet | 6,000 | $0.018 |
| Test | sonnet | 6,000 | $0.018 |
| Document | haiku | 2,000 | $0.001 |
| Package | haiku | 1,000 | $0.001 |
| Release | haiku | 1,000 | $0.001 |
| **Total** | | **30,000** | **~$0.08** |

Per-version cost target: **< $0.15 for standard releases**
