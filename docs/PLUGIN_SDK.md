# Plugin SDK (Draft)

This document defines the minimal plugin contract for Loofi Fedora Tweaks.

## Directory Layout

```
plugins/
  my_plugin/
    plugin.json
    plugin.py
```

## `plugin.json`

```json
{
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "You",
  "description": "What the plugin does.",
  "entry": "plugin.py",
  "min_app_version": "12.0.0",
  "permissions": ["network", "system"],
  "icon": "🔌"
}
```

## Python Entry (`plugin.py`)

```python
from utils.plugin_base import LoofiPlugin, PluginInfo

class MyPlugin(LoofiPlugin):
    @property
    def info(self):
        return PluginInfo(
            name="My Plugin",
            version="1.0.0",
            author="You",
            description="What the plugin does.",
            icon="🔌",
        )

    def create_widget(self):
        # Return a QWidget instance
        from PyQt6.QtWidgets import QWidget
        return QWidget()

    def get_cli_commands(self):
        return {}
```

## CLI Management

```
loofi plugins list
loofi plugins enable my_plugin
loofi plugins disable my_plugin
```
