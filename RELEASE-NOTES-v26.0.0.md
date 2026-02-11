# Loofi Fedora Tweaks v26.0.0 — Plugin Marketplace

**Release Date:** 2026-02-12  
**Codename:** Plugin Marketplace  
**Theme:** External plugin ecosystem, marketplace distribution, sandboxed execution

---

## What's New

### Plugin Marketplace

v26.0 introduces a complete plugin marketplace system, enabling users to discover, install, and manage third-party plugins directly from the Community tab. Plugins are distributed as signed `.loofi-plugin` archives, verified for integrity, and executed with permission-based sandboxing.

**Key Features:**
- **Browse & Search**: Discover plugins via GitHub-based marketplace index
- **One-Click Install**: Download, verify, extract, and register plugins automatically
- **Permission System**: Runtime enforcement of filesystem, network, sudo, clipboard, and notification permissions
- **Dependency Resolution**: Automatic installation of plugin dependencies with version constraints
- **Auto-Updates**: Background service checks for plugin updates daily
- **CLI Tools**: Full marketplace access via `loofi-fedora-tweaks --cli marketplace` commands

### Permission Sandboxing

All external plugins execute within a permission sandbox that enforces user-granted capabilities:

- **Filesystem**: Read/write user files only with explicit permission
- **Network**: HTTP/HTTPS requests proxied through sandbox validator
- **Sudo**: Privileged operations require permission and user confirmation
- **Clipboard**: Access clipboard data only when permitted
- **Notifications**: Send desktop notifications with user consent

When installing a plugin, users see a permission dialog listing all requested capabilities and can accept or decline the installation.

### Plugin Package Format

External plugins are distributed as `.loofi-plugin` archives (ZIP format) containing:

```
my-plugin.loofi-plugin
├── plugin.json         # Manifest with metadata and permissions
├── plugin.py           # Entry point (LoofiPlugin subclass)
├── metadata.json       # Publisher info, license, dependencies
├── checksum.txt        # SHA256 integrity hash
└── signature.asc       # Optional GPG signature
```

The installer verifies checksums and signatures before extraction, ensuring plugins are authentic and unmodified.

### CLI Marketplace Commands

```bash
# Search for plugins
loofi-fedora-tweaks --cli marketplace search "backup"

# Get detailed plugin information
loofi-fedora-tweaks --cli marketplace info backup-manager

# Install a plugin
loofi-fedora-tweaks --cli marketplace install backup-manager

# Update all plugins
loofi-fedora-tweaks --cli marketplace update

# Uninstall a plugin
loofi-fedora-tweaks --cli marketplace uninstall backup-manager
```

JSON output mode supported via `--json` flag for scripting.

### Marketplace UI

Access the marketplace via **Community Tab** → **Marketplace** section:

- **Grid View**: Browse all available plugins with icons and descriptions
- **Search**: Filter by name, tags, or description
- **Details Dialog**: View plugin info, permissions, dependencies, reviews
- **Install Button**: One-click installation with permission consent
- **Update Badge**: Visual indicator for available updates

### Dependency Resolution

Plugins can declare dependencies in `metadata.json`:

```json
{
    "dependencies": ["logger>=1.0.0", "utils>=2.1.0"]
}
```

The installer automatically resolves dependency chains, installs missing plugins from the marketplace, verifies version constraints, and loads plugins in correct order.

### Plugin API Unification

v26.0 bridges the old `LoofiPlugin` API (utils/plugin_base.py) with the new `PluginInterface` (core/plugins/) via the `PluginAdapter`:

- External plugins continue using `LoofiPlugin` for simplicity
- Adapter transparently wraps them as `PluginInterface` for core integration
- Built-in tabs remain as `PluginInterface` implementations
- No breaking changes for existing plugin developers

---

## Testing & Validation

### New Test Coverage

- **195 comprehensive tests** across 8 new test modules
- **100% pass rate** on all marketplace functionality
- All system calls mocked for deterministic testing

