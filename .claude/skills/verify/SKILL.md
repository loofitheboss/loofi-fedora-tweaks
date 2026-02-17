---
name: verify
description: Run full verification suite (lint, typecheck, tests, coverage) before committing. Use this before any commit or PR.
---

# Verify

Run the full project verification pipeline. Report results clearly.

## Steps

1. Run `just lint` — report pass/fail
2. Run `just typecheck` — report pass/fail
3. Run `just test-coverage` — report pass/fail and coverage percentage
4. If all pass, confirm ready to commit
5. If any fail, list the specific failures with file:line references

## Rules

- Never skip a step
- If lint fails, do NOT proceed to typecheck — fix lint first
- Report coverage percentage from the output
- Do not auto-fix anything — only report
