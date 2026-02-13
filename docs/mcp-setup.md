# MCP Setup Guide — GitHub Copilot Integration

> **Model Context Protocol (MCP)** enables AI tools like GitHub Copilot to interact with external services via standardized APIs. This guide explains how Loofi Fedora Tweaks uses MCP for automated workflows.

---

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [GitHub MCP Server](#github-mcp-server)
3. [Setup for VS Code](#setup-for-vs-code)
4. [Setup for Copilot CLI](#setup-for-copilot-cli)
5. [Automated Bot Workflows](#automated-bot-workflows)
6. [Security Best Practices](#security-best-practices)

---

## What is MCP?

**Model Context Protocol (MCP)** is an open protocol that allows AI assistants to:
- Access external data sources (files, APIs, databases)
- Execute operations (create issues, run tests, scan code)
- Maintain stateful context across interactions

In this repository, MCP connects GitHub Copilot to the GitHub API, enabling:
- Automated PR security scans
- Smart issue/PR labeling
- Dependabot auto-merge
- Code security analysis

---

## GitHub MCP Server

The GitHub MCP server provides these **toolsets**:

| Toolset | Capabilities |
|---------|-------------|
| `pull_requests` | Create, review, and manage PRs |
| `code_security` | Run security scans (Bandit, CodeQL) |
| `secret_protection` | Detect hardcoded secrets |
| `issues` | Create, label, and manage issues |
| `repos` | Repository metadata and operations |

**Connection**: The MCP server is hosted at `https://api.githubcopilot.com/mcp/` and requires GitHub Copilot subscription.

---

## Setup for VS Code

### 1. Configuration File

The MCP server is configured in `.vscode/mcp.json`:

```json
{
  "servers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "toolsets": [
        "pull_requests",
        "code_security", 
        "secret_protection",
        "issues",
        "repos"
      ]
    }
  }
}
```

### 2. Prerequisites

- **VS Code**: 1.85.0 or later
- **GitHub Copilot Extension**: Latest version
- **GitHub Account**: With Copilot subscription

### 3. Activation

1. Open the repository in VS Code
2. GitHub Copilot will automatically detect `.vscode/mcp.json`
3. Verify by opening Copilot Chat and typing:
   ```
   @github list recent pull requests
   ```
4. You should see PRs from this repository

### 4. Available Commands

Once configured, you can use these Copilot commands:

```
@github create a PR for branch feature/xyz
@github scan this PR for security issues
@github label this issue as "bug" and "ui"
@github list open issues with label "security"
```

---

## Setup for Copilot CLI

### 1. Configuration File

The Copilot CLI uses `.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "toolsets": [
        "pull_requests",
        "code_security",
        "secret_protection",
        "issues",
        "repos"
      ]
    }
  }
}
```

### 2. Installation

```bash
# Install GitHub Copilot CLI
npm install -g @githubnext/github-copilot-cli

# Authenticate
github-copilot-cli auth login
```

### 3. Usage Examples

```bash
# Explain a PR
copilot explain pr 123

# Suggest security fixes
copilot suggest security-fix --file loofi-fedora-tweaks/utils/operations.py

# Create an issue
copilot create issue --title "Add dark mode support" --label enhancement
```

---

## Automated Bot Workflows

This repository includes **three automated bot workflows** that leverage GitHub Actions:

### 1. PR Security Bot (`.github/workflows/pr-security-bot.yml`)

**Trigger**: Every PR to `master` branch (opened, synchronized, reopened)

**What it does**:
1. **Bandit (SAST)**: Static analysis for Python security issues
   - Severity: Medium-High, Confidence: Medium-High
   - Skips: `B404`, `B603`, `B602` (subprocess-related, handled by PrivilegedCommand pattern)
   
2. **pip-audit**: Scans `requirements.txt` for known CVEs in dependencies

3. **Trivy**: Filesystem scan for vulnerabilities and secrets

4. **detect-secrets**: Scans for hardcoded secrets (API keys, passwords, tokens)

**Output**: Posts a comment on the PR with a summary table:

```markdown
## 🔒 PR Security Bot Report

| Check | Status | Details |
|-------|--------|---------|
| Bandit (SAST) | ✅ | 0 issue(s) |
| pip-audit (Deps) | ⚠️ | 2 vulnerability(ies) |
| Trivy (FS Scan) | ✅ | 0 finding(s) |
| Secret Detection | ✅ | 0 potential secret(s) |

**Overall: ⚠️ WARNINGS**
```

**Reports**: All scan results are uploaded as workflow artifacts for detailed review.

**How to read the report**:
- ✅ **PASS**: No issues found
- ⚠️ **WARN**: Issues found but not critical (review recommended)
- ❌ **FAIL**: Critical issues found (must fix before merge)

**Note**: Warnings don't block PRs — they're informational. Failures (e.g., hardcoded secrets) should be fixed immediately.

---

### 2. Bot Automation (`.github/workflows/bot-automation.yml`)

**Triggers**:
- PR opened → Auto-label by file path
- Issue opened → Auto-label by keywords
- Weekly cron (Monday 6 AM UTC) → Stale cleanup

#### Auto-Label PRs

When a PR is opened, the bot analyzes changed files and applies labels:

| File Pattern | Label |
|--------------|-------|
| `loofi-fedora-tweaks/ui/` | `ui` |
| `loofi-fedora-tweaks/utils/` | `backend` |
| `loofi-fedora-tweaks/cli/` | `cli` |
| `loofi-fedora-tweaks/core/` | `core` |
| `loofi-fedora-tweaks/services/` | `services` |
| `loofi-fedora-tweaks/api/` | `api` |
| `loofi-fedora-tweaks/config/` | `config` |
| `tests/` | `tests` |
| `.github/` | `ci/cd` |
| `docs/` | `docs` |
| `scripts/` | `tooling` |
| Files with "security" or "bandit" | `security` |
| `.spec`, `.service`, `flatpak`, `appimage` | `packaging` |

#### Auto-Label Issues

When an issue is opened, the bot scans the title and body for keywords:

| Keyword | Label |
|---------|-------|
| bug, crash, error, broken | `bug` |
| feature, request, enhancement, add | `enhancement` |
| security, vulnerability, cve | `security` |
| ui, tab, widget, gui | `ui` |
| cli, command line, terminal | `cli` |
| test, coverage, pytest | `tests` |
| doc, readme, changelog | `docs` |
| rpm, flatpak, appimage, package | `packaging` |
| performance, slow, memory | `performance` |

#### Stale Cleanup

**Schedule**: Every Monday at 6 AM UTC

**Rules**:
- **Stale after**: 30 days of inactivity
- **Close after**: 14 more days (44 days total)
- **Exempt labels**: `roadmap-item`, `pinned`, `in-progress`, `do-not-close`

**Messages**:
```
This issue/PR has been automatically marked as stale because it has not had
recent activity. It will be closed in 14 days if no further activity occurs.
```

**Prevent stale**: Add the `in-progress` label to keep an issue/PR alive.

---

### 3. Auto-merge Dependabot (`.github/workflows/auto-merge-dependabot.yml`)

**Trigger**: Dependabot opens a PR

**What it does**:
1. Checks if the update is a **patch-level** version bump (e.g., `1.2.3` → `1.2.4`)
2. If yes:
   - Auto-approves the PR
   - Enables auto-merge (squash strategy)
   - PR merges once CI passes

**What it doesn't do**:
- Minor/major updates (e.g., `1.2.3` → `1.3.0` or `2.0.0`) require manual review
- Security updates always auto-merge (regardless of version)

**Why patch-only?**
- Patch updates typically contain bug fixes and security patches
- Low risk of breaking changes
- Faster turnaround for security fixes

**Dependabot schedule**: Mondays, weekly (configured in `.github/dependabot.yml`)

---

## Security Best Practices

### For Contributors

1. **Never commit secrets**:
   - API keys, passwords, tokens, private keys
   - Use environment variables or GitHub Secrets
   - The PR Security Bot will detect and flag hardcoded secrets

2. **Review security scan results**:
   - Check the PR comment from PR Security Bot
   - Download artifacts for detailed analysis
   - Fix ❌ FAIL issues before requesting review

3. **Keep dependencies updated**:
   - Dependabot will automatically create PRs for updates
   - Review and merge dependency PRs promptly
   - Check CHANGELOG.md for breaking changes

4. **Use PrivilegedCommand pattern**:
   - Always use `utils/commands.py::PrivilegedCommand` for `pkexec` operations
   - Never use raw `subprocess` calls with `sudo`
   - This prevents B404/B603/B602 Bandit warnings

### For Maintainers

1. **Monitor security reports**:
   - Review weekly Trivy/Bandit reports from CI
   - Check GitHub Security tab for Dependabot alerts
   - Enable "Require approval for Dependabot PRs" in repo settings

2. **Audit bot configurations**:
   - Review `.github/workflows/pr-security-bot.yml` quarterly
   - Update Bandit/Trivy rules as needed
   - Adjust stale cleanup thresholds based on project velocity

3. **MCP server permissions**:
   - GitHub Copilot MCP server uses GitHub Actions token scope
   - No additional credentials needed
   - Review GitHub App permissions in repo settings

---

## Troubleshooting

### MCP not working in VS Code

**Symptom**: `@github` commands return "Server not found"

**Fix**:
1. Verify GitHub Copilot extension is enabled
2. Check `.vscode/mcp.json` syntax (must be valid JSON)
3. Restart VS Code
4. Try: `Ctrl+Shift+P` → "Copilot: Reload Extensions"

### PR Security Bot not commenting

**Symptom**: Workflow runs but no PR comment

**Check**:
1. Workflow logs: `.github/workflows/pr-security-bot.yml` → Actions tab
2. Permissions: Ensure bot has `pull-requests: write` permission
3. Branch protection: If required checks are enabled, bot may be blocked

### Dependabot auto-merge not working

**Symptom**: Patch PRs are not auto-merging

**Check**:
1. CI must pass before auto-merge triggers
2. Branch protection rules must allow auto-merge
3. Verify PR is from `dependabot[bot]`, not `dependabot-preview[bot]`

---

## Additional Resources

- [GitHub Copilot MCP Documentation](https://docs.github.com/en/copilot/using-github-copilot/using-mcp-with-github-copilot)
- [MCP Protocol Specification](https://modelcontextprotocol.io/introduction)
- [Bandit Security Scanner](https://bandit.readthedocs.io/)
- [Trivy Vulnerability Scanner](https://trivy.dev/)
- [detect-secrets](https://github.com/Yelp/detect-secrets)

---

## Contributing

If you encounter issues with MCP setup or automated workflows:

1. Open an issue with label `ci/cd` or `security`
2. Include workflow logs if applicable
3. Describe expected vs actual behavior

**Maintainers**: Tag with `@loofitheboss` for urgent security issues.

---

*Last updated: 2026-02-13*
