"""
v26.0 Phase 1 Usage Examples — Plugin System Components

This file demonstrates Phase 1 tasks (T1-T4):
- T1: PluginAdapter for legacy plugins
- T2: PluginPackage & PluginManifest
- T3: PluginSandbox for permissions
- T4: PluginScanner & PluginLoader for external plugins
"""

# Example 1: Using PluginAdapter to register legacy plugins
def example_adapter_usage():
    """Wrap a legacy LoofiPlugin and register it in PluginRegistry."""
    from utils.plugin_base import LoofiPlugin, PluginInfo
    from core.plugins import PluginAdapter, PluginRegistry
    from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
    
    # Legacy plugin (v13.0 style)
    class MyLegacyPlugin(LoofiPlugin):
        @property
        def info(self) -> PluginInfo:
            return PluginInfo(
                name="Legacy Plugin",
                version="1.0.0",
                author="Community Author",
                description="Example legacy plugin",
                icon="🔧"
            )
        
        def create_widget(self) -> QWidget:
            widget = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Hello from legacy plugin!"))
            widget.setLayout(layout)
            return widget
        
        def get_cli_commands(self) -> dict:
            return {"legacy-cmd": lambda: print("Legacy command")}
    
    # Wrap with adapter
    legacy = MyLegacyPlugin()
    adapter = PluginAdapter(legacy)
    
    # Register in unified registry (works seamlessly!)
    registry = PluginRegistry.instance()
    registry.register(adapter)
    
    # Now it appears alongside built-in tabs
    print(f"Registered: {adapter.metadata().name}")
    print(f"Category: {adapter.metadata().category}")  # "Community"
    print(f"Badge: {adapter.metadata().badge}")        # "community"
    print(f"Order: {adapter.metadata().order}")        # 500


# Example 2: Creating a .loofi-plugin package
def example_package_creation():
    """Build a .loofi-plugin archive from scratch (for plugin authors)."""
    from core.plugins import PluginManifest, PluginPackage
    
    # Define manifest
    manifest = PluginManifest(
        id="my-awesome-plugin",
        name="My Awesome Plugin",
        version="1.0.0",
        description="Does something amazing",
        author="John Doe",
        author_email="john@example.com",
        license="MIT",
        homepage="https://github.com/user/plugin",
        permissions=["network", "notifications"],
        requires=["core-utils>=1.0"],
        min_app_version="25.0.0",
        icon="🚀",
    )
    
    # Plugin code
    plugin_code = '''
from utils.plugin_base import LoofiPlugin, PluginInfo
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class MyAwesomePlugin(LoofiPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="My Awesome Plugin",
            version="1.0.0",
            author="John Doe",
            description="Does something amazing",
            icon="🚀"
        )
    
    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("🚀 Awesome features here!"))
        widget.setLayout(layout)
        return widget
    
    def get_cli_commands(self) -> dict:
        return {"awesome": self.do_awesome}
    
    def do_awesome(self):
        print("Doing awesome things...")

# Entry point
plugin = MyAwesomePlugin()
'''
    
    # Create package
    package = PluginPackage.create(
        manifest=manifest,
        plugin_code=plugin_code,
        assets={
            "icon.png": b"PNG_ICON_BYTES_HERE",  # Example asset
        }
    )
    
    # Save to file
    package.save("my-awesome-plugin-1.0.0.loofi-plugin")
    print(f"Created: my-awesome-plugin-1.0.0.loofi-plugin")


