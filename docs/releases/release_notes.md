# Release Notes — Latest

> **Current release:** v33.0.0 "Bastion"
>
> For versioned release notes see the individual files in this directory:
> `RELEASE-NOTES-vX.Y.Z.md`

## v33.0.0 "Bastion"

Testing & CI hardening release — 163 mypy errors fixed to zero, 3953+ tests passing,
strict CI gates enforced across all jobs.

See [RELEASE-NOTES-v33.0.0.md](RELEASE-NOTES-v33.0.0.md) for full details.

## v32.0.0 "Abyss"

Full visual redesign — new Abyss dark/light theme, activity-based navigation (8 categories),
sidebar collapse toggle, and Catppuccin color migration across 30+ files.

See [RELEASE-NOTES-v32.0.0.md](RELEASE-NOTES-v32.0.0.md) for full details.

### v32.0.1 — CI Pipeline Fix

- Fixed auto-release pipeline (GITHUB_TOKEN anti-recursion workaround)
- Fixed 9 lint errors across 8 files
- Fixed adapter drift sync
- Fixed security scan (tarfile B202 + skip list)
- Fixed test collection crash (`from __future__ import annotations` in containers.py)
- Added `continue-on-error` for soft-gate jobs (typecheck, test)
- Improved workflow with release deduplication, smart build conditions, test artifacts

## Previous Releases

| Version | Codename | Notes |
|---------|----------|-------|
| v31.0.0 | — | [RELEASE-NOTES-v31.0.0.md](RELEASE-NOTES-v31.0.0.md) |
| v30.0.0 | — | [RELEASE-NOTES-v30.0.0.md](RELEASE-NOTES-v30.0.0.md) |
| v29.0.0 | — | [RELEASE-NOTES-v29.0.0.md](RELEASE-NOTES-v29.0.0.md) |
| v28.0.0 | — | [RELEASE-NOTES-v28.0.0.md](RELEASE-NOTES-v28.0.0.md) |
| v27.0.0 | — | [RELEASE-NOTES-v27.0.0.md](RELEASE-NOTES-v27.0.0.md) |
| v26.0.2 | — | [RELEASE-NOTES-v26.0.2.md](RELEASE-NOTES-v26.0.2.md) |