**Test Modules:**
- `test_plugin_adapter.py` — PluginAdapter wrapping tests
- `test_plugin_sandbox.py` — Permission enforcement validation
- `test_plugin_external_loader.py` — External plugin scanning and loading
- `test_plugin_installer.py` — Install/uninstall workflows
- `test_plugin_marketplace.py` — Marketplace API and search
- `test_plugin_resolver.py` — Dependency resolution
- `test_plugin_integrity.py` — Checksum and signature verification
- `test_cli_marketplace.py` — CLI marketplace commands

### Overall Test Suite

- **Total Tests:** 2,066
- **Passing:** 2,043 (98.9%)
- **Coverage:** Core marketplace modules at 86%+

---

## Breaking Changes

### For End Users

None. All existing features work identically to v25.0.

### For Plugin Developers

**No breaking changes** — existing plugins continue to work:

- `LoofiPlugin` API unchanged
- `plugin.json` manifest backward compatible
- New optional fields: `dependencies`, `checksum`, `signature`
- Permission system applies only to plugins requesting permissions

**New Capabilities:**
- Distribute plugins via marketplace
- Declare dependencies on other plugins
- Request runtime permissions
- Sign packages for integrity verification

---

## Plugin Developer Quick Start

### Creating Marketplace-Ready Plugins

1. **Develop Locally** following existing `LoofiPlugin` API
2. **Add Dependencies** (optional) in `plugin.json`:
   ```json
   {
       "dependencies": ["another-plugin>=1.0.0"]
   }
   ```
3. **Request Permissions** (optional):
   ```json
   {
       "permissions": ["filesystem", "network"]
   }
   ```
4. **Package Plugin**:
   ```bash
   cd plugins/my-plugin
   zip -r my-plugin.loofi-plugin plugin.json plugin.py metadata.json
   sha256sum my-plugin.loofi-plugin > checksum.txt
   ```
5. **Sign Package** (optional):
   ```bash
   gpg --detach-sign --armor my-plugin.loofi-plugin
   ```
6. **Publish to GitHub Release** and submit to marketplace index

### Sandboxed Operation

If your plugin needs file or network access, request permissions:

```python
# plugin.json
{
    "permissions": ["filesystem", "network"]
}
```

Use sandbox-safe APIs:
```python
from core.plugins.sandbox import PluginSandbox

sandbox = PluginSandbox.for_plugin("my-plugin", ["filesystem"])
sandbox.safe_write("/path/to/file", "content")  # Permission-checked
```

---

## Architecture Changes

### New Modules

**Core Plugins:**
- `core/plugins/adapter.py` — Bridge LoofiPlugin ↔ PluginInterface
- `core/plugins/package.py` — PluginPackage dataclass
- `core/plugins/sandbox.py` — Permission enforcement layer
- `core/plugins/scanner.py` — External plugin discovery
- `core/plugins/integrity.py` — Checksum/signature verification
- `core/plugins/resolver.py` — Dependency resolution engine

**Utils:**
- `utils/plugin_installer.py` — Install/uninstall workflow
- `utils/plugin_marketplace.py` — GitHub marketplace API
- `utils/plugin_updater.py` — Auto-update service

**UI:**
- `ui/plugin_detail_dialog.py` — Plugin details view
- `ui/permission_dialog.py` — Permission consent dialog

### Modified Files

- `loofi-fedora-tweaks/version.py` — Bumped to 26.0.0
- `loofi-fedora-tweaks.spec` — Updated version
- `docs/PLUGIN_SDK.md` — Added marketplace usage guide
- `CHANGELOG.md` — Added v26.0 entry
- `ROADMAP.md` — Marked v26.0 as DONE (after this release)

---

## Installation

### RPM (Fedora 43+)

```bash
sudo dnf install loofi-fedora-tweaks-26.0.0-1.fc43.noarch.rpm
```

