"""
Plugin Base - Abstract base class for Loofi plugins.
Enables modular, third-party feature extensions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Type, Any
from pathlib import Path
import importlib.util
import os


@dataclass
class PluginInfo:
    """Plugin metadata."""
    name: str
    version: str
    author: str
    description: str
    icon: str = "🔌"


class LoofiPlugin(ABC):
    """
    Abstract base class for Loofi Fedora Tweaks plugins.
    
    Plugins must implement:
    - info: Plugin metadata
    - create_widget(): Return a QWidget for the tab
    - get_cli_commands(): Return dict of CLI commands
    """
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        pass
    
    @abstractmethod
    def create_widget(self) -> Any:  # Returns QWidget but avoiding import
        """
        Create and return the plugin's main widget.
        This will be added as a tab in the main window.
        """
        pass
    
    @abstractmethod
    def get_cli_commands(self) -> Dict[str, callable]:
        """
        Return dictionary of CLI commands this plugin provides.
        
        Example:
            {"my-command": self.run_my_command}
        """
        pass
    
    def on_load(self) -> None:
        """Called when plugin is loaded. Override for initialization."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unloaded. Override for cleanup."""
        pass


class PluginLoader:
    """
    Loads plugins from the plugins directory.
    
    Plugin structure:
        plugins/
            my_plugin/
                __init__.py  # Contains class inheriting LoofiPlugin
                plugin.py    # Alternative location
    """
    
    PLUGINS_DIR = Path(__file__).parent.parent / "plugins"
    
    def __init__(self):
        self.plugins: Dict[str, LoofiPlugin] = {}
        self._ensure_plugins_dir()
    
    def _ensure_plugins_dir(self):
        """Create plugins directory if it doesn't exist."""
        self.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py if missing
        init_file = self.PLUGINS_DIR / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Loofi plugins directory\n")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugins directory.
        
        Returns:
            List of plugin directory names.
        """
        plugins = []
        
        if not self.PLUGINS_DIR.exists():
            return plugins
        
        for item in self.PLUGINS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                # Check for plugin.py or __init__.py with LoofiPlugin subclass
                if (item / "plugin.py").exists() or (item / "__init__.py").exists():
                    plugins.append(item.name)
        
        return plugins
    
    def load_plugin(self, plugin_name: str) -> Optional[LoofiPlugin]:
        """
        Load a single plugin by name.
        
        Args:
            plugin_name: Name of the plugin directory.
            
        Returns:
            LoofiPlugin instance or None if loading fails.
        """
        plugin_dir = self.PLUGINS_DIR / plugin_name
        
        if not plugin_dir.exists():
            return None
        
        # Try plugin.py first, then __init__.py
        plugin_file = plugin_dir / "plugin.py"
        if not plugin_file.exists():
            plugin_file = plugin_dir / "__init__.py"
        
        if not plugin_file.exists():
            return None
        
        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}", 
                plugin_file
            )
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find LoofiPlugin subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, LoofiPlugin) and 
                    attr is not LoofiPlugin):
                    
                    # Instantiate plugin
                    plugin = attr()
                    plugin.on_load()
                    self.plugins[plugin_name] = plugin
                    return plugin
            
        except Exception as e:
            print(f"Failed to load plugin {plugin_name}: {e}")
        
        return None
    
    def load_all_plugins(self) -> Dict[str, LoofiPlugin]:
        """
        Load all discovered plugins.
        
        Returns:
            Dictionary of plugin_name -> LoofiPlugin instance.
        """
        for plugin_name in self.discover_plugins():
            self.load_plugin(plugin_name)
        
        return self.plugins
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to unload.
            
        Returns:
            True if successfully unloaded.
        """
        if plugin_name in self.plugins:
            try:
                self.plugins[plugin_name].on_unload()
                del self.plugins[plugin_name]
                return True
            except Exception:
                pass
        return False
    
    def get_all_cli_commands(self) -> Dict[str, callable]:
        """
        Get CLI commands from all loaded plugins.
        
        Returns:
            Merged dictionary of all plugin CLI commands.
        """
        commands = {}
        for plugin in self.plugins.values():
            commands.update(plugin.get_cli_commands())
        return commands
