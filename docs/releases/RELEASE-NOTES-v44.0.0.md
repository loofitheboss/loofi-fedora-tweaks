# Release Notes -- v44.0.0 "Review Gate"

**Release Date:** 2026-02-16
**Codename:** Review Gate
**Theme:** Fedora review prerequisite enforcement for packaging and release workflows

## Summary

v44.0.0 introduces a required Fedora review tooling gate across local workflow execution
and GitHub Actions pipelines. The release ensures package/release phases fail fast when
`fedora-review` is unavailable or unhealthy.

## Highlights

- New checker script: `scripts/check_fedora_review.py`
- Workflow runner gating for write-mode `package` and `release`
- Required `fedora_review` CI gate in both `ci.yml` and `auto-release.yml`
- Workflow/docs/test contracts updated for the new requirement

## Changes

### Added

- `scripts/check_fedora_review.py`
- `tests/test_check_fedora_review.py`
- `tests/test_workflow_fedora_review_contract.py`

### Changed

- `scripts/workflow_runner.py` now blocks write-mode `package`/`release` when Fedora review checks fail.
- `.github/workflows/ci.yml` now includes a required `fedora_review` job.
- `.github/workflows/auto-release.yml` now includes a required `fedora_review` job and build hard-depends on it.
- `.github/workflow/PIPELINE.md`, `.github/workflow/QUICKSTART.md`, `.github/workflow/prompts/package.md`, and `.github/workflow/prompts/release.md` now document Fedora review prerequisites.
- `README.md` and `docs/RELEASE_CHECKLIST.md` now include the Fedora review gate in release flow guidance.

### Fixed

- N/A (workflow contract hardening release).

## Validation

- Targeted tests include checker behavior, workflow runner gate behavior, and CI workflow contract assertions.
- Version alignment updated to `44.0.0` across `version.py`, `.spec`, and `pyproject.toml`.

## Upgrade Notes

Install Fedora review tooling on Fedora hosts used for package/release operations:

```bash
dnf install -y fedora-review
```
