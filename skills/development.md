# Development Skills

## Developer Tools
- **Toolchain management** — Install and manage development toolchains
- **IDE integration** — Configure VS Code and other editors
- **Container support** — Podman/Docker container management
- **Language runtimes** — Manage Python, Node.js, Go, Rust installations

**Modules:** `utils/devtools.py`, `utils/vscode.py`
**UI:** Development Tab

## Container Management
- **Podman integration** — Build, run, manage OCI containers
- **Image management** — Pull, list, remove container images
- **Container networking** — Configure container network settings

**Modules:** `utils/containers.py`
**UI:** Development Tab

## VS Code Integration
- **Workspace setup** — Configure VS Code workspace for Fedora development
- **Extension management** — Install recommended VS Code extensions
- **Settings sync** — Synchronize VS Code settings

**Modules:** `utils/vscode.py`
**UI:** Development Tab

## Diagnostics
- **Dependency doctor** — Check for missing system dependencies
- **Boot analysis** — Identify slow boot services and configurations
- **System validation** — Verify system integrity and configuration
- **Health check** — Run comprehensive system health diagnostics

**Modules:** `utils/boot_analyzer.py`, `core/diagnostics/`
**UI:** Diagnostics Tab
**CLI:** `doctor`

## Configuration Management
- **Config file management** — Read, write, validate configuration files
- **Environment management** — Manage environment variables and dotenv files
- **Settings persistence** — Save and load application settings

**Modules:** `utils/config_manager.py`, `utils/settings.py`, `utils/dotenv.py`
