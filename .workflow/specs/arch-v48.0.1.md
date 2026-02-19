# Architecture — v48.0.1

## Goals

- Stabilization patch: harden API, remove privilege hygiene gaps, expand test coverage

## Decisions

- API `/execute` uses `COMMAND_ALLOWLIST` frozenset for O(1) validation
- Bearer JWT auth on info/agents endpoints via existing `AuthManager`
- `build_install_hint()` replaces all raw sudo strings
- pip-audit added to CI as non-blocking audit job
