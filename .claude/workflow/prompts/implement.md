# Prompt: P3 IMPLEMENT Phase

> Agents: backend-builder, frontend-integration-builder, code-implementer
> Model: sonnet (default), opus for complex | Cost: VARIABLE

## System Prompt

You are implementing tasks for Loofi Fedora Tweaks v{VERSION}.
Follow the task list exactly. One task at a time. Verify before moving on.

## User Prompt Template

```
Version: v{VERSION}
Phase: IMPLEMENT
Task: #{TASK_NUM} — {TASK_TITLE}
Agent: {AGENT_NAME}

1. Read the task from .claude/workflow/tasks-v{VERSION}.md
2. Read affected files listed in the task
3. Implement the change following existing patterns
4. Verify: no lint errors, imports resolve, no regressions

Output format:
## Task #{TASK_NUM}: {TASK_TITLE}

### Changes
- `path/to/file.py`: [what changed, 1 line]

### Verification
- [ ] Lint clean
- [ ] Imports resolve
- [ ] Existing tests still pass

### Notes
- [anything the next task needs to know]

Rules:
- ONLY change files listed in the task
- Follow existing patterns (BaseTab, PrivilegedCommand, etc.)
- No overengineering — minimal diff
- If blocked, document why and move to next task
- Mark task as done in tasks-v{VERSION}.md
```

## Agent-Specific Instructions

### backend-builder
- Focus: utils/, core/, services/
- Pattern: @staticmethod, dataclasses, Tuple returns
- Always mock system calls in implementation

### frontend-integration-builder
- Focus: ui/, assets/
- Pattern: BaseTab inheritance, lazy loading, QSS scoping
- No global styles — use setObjectName()

### code-implementer
- Focus: integration, lint cleanup, final pass
- Verify all layers connect properly
- Run flake8 and fix issues

## Exit Criteria
- [ ] All implementation tasks marked done
- [ ] No lint errors
- [ ] Application entry point works (`python main.py --version`)
