# Frontend Integration Builder Memory

## v25.0 Plugin Architecture — MainWindow Integration

### Key files

- `loofi-fedora-tweaks/ui/main_window.py` — sidebar now sourced from PluginRegistry
- `loofi-fedora-tweaks/core/plugins/` — all 6 plugin arch modules implemented (Tasks 1-8)
- `loofi-fedora-tweaks/assets/modern.qss` — QSS for disabled plugin items added at end

### MainWindow patterns (Tasks 9-10)

- `_build_sidebar_from_registry(context)` — called from `__init__`, replaces 26 hardcoded `add_page()` calls
- `_wrap_in_lazy(plugin)` — wraps `plugin.create_widget` (bound method, zero-arg) in `LazyWidget`
- `_add_plugin_page(meta, widget, compat)` — bridges PluginMetadata → `add_page()` kwargs
- `add_page()` now accepts `disabled: bool = False` and `disabled_reason: str = ""` kwargs
- `DisabledPluginPage(meta, reason)` — QWidget placeholder; label objectName="disabledPluginLabel"
- `PluginRegistry` is singleton — tests must call `PluginRegistry.reset()` in teardown
- Context dict: `{"main_window": self, "config_manager": ConfigManager, "executor": None}`

### QSS additions (modern.qss section v25.0)

- `QLabel#disabledPluginLabel` — color #6c6f85, font-size 14px, padding 40px
- `QTreeWidget#sidebar QTreeWidgetItem:disabled` — color #6c6f85, font-style italic

### PluginMetadata and CompatStatus

- PluginMetadata required fields: `id`, `name`, `description`, `category`, `icon`, `badge`
- CompatStatus fields: `compatible: bool`, `reason: str = ""`

## Theme System Patterns (GTK/PyQt6)

### Replacing Inline Styles with Theme-Aware Approach
- **NEVER** use hardcoded hex colors in setStyleSheet() calls
- **ALWAYS** use setObjectName() + QSS rules in modern.qss/light.qss
- Pattern: Remove setStyleSheet() → Add setObjectName("uniqueName") → Add QSS rules to both theme files

### Color Mappings (Catppuccin Mocha → Latte)
- Dark accent blue: #89b4fa → Light accent blue: #1e66f5
- Dark background: #1e1e2e → Light background: #eff1f5
- Dark surface: #313244 → Light surface: #ccd0da
- Dark text: #cdd6f4 → Light text: #4c4f69
- Dark muted: #a6adc8 → Light muted: #6c6f85
- Yellow warning: #f9e2af → Orange warning: #df8e1d
- Red error: #f38ba8 → Red error: #d20f39
- Green success: #a6e3a1 → Green success: #40a02b

### Component-Specific ObjectNames
- Dashboard: systemBadge, rebootBanner, rebootLabel, rebootButton, dashboardCard, quickActionButton
- Notification: notificationPanel
- Lazy Loading: loadingLabel, errorLabel

### QSS Section Naming Convention
- Use v-prefixed comments: /* ===== v20.1 Component Name ===== */
- Group related components under same section
- Place new sections at end of file before closing

## Web Dashboard Patterns

### API Structure
- Backend: FastAPI server in `loofi-fedora-tweaks/utils/api_server.py`
- Routes: Modular routers in `loofi-fedora-tweaks/api/routes/` (system.py, executor.py)
- Authentication: JWT tokens via `utils/auth.py` (AuthManager class)

### Static File Serving
- Web files: `loofi-fedora-tweaks/web/` directory
- Assets: `web/assets/` (style.css, app.js)
- Pattern: Mount StaticFiles for /assets, FileResponse for / (index.html)
- Path resolution: `Path(__file__).parent.parent / "web"`

### API Response Structures
- `/api/info`: Returns nested health data with version, codename, system_type, package_manager, health.cpu, health.memory
- `/api/agents`: Returns {agents: [], states: [], summary: {}}
- `/api/token`: Accepts form-urlencoded api_key, returns {access_token, token_type}

### Frontend Patterns
- Vanilla JS (no frameworks) - matches project philosophy
- Dark theme with CSS variables in :root
- Mobile-first responsive design
- SessionStorage for JWT token persistence
- Auto-redirect to login on 401 responses
- Auto-refresh system/agent data every 10s

### Authentication Flow
1. User submits API key via form-urlencoded POST to /api/token
2. Backend returns JWT token in {access_token, token_type: "bearer"}
3. Frontend stores in sessionStorage
4. All protected requests include: Authorization: Bearer <token>
5. 401 response triggers logout and redirect to login

### Design Constraints
- Match GTK app dark theme aesthetic (#1a1a1a primary, #2d2d2d secondary)
- Minimal dependencies (no npm/webpack)
- Mobile Safari and Chrome compatibility required
- User-friendly error messages (no raw tracebacks)

## Files Created
- `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/web/index.html`
- `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/web/assets/style.css`
- `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/web/assets/app.js`

## Files Modified
- `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/api_server.py` (added static file serving)
