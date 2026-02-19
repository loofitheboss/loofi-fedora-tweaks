# Release Notes -- v48.0.1 "Sidebar Index"

**Release Date:** 2026-02-19
**Codename:** Sidebar Index
**Theme:** Comprehensive stabilization pass — API hardening, privilege hygiene, test expansion

## Summary

Patch release for v48.0.0 applying comprehensive stabilization: API command allowlisting, auth-gated endpoints, sudo string removal, 282 new tests across 10 modules, CI dependency auditing, and documentation updates.

## Highlights

- API `/execute` endpoint hardened with `COMMAND_ALLOWLIST` (30+ executables) — non-allowlisted commands return 403
- `/info` and `/agents` endpoints gated with Bearer JWT authentication
- 4 hardcoded `sudo dnf` strings replaced with safe `build_install_hint()` calls
- 10 new test files covering previously untested security-sensitive modules
- CI `dependency_audit` job added (pip-audit)

## Changes

### Security

- `COMMAND_ALLOWLIST` frozenset guards `/execute` endpoint with audit logging
- Bearer JWT auth on `/info` and `/agents` endpoints
- Version removed from `/health` response (information disclosure fix)
- Sudo-string AST check added to stabilization rules (Rule 5)

### Testing

- 282 new test methods across: auth, clipboard sync, state teleport, VFIO, AI models, disposable VM, mesh discovery, voice, arbitrator, agent scheduler
- Fixed PyQt6 test pollution (module-level import in conftest.py)
- Aligned existing tests with API hardening changes

### Documentation

- API Threat Model in SECURITY.md
- ARCHITECTURE.md updated to v48.0.0 with 82% coverage
- ROADMAP.md v46 ACTIVE → DONE

## Stats

- **Tests:** 6240 passed, 95 skipped, 0 failed
- **Lint:** 0 errors
- **Coverage:** 82%
- **CI Jobs:** 14/14 green

## Upgrade Notes

No user-facing changes. Internal security and testing improvements only.

- **Tests:** TODO passed, TODO skipped, 0 failed
- **Lint:** 0 errors
- **Coverage:** TODO%

## Upgrade Notes

TODO — or "No user-facing changes."