# Example 3: Loading and verifying a .loofi-plugin package
def example_package_loading():
    """Load an external plugin from a .loofi-plugin archive."""
    from core.plugins import PluginPackage, PluginAdapter, PluginRegistry
    from pathlib import Path
    import importlib.util
    import sys
    
    # Load package
    package = PluginPackage.from_file("my-awesome-plugin-1.0.0.loofi-plugin")
    
    # Verify integrity (checksums)
    if not package.verify():
        print("❌ Package verification failed!")
        return
    
    print(f"✓ Loaded: {package.manifest.name} v{package.manifest.version}")
    print(f"  Author: {package.manifest.author}")
    print(f"  Permissions: {', '.join(package.manifest.permissions)}")
    
    # Extract plugin code to temp location
    temp_dir = Path("/tmp/loofi-plugins") / package.manifest.id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    plugin_file = temp_dir / package.manifest.entry_point
    plugin_file.write_bytes(package.files[package.manifest.entry_point])
    
    # Dynamically load plugin module
    spec = importlib.util.spec_from_file_location(
        f"plugins.{package.manifest.id}",
        plugin_file
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    
    # Instantiate plugin (assumes module has 'plugin' variable)
    legacy_plugin = module.plugin
    
    # Wrap with adapter
    adapter = PluginAdapter(legacy_plugin)
    
    # Inject manifest so adapter can check min_app_version
    adapter.wrapped_plugin.manifest = package.manifest
    
    # Register
    registry = PluginRegistry.instance()
    registry.register(adapter)
    
    print(f"✓ Registered {package.manifest.name} in unified registry")


# Example 4: Compatibility checking with adapter
def example_compat_checking():
    """Check if an external plugin is compatible with current system."""
    from core.plugins import PluginAdapter, CompatibilityDetector
    from utils.plugin_base import LoofiPlugin, PluginInfo
    from PyQt6.QtWidgets import QWidget
    
    class OldPlugin(LoofiPlugin):
        @property
        def info(self) -> PluginInfo:
            return PluginInfo(
                name="Old Plugin",
                version="0.5.0",
                author="Legacy Dev",
                description="Built for old version",
            )
        
        def create_widget(self) -> QWidget:
            return QWidget()
        
        def get_cli_commands(self) -> dict:
            return {}
    
    # Create plugin with manifest requiring newer version
    from core.plugins.package import PluginManifest
    plugin = OldPlugin()
    plugin.manifest = PluginManifest(
        id="old-plugin",
        name="Old Plugin",
        version="0.5.0",
        description="Built for old version",
        author="Legacy Dev",
        min_app_version="30.0.0",  # Requires future version!
    )
    
    # Wrap and check compat
    adapter = PluginAdapter(plugin)
    detector = CompatibilityDetector()
    compat = adapter.check_compat(detector)
    
    if not compat.compatible:
        print(f"❌ Incompatible: {compat.reason}")
    else:
        print("✓ Compatible!")
        if compat.warnings:
            print(f"⚠️  Warnings: {', '.join(compat.warnings)}")


# Example 5: Full workflow — Create, Save, Load, Register
def example_full_workflow():
    """Complete workflow from package creation to registration."""
    from core.plugins import PluginManifest, PluginPackage
    
    # 1. Plugin author creates package
    manifest = PluginManifest(
        id="demo-plugin",
        name="Demo Plugin",
        version="2.0.0",
        description="Demonstration plugin",
        author="Demo Author",
        permissions=["filesystem"],
    )
    
    plugin_code = '''
from utils.plugin_base import LoofiPlugin, PluginInfo
from PyQt6.QtWidgets import QWidget, QPushButton

class DemoPlugin(LoofiPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="Demo Plugin", version="2.0.0",
            author="Demo Author", description="Demonstration plugin"
        )
    
    def create_widget(self) -> QWidget:
        return QPushButton("Click Me!")
    
    def get_cli_commands(self) -> dict:
        return {}

plugin = DemoPlugin()
'''
    
    package = PluginPackage.create(manifest, plugin_code)
    package.save("demo-plugin-2.0.0.loofi-plugin")
    print("✓ Package created and saved")
    
    # 2. User downloads and installs
    loaded = PluginPackage.from_file("demo-plugin-2.0.0.loofi-plugin")
    assert loaded.verify(), "Verification failed!"
    print("✓ Package loaded and verified")
    
    # 3. System registers plugin (automated via PluginLoader in v26.0 T3+)
    print(f"✓ Ready to register: {loaded.manifest.name}")


# Example 6: PluginScanner - Discover external plugins (T4)
def example_scanner_usage():
    """Use PluginScanner to discover plugins in user directory."""
    from core.plugins import PluginScanner
    from pathlib import Path
    
    # Initialize scanner (default: ~/.config/loofi-fedora-tweaks/plugins/)
    scanner = PluginScanner()
    
    print(f"Scanning: {scanner.plugins_dir}")
    
    # Scan for plugins
    discovered = scanner.scan()
    
    print(f"Found {len(discovered)} plugin(s):")
    for plugin_path, manifest in discovered:
        print(f"\n  📦 {manifest.name}")
        print(f"     ID: {manifest.id}")
        print(f"     Version: {manifest.version}")
        print(f"     Author: {manifest.author}")
        print(f"     Permissions: {', '.join(manifest.permissions)}")
        print(f"     Entry: {manifest.entry_point}")
        
        if manifest.min_app_version:
            print(f"     Min App: {manifest.min_app_version}")


# Example 7: PluginLoader - Load external plugins (T4)
def example_loader_usage():
    """Use PluginLoader to load external plugins into registry."""
    from core.plugins import PluginLoader, PluginRegistry
    
    # Initialize loader and registry
    registry = PluginRegistry.instance()
    loader = PluginLoader(registry=registry)
    
    # Prepare context for plugins
    context = {
        "main_window": None,      # MainWindow instance
        "config_manager": None,   # ConfigManager instance
        "executor": None,         # CommandExecutor instance
    }
    
    # Load built-in plugins first
    builtin_ids = loader.load_builtins(context)
    print(f"Loaded {len(builtin_ids)} built-in plugins")
    
    # Load external plugins from user directory
    external_ids = loader.load_external(context)
    print(f"Loaded {len(external_ids)} external plugin(s)")
    
    # Access loaded plugins
    for plugin_id in external_ids:
        plugin = registry.get_by_id(plugin_id)
        if plugin:
            metadata = plugin.metadata()
            print(f"  ✓ {metadata.name} (category: {metadata.category})")


# Example 8: Creating plugin directory structure (T4)
def example_create_plugin_directory():
    """Show how to manually create a plugin in user directory."""
    import json
    from pathlib import Path
    
    # Plugin directory
    base = Path.home() / ".config" / "loofi-fedora-tweaks" / "plugins"
    plugin_dir = base / "my-custom-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    # Create plugin.json
    manifest = {
        "id": "my-custom-plugin",
        "name": "My Custom Plugin",
        "version": "1.0.0",
        "description": "A custom plugin for Loofi",
        "author": "Your Name",
        "permissions": ["network", "filesystem"],
        "min_app_version": "25.0.0",
        "entry_point": "plugin.py",
        "icon": "🎨",
        "category": "Customization"
    }
    
    manifest_path = plugin_dir / "plugin.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"✓ Created: {manifest_path}")
    
    # Create plugin.py
    plugin_code = '''
from utils.plugin_base import LoofiPlugin, PluginInfo
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class MyCustomPlugin(LoofiPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="My Custom Plugin",
            version="1.0.0",
            author="Your Name",
            description="A custom plugin for Loofi",
            icon="🎨"
        )
    
    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("🎨 My Custom Plugin Widget"))
        widget.setLayout(layout)
        return widget
    
    def get_cli_commands(self) -> dict:
        return {"custom-cmd": self.run_custom}
    
    def run_custom(self):
        print("Running custom command...")
'''
    
    plugin_path = plugin_dir / "plugin.py"
    plugin_path.write_text(plugin_code)
    print(f"✓ Created: {plugin_path}")
    
    print(f"\n✓ Plugin created at: {plugin_dir}")
    print("  Restart Loofi to load the plugin!")


# Example 9: Full integration in MainWindow (T4)
def example_mainwindow_integration():
    """Show how MainWindow integrates scanner and loader."""
    from core.plugins import PluginLoader, PluginRegistry
    
    # In MainWindow.__init__():
    print("=== MainWindow Plugin Integration ===\n")
    
    # 1. Initialize registry and loader
    registry = PluginRegistry.instance()
    loader = PluginLoader(registry=registry)
    
    # 2. Prepare context
    context = {
        "main_window": None,      # self (MainWindow instance)
        "config_manager": None,   # self.config_manager
        "executor": None,         # self.executor
    }
    
    # 3. Load built-in plugins (26 tabs)
    print("Loading built-in plugins...")
    builtin_ids = loader.load_builtins(context)
    print(f"✓ Loaded {len(builtin_ids)} built-in plugins\n")
    
    # 4. Load external plugins
    print("Loading external plugins...")
    external_ids = loader.load_external(context)
    print(f"✓ Loaded {len(external_ids)} external plugin(s)")
    
    # 5. External plugins appear in sidebar with "community" badge
    all_plugins = registry.get_all()
    community_plugins = [p for p in all_plugins if p.metadata().badge == "community"]
    
    print(f"\n📦 Community Plugins ({len(community_plugins)}):")
    for plugin in community_plugins:
        meta = plugin.metadata()
        print(f"   {meta.icon} {meta.name} (v{meta.version})")


if __name__ == "__main__":
    print("=== v26.0 Plugin System Examples ===\n")
    
    # Run examples (comment out as needed)
    # example_adapter_usage()
    # example_package_creation()
    # example_package_loading()
    # example_compat_checking()
    # example_full_workflow()
    
    # T4 Examples (Scanner & Loader)
    example_scanner_usage()
    # example_loader_usage()
    # example_create_plugin_directory()
    # example_mainwindow_integration()
