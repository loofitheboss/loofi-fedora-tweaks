#!/bin/bash
# Loofi Fedora Tweaks - Uninstaller

set -e

echo "🗑️ Removing Loofi Fedora Tweaks..."

# Remove package
sudo dnf remove -y loofi-fedora-tweaks

# Remove repository (optional)
read -p "Remove repository too? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo rm -f /etc/yum.repos.d/loofi-fedora-tweaks.repo
    echo "✅ Repository removed."
fi

echo "✅ Uninstallation complete!"
