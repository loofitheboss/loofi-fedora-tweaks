---
description: "Generate conventional commit messages following project conventions (fix:, feat:, docs:, test: prefixes)"
---

# Conventional Commit Message Generator

## Workflow

1. Run `git status` to review changed files.
2. Run `git diff --cached` to inspect staged changes.
3. Construct the commit message using the project's commit style.

## Commit Message Format

```
type(scope): imperative description

Optional body with more detail.

Optional footer (e.g., BREAKING CHANGE: details)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

## Allowed Types

| Type | Description |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `style` | Formatting, missing semicolons, etc. |
| `ci` | CI/CD configuration changes |
| `build` | Build system or dependencies |
| `chore` | Other changes that don't modify src or test files |

## Examples

```
feat(ui): add search filter to extensions tab
fix(utils): handle missing dnf lock file gracefully
docs: update README with new CLI subcommands
test(commands): add atomic Fedora path coverage
refactor(executor): use ActionResult dataclass for structured results
ci: add fedora-44 chroot to COPR publishing
```

## Rules

- Use imperative mood ("add", not "added")
- Keep first line under 72 characters
- Always include the `Co-authored-by: Copilot` trailer
- Reference issue numbers in footer when applicable: `Fixes #123`
