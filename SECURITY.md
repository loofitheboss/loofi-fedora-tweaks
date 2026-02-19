# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| v48.x   | Active  |
| v47.x   | Security fixes only |
| v46.x   | Security fixes only |
| < v46   | End of life |

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

## API Threat Model

The optional REST API server (`--api` mode) exposes system operations over HTTP. It is designed for local automation and must never be exposed to untrusted networks.

### Binding & Network Exposure

| Setting | Binding | Risk Level |
|---------|---------|------------|
| Default | `127.0.0.1:8000` | Low — localhost only |
| `--unsafe-expose` | `0.0.0.0:8000` | **High** — network-accessible |

The `--unsafe-expose` flag is required to bind to all interfaces and logs a security warning on startup.

### Authentication

- **JWT HS256** tokens with 3600s (1 hour) lifetime
- **bcrypt** hashed API keys stored in `~/.config/loofi-fedora-tweaks/auth.json`
- Bearer token required on all endpoints except `GET /health`
- No token revocation (tokens expire naturally)

### Endpoint Security

| Endpoint | Auth | Risk | Mitigations |
|----------|------|------|-------------|
| `GET /health` | None | Minimal | Returns `{"status": "ok"}` only — no version leak |
| `GET /api/info` | Bearer JWT | Low | Read-only system info |
| `GET /api/agents` | Bearer JWT | Low | Read-only agent list |
| `POST /api/execute` | Bearer JWT | **Critical** | Command allowlist (30+ approved executables), audit logging, parameter validation |
| `POST /api/preview` | Bearer JWT | Medium | Dry-run only, audit-logged |

### Command Allowlist (`POST /execute`)

The executor enforces a `COMMAND_ALLOWLIST` frozenset. Only executables listed in the allowlist (derived from `PrivilegedCommand` builders + read-only diagnostics) can be invoked. Disallowed commands return HTTP 403 with an audit log entry.

Allowlisted categories:
- **Package management**: `dnf`, `rpm-ostree`, `flatpak`, `rpm`
- **System services**: `systemctl`, `journalctl`, `loginctl`, `hostnamectl`, `timedatectl`
- **Hardware/firmware**: `fwupdmgr`, `fstrim`, `lsblk`, `lspci`, `lsusb`, `lscpu`, `sensors`
- **Network**: `nmcli`, `firewall-cmd`, `ip`, `ss`, `resolvectl`
- **Privilege**: `pkexec` (Polkit escalation)
- **Diagnostics**: `uname`, `cat`, `grep`, `free`, `df`, `findmnt`, `sysctl`

### Known Limitations

- No rate limiting on API endpoints (mitigated by localhost-only default)
- No token revocation mechanism (1-hour expiry is the only control)
- No TLS by default (acceptable for localhost; not for `--unsafe-expose`)

### Recommendations for Operators

1. **Never** use `--unsafe-expose` on machines accessible from untrusted networks
2. Rotate API keys periodically via `AuthManager.generate_api_key()`
3. Monitor `audit.jsonl` for unexpected command patterns
4. Consider a reverse proxy with TLS if remote access is required

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