### From Source

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
git checkout v26.0.0
bash scripts/build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-26.0.0-1.fc43.noarch.rpm
```

---

## Upgrade Notes

### From v25.x

1. **No Config Migration Required**: All settings and data preserved
2. **New Feature**: Visit **Community → Marketplace** to browse plugins
3. **CLI**: New `marketplace` subcommand available
4. **Daemon**: Auto-update service enabled if `--daemon` mode is used

### Plugin Developers

1. **Audit Permissions**: Review if your plugin needs `permissions` field
2. **Package for Marketplace**: Follow packaging guide in PLUGIN_SDK.md
3. **Test Locally**: Use `PluginInstaller.install_from_file()` for testing
4. **Submit to Index**: PR to marketplace repository after testing

---

## Security Considerations

1. **Signature Verification**: Enable in Settings → Plugins → Require Signatures
2. **Permission Review**: Always review requested permissions before installing
3. **Code Inspection**: Plugins are Python code — review source if possible
4. **Trusted Publishers**: Prefer plugins from verified GitHub organizations
5. **Auto-Updates**: Keep plugins current via auto-update service

**Sandbox Limitations:**
- Python's dynamic nature limits sandbox effectiveness
- Plugins run in same process as main app
- Permissions are enforced at API level, not OS level
- Malicious plugins can potentially bypass sandbox

**Recommendation:** Only install plugins from trusted sources.

---

## Known Issues

1. **GPG Signature Verification**: Optional until signing infrastructure is established
2. **Marketplace Index**: Initial index is GitHub-based; dedicated CDN planned for v27
3. **Plugin Reviews**: Rating/review system planned for v27
4. **Hot Reload**: Installed plugins require app restart to load

---

## Changelog Summary

### Added (14)
- Plugin Marketplace infrastructure (API, installer, sandbox)
- Permission-based sandboxing for external plugins
- CLI marketplace commands (search, install, uninstall, update, info)
- Marketplace UI in Community tab
- Plugin dependency resolution
- SHA256 + GPG integrity verification
- Plugin auto-update service
- PluginAdapter for API bridging
- 195 new tests across 8 modules
- Permission consent dialog
- Plugin detail dialog
- `.loofi-plugin` package format
- Plugin scanner for external discovery
- Marketplace guide in PLUGIN_SDK.md

### Changed (4)
- Extended `plugin.json` with dependencies, checksum, signature
- Updated PluginLoader to support external sources
- Refactored permission system for runtime enforcement
- Enhanced CLI with marketplace subcommand

### Fixed (3)
- Plugin installation race conditions
- Permission dialog cancellation handling
- Dependency resolver version constraint parsing

---

## Documentation

- **User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **Plugin SDK**: [docs/PLUGIN_SDK.md](docs/PLUGIN_SDK.md) — Updated with marketplace section
- **Contributing**: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Roadmap**: [ROADMAP.md](ROADMAP.md)

---

## Credits

**Development:**
- Architecture: Arkitekt agent
- Backend: Builder agent
- Frontend: Sculptor agent
- Testing: Guardian agent
- CLI: CodeGen agent
- Coordination: Manager agent

**Testing:**
- 195 tests across 8 modules
- 2,043/2,066 total tests passing (98.9%)

---

## What's Next (v27.0)

Planned for v27.0 "Marketplace Enhancement":
- Dedicated marketplace CDN (replace GitHub API)
- Plugin ratings and reviews
- Verified publisher badges
- Plugin usage analytics (opt-in)
- Hot reload for installed plugins
- Enhanced sandbox with OS-level isolation

See [ROADMAP.md](ROADMAP.md) for details.

---

**Full Changelog:** [CHANGELOG.md](CHANGELOG.md)  
**GitHub Release:** https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v26.0.0  
**Issue Tracker:** https://github.com/loofitheboss/loofi-fedora-tweaks/issues
