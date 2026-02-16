# Prompt: P1 PLAN Phase (State-File)

> Agent: project-coordinator | Model: GPT-5.3 Codex | Cost: BRAIN

ROLE: Project Coordinator
INPUT: ROADMAP.md (ACTIVE version), AGENTS.md (conventions), agent memory
GOAL: Produce a strict task artifact for downstream phases.

INSTRUCTIONS:
1. Read ROADMAP.md to identify the ACTIVE target version scope.
2. Read AGENTS.md for project conventions and critical rules.
3. Read agent memory for historical context (if available).
4. Break work into atomic tasks (max ~1 hour each).
5. Capture dependency ordering explicitly.
6. DO NOT return chat output. Write directly to target artifact file.
7. Use the mandatory task contract fields below for every task entry.

FORMAT (tasks-vXX.md):
- [ ] ID: TASK-001 | Files: `path/a.py, path/b.py` | Dep: - | Agent: backend-builder | Description: ...
  Acceptance: ...
  Docs: none|CHANGELOG|README|RELEASE-NOTES
  Tests: none|`tests/test_foo.py`
- [ ] ID: TASK-002 | Files: `path/c.py` | Dep: TASK-001 | Agent: test-writer | Description: ...
  Acceptance: ...
  Docs: ...
  Tests: ...

RULES:
- Follow ALL critical rules from AGENTS.md (never sudo, never hardcode dnf, always timeout, etc.)
- Include implementation, tests, and documentation tasks.
- No vague tasks (each task must name files and acceptance check).
- Keep the artifact concise and execution-ready.
- For utils/ modules: use @staticmethod, return operations tuples
- For ui/ tabs: inherit from BaseTab, use CommandRunner
- For CLI: call utils/ directly, support --json output

EXIT CRITERIA:
- [ ] Artifact created in `.workflow/specs/tasks-vXX.md`
- [ ] Dependencies form a DAG
- [ ] Every task has an acceptance check
- [ ] All tasks follow project conventions from AGENTS.md
