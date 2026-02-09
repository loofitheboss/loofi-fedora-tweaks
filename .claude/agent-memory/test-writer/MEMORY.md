# Test Writer Memory — Loofi Fedora Tweaks

## Project Test Structure
- Test directory: `/workspaces/loofi-fedora-tweaks/tests/`
- Naming convention: `test_<module_name>.py`
- Test runner: pytest with `-v` flag for verbose output
- No root/sudo required — all tests mock system calls

## Mocking Patterns

### ActionExecutor Mocking
- Mock at `utils.action_executor.ActionExecutor.run`
- Return `ActionResult` objects with structured fields
- ActionResult must include: success, message, exit_code, stdout, stderr, preview, action_id
- Use `@patch` decorator or context manager with `unittest.mock.patch`

### FastAPI Testing
- Use `fastapi.testclient.TestClient` for HTTP testing
- Create pytest fixtures for test client, auth tokens, mocks
- Exception handling: FastAPI lets unhandled exceptions propagate (test with `pytest.raises`)
- Token endpoint returns 200 with `{"error": "..."}` for validation errors (not 422)

### Authentication Testing
- `AuthManager.generate_api_key()` creates new API keys
- Token flow: generate key → POST /api/token → get JWT → use in Bearer header
- Mock `jose.jwt.encode/decode` for expired token tests
- Auth failures return 401 with `{"detail": "..."}` in response

## Security Test Coverage Areas
1. **Authentication**: Missing/invalid/expired tokens, wrong API keys
2. **Input Validation**: Command injection, path traversal, malformed JSON, extremely long inputs
3. **Authorization**: pkexec requires auth, read-only endpoints (/api/health, /api/info) don't
4. **Error Handling**: Invalid commands, executor exceptions, timeouts

## Common System Call Boundaries
- `ActionExecutor.run()` — centralized command execution (v19.0)
- `subprocess.run()` — underlying system call wrapper
- `SystemMonitor.get_system_health()` — system metrics
- `ConfigManager` — file I/O for config storage
- `AuthManager` — JWT and bcrypt operations

## Test Fixtures Best Practices
- `test_client`: FastAPI test client instance
- `valid_api_key`: Generated API key for auth tests
- `valid_token`: JWT token from valid_api_key
- `mock_action_executor`: Mocked ActionExecutor.run with default ActionResult
- Fixtures should be independent and reusable across test classes

## Edge Cases to Always Test
- Empty strings, None values, missing required fields
- Extremely long inputs (DoS protection)
- Unicode and special characters
- Malformed JSON payloads
- Exception propagation through the API layer

## PyQt6 Testing Patterns

### Environment Setup
- ALWAYS set `QT_QPA_PLATFORM=offscreen` before Qt imports
- Use `@unittest.skipUnless(_HAS_QT_WIDGETS, ...)` to skip when PyQt6 unavailable
- Initialize Qt in `setUpClass`: `cls.app = QApplication.instance() or QApplication([])`
- Call `.show()` and `app.processEvents()` before geometry checks

### Main Window Testing
- Mock system-facing methods: `_start_pulse_listener`, `setup_tray`, `check_dependencies`, `_check_first_run`
- Pattern: `patch.object(MainWindow, method_name, lambda self: None)`
- Always call `window.close()` in cleanup

### Tab Testing
- Standard margins: `ui.tab_utils.CONTENT_MARGINS = (20, 16, 20, 16)`
- Retrieve via `layout.getContentsMargins()` → `(left, top, right, bottom)`
- AIEnhancedTab: Mock `utils.ai_models`, `utils.voice`, `utils.context_rag`
- SettingsTab: Patch `SettingsManager.instance()` with mock

### Geometry Checks
- Min window: 800x500, Breadcrumb: `_line_height * 3`, Status: `_line_height * 2`, Sidebar: `_line_height * 15`
- Assert > 0, not exact values (HiDPI varies)

## Architecture Import Testing (v23.0)
- Import tests validate refactor integrity without system calls
- Test both new locations (`core.executor`, `services.*`) and backward-compat shims (`utils.*`)
- Verify object identity: old and new imports must reference same class (`is` check, not `==`)
- Test `__all__` exports match expected public API surface
- Import performance tests ensure no expensive initialization (<1s threshold)
- Abstract base classes should fail instantiation with `pytest.raises(TypeError)`
- Deprecation warnings appear for old import paths (intentional for backward compat)

## Lessons Learned
- FastAPI's test client raises exceptions when endpoints raise unhandled exceptions
- API validation errors may return 200 with error payload instead of HTTP error codes
- Always verify mock call arguments, not just return values
- Token expiration requires mocking `jwt.decode` to raise `ExpiredSignatureError`
- CI environments may lack OpenGL; tests skip gracefully via `@unittest.skipUnless`
- HiDPI layout uses font metrics for scalable dimensions
- v23.0 architecture: `core/` (base), `services/` (managers), `utils/` (backward compat shims)
