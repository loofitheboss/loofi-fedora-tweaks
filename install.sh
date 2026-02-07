#!/bin/bash
# Loofi Fedora Tweaks - Easy Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash

set -e

echo "🚀 Installing Loofi Fedora Tweaks..."

# Add repository
echo "📦 Adding repository..."
sudo dnf config-manager --add-repo https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/loofi-fedora-tweaks.repo

# Install package
echo "⬇️ Installing package..."
sudo dnf install -y loofi-fedora-tweaks --refresh

echo ""
echo "✅ Installation complete!"
echo "🎉 Run 'loofi-fedora-tweaks' or find it in your app menu."
