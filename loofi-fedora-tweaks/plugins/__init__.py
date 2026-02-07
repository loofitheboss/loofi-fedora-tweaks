# Loofi plugins directory
# Place plugin folders here to extend functionality.
#
# Plugin structure:
#   plugins/
#     my_plugin/
#       plugin.py  # Must contain a class inheriting LoofiPlugin
#
# Example plugin:
#   from utils.plugin_base import LoofiPlugin, PluginInfo
#
#   class MyPlugin(LoofiPlugin):
#       @property
#       def info(self):
#           return PluginInfo(name="My Plugin", version="1.0", ...)
#
#       def create_widget(self):
#           return MyWidget()
#
#       def get_cli_commands(self):
#           return {"my-cmd": self.my_command}
