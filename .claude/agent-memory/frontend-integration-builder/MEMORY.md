# Frontend Integration Builder Memory

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
