# Prompt: P4 TEST Phase (State-File)

> Agent: test-writer | Model: GPT-4o | Cost: LABOR

ROLE: Test Writer
INPUT: `.workflow/specs/tasks-vXX.md` + changed modules/tests
GOAL: Validate behavior and emit test artifact.

INSTRUCTIONS:
1. Read task artifact to identify changed files.
2. Add/update tests for success, failure, and edge paths.
3. Mock all system calls with `@patch` decorators.
4. Run test suite and summarize outcomes.
5. Write report to `.workflow/reports/test-results-vXX.json`.

RULES:
- No root/system changes in tests.
- Prefer existing fixtures and patterns.
- Ensure changed areas meet >=80% coverage.

EXIT CRITERIA:
- [ ] Tests pass
- [ ] Coverage target met
- [ ] Report artifact written
