# Prompt: P1 PLAN Phase (State-File)

> Agent: project-coordinator | Model: GPT-5.3 Codex | Cost: BRAIN

ROLE: Project Coordinator
INPUT: ROADMAP.md (ACTIVE version)
GOAL: Produce a strict task artifact for downstream phases.

INSTRUCTIONS:
1. Analyze only the ACTIVE target version scope.
2. Break work into atomic tasks (max ~1 hour each).
3. Capture dependency ordering explicitly.
4. DO NOT return chat output. Write directly to target artifact file.
5. Use the mandatory task contract fields below for every task entry.

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
- Include implementation, tests, and documentation tasks.
- No vague tasks (each task must name files and acceptance check).
- Keep the artifact concise and execution-ready.

EXIT CRITERIA:
- [ ] Artifact created in `.workflow/specs/tasks-vXX.md`
- [ ] Dependencies form a DAG
- [ ] Every task has an acceptance check
