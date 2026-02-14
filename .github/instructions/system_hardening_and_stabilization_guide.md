# SYSTEM_HARDENING_AND_STABILIZATION_GUIDE

## Purpose

This document defines the mandatory stabilization, hardening, and trust-building work required before introducing new major features.
All AI agents (Claude, Copilot, Cline, etc.) must treat this as a priority directive.

No new feature expansion is allowed before items in Phase 1 and Phase 2 are completed.

---

## Core Principle

Loofi Fedora Tweaks is a privileged system-level tool.

Security, rollback safety, deterministic packaging, and predictable behavior are more important than feature count.

If there is ever a trade-off between velocity and safety, safety wins.

---

# PHASE 1 – Installation & Distribution Hardening (Critical)

1. Remove “curl | bash” as primary install method.
   - Move to “Advanced / at your own risk”.
   - Default install path must use signed RPM or Copr.

2. Implement signed RPM distribution.
   - GPG-sign repository metadata.
   - Publish sha256 checksums for releases.
   - CI must verify artifact integrity.

3. Standardize RPM spec.
   - Proper %prep, %build, %install, %files sections.
   - No implicit file inclusion.
   - Version sourced from a single canonical file.

4. Enforce reproducible builds.
   - Deterministic version injection.
   - CI builds via mock or clean container.

---

# PHASE 2 – Privilege Boundary Enforcement (Critical)

1. Eliminate arbitrary shell execution as root.
   - Introduce named privileged actions.
   - Strict allowlist.
   - Parameter schema validation required.

2. Polkit separation.
   - One policy per privileged capability.
   - No global “admin mode”.

3. Add structured audit logging.
   - Timestamp
   - Action name
   - Sanitized parameters
   - Exit code
   - stderr hash

4. Add timeout enforcement on all subprocess calls.

5. Add dry-run mode for all system mutations.

---

# PHASE 3 – API Security & Exposure Control

1. Default bind must remain 127.0.0.1.
2. External exposure requires explicit `--unsafe-expose` flag.
3. Implement rate limiting for authentication endpoints.
4. Fix auth storage implementation.
   - Proper JSON storage.
   - Correct file permissions.
5. Separate read-only vs privileged API endpoints.
6. Document threat model for API mode.

---

# PHASE 4 – UX Stabilization & Scope Control

1. Introduce Safe Mode (default on first launch).
   - Read-only diagnostics.
   - Explicit toggle required for mutations.

2. Implement risk classification per tweak.
   - Low / Medium / High
   - Show revert instructions.

3. Add rollback/undo support.
   - Config backup minimum.
   - Snapshot integration where possible.

4. Define primary user journeys:
   - Post-install checklist
   - Health dashboard
   - Performance profile switch

All other advanced modules must be secondary.

---

# PHASE 5 – Plugin & Daemon Integrity

1. Disable automatic plugin updates by default.
2. Require manifest version + checksum validation.
3. Implement rollback mechanism for plugin updates.
4. Harden daemon via systemd restrictions where applicable.
5. Ensure daemon cannot execute arbitrary commands.

---

# PHASE 6 – Version & Consistency Cleanup

1. Single canonical version source.
2. UI, API, daemon must report identical version.
3. Remove hardcoded version inconsistencies.
4. Add SECURITY.md with disclosure process.

---

## Operational Rules for AI Agents

When working on this repository:

- Do not introduce new large feature sets.
- Refactor before expanding.
- Prefer explicit configuration over magic behavior.
- Never expand root-level capability without:
  - validation
  - audit log
  - rollback strategy
- If unsure, default to restrictive behavior.

---

## Definition of “Stabilized”

The application is considered stabilized when:

- Installation is cryptographically verifiable.
- Privileged execution is strictly bounded.
- Rollback exists for destructive operations.
- API exposure is safe by default.
- Packaging is reproducible.
- Documentation matches actual behavior.

Only after stabilization may large feature expansions resume.

