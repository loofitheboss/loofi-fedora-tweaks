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

FORMAT (tasks-vXX.md):
- [ ] ID: TASK-001 | File: `path/to/file.py` | Agent: backend-builder | Description: ...
- [ ] ID: TASK-002 | File: `path/to/file.py` | Dep: TASK-001 | Agent: test-writer | Description: ...

RULES:
- Include implementation, tests, and documentation tasks.
- No vague tasks (each task must name files and acceptance check).
- Keep the artifact concise and execution-ready.

EXIT CRITERIA:
- [ ] Artifact created in `.workflow/specs/tasks-vXX.md`
- [ ] Dependencies form a DAG
- [ ] Every task has an acceptance check
