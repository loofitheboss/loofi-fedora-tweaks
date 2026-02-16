#!/bin/bash
# Loofi Fedora Tweaks - Easy Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
#
# ⚠️  DEPRECATED: This installation method is not recommended.
# Preferred methods: RPM/Copr repository or Flatpak.
# See README.md for recommended installation instructions.

set -e

# ─── Deprecation Warning ───────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  WARNING: curl-pipe-bash installation is DEPRECATED     ║"
echo "║                                                            ║"
echo "║  This method downloads and runs code without verification. ║"
echo "║  It is kept for backward compatibility but NOT recommended.║"
echo "║                                                            ║"
echo "║  Recommended installation method:                            ║"
echo "║    • sudo dnf copr enable loofitheboss/loofi-fedora-tweaks ║"
echo "║    • sudo dnf install loofi-fedora-tweaks                  ║"
echo "║                                                            ║"
echo "║  To proceed anyway, re-run with:                           ║"
echo "║    bash install.sh --i-know-what-i-am-doing                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [[ "$1" != "--i-know-what-i-am-doing" ]]; then
    echo "❌ Aborting. Use --i-know-what-i-am-doing flag to proceed."
    exit 1
fi
# ─── End Deprecation Warning ───────────────────────────────────────

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
