#!/usr/bin/env bash
# create_plugin.sh — v31.0 Smart UX
# Scaffold a new Loofi Fedora Tweaks plugin directory.
#
# Usage: ./scripts/create_plugin.sh <plugin-name>
# Example: ./scripts/create_plugin.sh my-awesome-plugin
#
# Creates:
#   plugins/<plugin-name>/
#   ├── plugin.py
#   ├── metadata.json
#   ├── README.md
#   └── tests/
#       └── test_plugin.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGINS_DIR="$PROJECT_ROOT/plugins"

usage() {
    echo "Usage: $0 <plugin-name>"
    echo ""
    echo "Creates a new plugin scaffold under plugins/<plugin-name>/"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 system-cleaner"
    exit 0
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
fi

if [[ $# -lt 1 ]]; then
    echo "Error: Plugin name required."
    echo ""
    usage
fi

PLUGIN_NAME="$1"
PLUGIN_DIR="$PLUGINS_DIR/$PLUGIN_NAME"

# Convert kebab-case to PascalCase for class name
PLUGIN_CLASS=$(echo "$PLUGIN_NAME" | sed -r 's/(^|-)(\w)/\U\2/g')

# Convert kebab-case to snake_case for module name
PLUGIN_MODULE=$(echo "$PLUGIN_NAME" | tr '-' '_')

if [[ -d "$PLUGIN_DIR" ]]; then
    echo "Error: Plugin directory already exists: $PLUGIN_DIR"
    exit 1
fi

echo "Creating plugin scaffold: $PLUGIN_NAME"
echo "  Directory: $PLUGIN_DIR"
echo "  Class: ${PLUGIN_CLASS}Plugin"
echo ""

# Create directory structure
mkdir -p "$PLUGIN_DIR/tests"

# plugin.py
cat > "$PLUGIN_DIR/plugin.py" << PYEOF
"""
${PLUGIN_CLASS} Plugin for Loofi Fedora Tweaks.

Extends LoofiPlugin to provide custom functionality.
"""

from utils.plugin_base import LoofiPlugin


class ${PLUGIN_CLASS}Plugin(LoofiPlugin):
    """${PLUGIN_CLASS} plugin implementation."""

    @property
    def name(self) -> str:
        return "${PLUGIN_NAME}"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "A ${PLUGIN_CLASS} plugin for Loofi Fedora Tweaks."

    def activate(self) -> None:
        """Called when the plugin is activated."""
        pass

    def deactivate(self) -> None:
        """Called when the plugin is deactivated."""
        pass
PYEOF

# metadata.json
cat > "$PLUGIN_DIR/metadata.json" << JSONEOF
{
    "id": "${PLUGIN_MODULE}",
    "name": "${PLUGIN_CLASS}",
    "version": "1.0.0",
    "description": "A ${PLUGIN_CLASS} plugin for Loofi Fedora Tweaks.",
    "author": "",
    "license": "MIT",
    "min_app_version": "31.0.0",
    "permissions": [],
    "entry_point": "plugin.py",
    "category": "General"
}
JSONEOF

# README.md
cat > "$PLUGIN_DIR/README.md" << MDEOF
# ${PLUGIN_CLASS} Plugin

A plugin for Loofi Fedora Tweaks.

## Installation

Copy this directory to \`~/.config/loofi-fedora-tweaks/plugins/${PLUGIN_NAME}/\`

## Development

\`\`\`bash
# Run tests
PYTHONPATH=loofi-fedora-tweaks python -m pytest ${PLUGIN_DIR}/tests/ -v
\`\`\`

## License

MIT
MDEOF

# tests/test_plugin.py
cat > "$PLUGIN_DIR/tests/test_plugin.py" << TESTEOF
"""Tests for ${PLUGIN_CLASS} plugin."""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'loofi-fedora-tweaks'))


class Test${PLUGIN_CLASS}Plugin(unittest.TestCase):
    """Tests for ${PLUGIN_CLASS}Plugin."""

    def test_plugin_can_be_imported(self):
        """Plugin module can be imported."""
        # This is a basic smoke test
        self.assertTrue(True)

    def test_plugin_has_name(self):
        """Plugin has a name property."""
        # TODO: Import and instantiate the plugin
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
TESTEOF

echo "✅ Plugin scaffold created successfully!"
echo ""
echo "Next steps:"
echo "  1. Edit $PLUGIN_DIR/plugin.py to add your logic"
echo "  2. Update $PLUGIN_DIR/metadata.json with your details"
echo "  3. Run tests: PYTHONPATH=loofi-fedora-tweaks python -m pytest $PLUGIN_DIR/tests/ -v"
