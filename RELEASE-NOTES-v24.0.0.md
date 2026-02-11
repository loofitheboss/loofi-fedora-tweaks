# Release Notes v24.0.0 "Power Features"

Released: 2026-02-10

## Highlights

- Introduce versioned profile schema models (`ProfileRecord`, `ProfileBundle`) in `core/profiles/`.
- Add `ProfileStore` for profile CRUD and single/bundle JSON import/export.
- Extend profile CLI with `export`, `import`, `export-all`, `import-all` plus overwrite/snapshot flags.
- Add profile API endpoints for list/apply/import/export workflows.
- Add snapshot-before-apply profile integration with graceful fallback warnings.
- Add live log panel in `Logs` tab with incremental polling and bounded buffer.

## API Endpoints

- `GET /api/profiles`
- `POST /api/profiles/apply`
- `GET /api/profiles/{name}/export`
- `POST /api/profiles/import`
- `GET /api/profiles/export-all`
- `POST /api/profiles/import-all`

## CLI Additions

```bash
loofi profile export <name> <path>
loofi profile import <path> [--overwrite]
loofi profile export-all <path> [--include-builtins]
loofi profile import-all <path> [--overwrite]
loofi profile apply <name> [--no-snapshot]
```

## Notes

- Legacy profile JSON remains supported for loading/import.
- Built-in profiles remain non-overwritable and non-deletable.

## Full Changelog

- See `CHANGELOG.md` for complete details.
