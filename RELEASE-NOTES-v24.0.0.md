# Release Notes v24.0.0 "Power Features"

Released: 2026-02-10

## Highlights

- Add versioned profile schema models (`ProfileRecord`, `ProfileBundle`) and a storage layer with legacy JSON compatibility.
- Add profile API routes for list/apply/import/export workflows (`/api/profiles`, `/api/profiles/apply`, `/api/profiles/{name}/export`, `/api/profiles/import`, `/api/profiles/export-all`, `/api/profiles/import-all`).
- Extend `loofi profile` CLI with `export`, `import`, `export-all`, `import-all`, `--overwrite`, `--include-builtins`, and `--no-snapshot`.
- Update Profiles tab workflows with per-profile export and bundle import/export actions.
- Integrate snapshot-before-apply into profile application with graceful fallback warnings when no snapshot backend is available.
- Add live log panel controls in Logs tab (start/stop polling, interval control, bounded buffer).
- Fix Logs tab export flow to pass fetched entries to `SmartLogViewer.export_logs()`.
- Expand automated coverage for profile storage, profile UI/CLI/API paths, and live log polling.

## Full Changelog

- See `CHANGELOG.md` for complete details.
