---
name: implement
description: Execute implementation tasks from the task list, one at a time, in dependency order.
---

# Implement Phase (P3)

## Steps
1. Read `.claude/workflow/tasks-v{VERSION}.md`
2. Find the next undone task
3. Read affected files listed in the task
4. Implement following existing patterns
5. Verify: lint clean, imports resolve
6. Mark task done in task file
7. Repeat until all implementation tasks complete

## Patterns to Follow
- `utils/`: `@staticmethod`, return `Tuple[str, List[str], str]`
- `ui/`: inherit `BaseTab`, use `self.run_command()`
- System calls: `PrivilegedCommand` (always unpack tuple)
- Package detection: `SystemManager.get_package_manager()`
- Errors: use typed exceptions from `utils/errors.py`

## Verification
```bash
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
python loofi-fedora-tweaks/main.py --version
```

## Rules
- Only change files listed in the task
- Minimal diff — no overengineering
- If blocked, document why and move to next task
- Reference `.claude/workflow/prompts/implement.md` for full prompt
