# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| v35.x   | ✅ Active  |
| v34.x   | ✅ Security fixes only |
| < v34   | ❌ End of life |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Loofi Fedora Tweaks, please report it responsibly.

### How to Report

1. **GitHub Security Advisories (preferred)**: [Create a private security advisory](https://github.com/loofitheboss/loofi-fedora-tweaks/security/advisories/new)
2. **Email**: security@loofi.dev (if available)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Potential impact assessment
- Any suggested fixes (optional)

### What to Expect

| Timeline | Action |
|----------|--------|
| 48 hours | Acknowledgment of your report |
| 7 days   | Initial assessment and severity classification |
| 30 days  | Fix developed and tested |
| 90 days  | Public disclosure (coordinated with reporter) |

We follow a **90-day responsible disclosure timeline**. If a fix takes longer, we will communicate the timeline and provide interim mitigations.

## Security Architecture

### Privilege Escalation

- All privileged operations use **Polkit (`pkexec`)** — never `sudo`
- Granular Polkit policies per capability (firewall, network, storage, etc.)
- `PrivilegedCommand` builder validates parameters before execution
- All privileged actions are audit-logged to `~/.config/loofi-fedora-tweaks/audit.jsonl`

### Subprocess Safety

- All `subprocess.run()` and `subprocess.check_output()` calls include `timeout` parameter
- No shell string interpolation — commands use argument lists
- `CommandRunner` wraps `QProcess` for async GUI operations

### Data Handling

- No telemetry or data collection
- Configuration stored locally at `~/.config/loofi-fedora-tweaks/`
- Plugin sandbox restricts file system and network access
- API server binds to localhost by default (requires `--unsafe-expose` for network binding)

### Dependencies

- Minimal dependency footprint (PyQt6, standard library)
- Dependabot monitors for vulnerable dependencies
- CI runs Bandit, pip-audit, and Trivy on every PR

## Scope

The following are **in scope** for security reports:

- Privilege escalation beyond intended Polkit policies
- Command injection via parameter validation bypass
- Unauthorized file access or modification
- Plugin sandbox escape
- API authentication bypass
- Information disclosure of sensitive system data

The following are **out of scope**:

- Attacks requiring physical access to the machine
- Social engineering
- Denial of service against local-only services
- Issues in upstream dependencies (report to upstream maintainers)

## Security Updates

Security fixes are released as patch versions (e.g., v35.0.1) and announced via:
- GitHub Releases
- CHANGELOG.md
- GitHub Security Advisories
