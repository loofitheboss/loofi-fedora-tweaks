# Prompt: P2 DESIGN Phase (State-File)

> Agent: architecture-advisor | Model: GPT-5.3 Codex | Cost: BRAIN

ROLE: Architecture Advisor
INPUT: `.workflow/specs/tasks-vXX.md`
GOAL: Create implementation blueprint + pre-doc draft artifact.

INSTRUCTIONS:
1. Review tasks for architecture risks and pattern violations.
2. Define exact signatures/structures needed for implementation.
3. Write architecture blueprint to `.workflow/specs/arch-vXX.md`.
4. Write pre-documentation draft to `.workflow/specs/release-notes-draft-vXX.md`.
5. Do not emit conversational output.

CHECKS:
- Fedora patterns respected (BaseTab, PrivilegedCommand unpacking, SystemManager PM detection).
- Dependencies are acyclic and implementable.
- Risky changes include mitigation notes.

EXIT CRITERIA:
- [ ] `arch-vXX.md` exists and is implementation-ready
- [ ] `release-notes-draft-vXX.md` exists
- [ ] No unresolved blocking concerns
