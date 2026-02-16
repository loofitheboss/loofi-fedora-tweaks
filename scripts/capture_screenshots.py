#!/usr/bin/env python3
"""
Screenshot Capture Assistant for Loofi Fedora Tweaks
Helps automate and guide the screenshot capture process for documentation.

Usage:
    python scripts/capture_screenshots.py [--auto]
    
Options:
    --auto    Attempt to automatically navigate and capture screenshots
              (requires running GUI instance)
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional

# Screenshot specifications
SCREENSHOTS = [
    {
        "filename": "home-dashboard.png",
        "tab_path": "Overview > Home",
        "description": "Show health score, quick actions, system summary",
        "priority": 1,
        "notes": "Ensure health metrics are visible, quick action buttons are clear"
    },
    {
        "filename": "system-monitor.png",
        "tab_path": "Overview > System Monitor",
        "description": "Show CPU/RAM/process data with active processes",
        "priority": 1,
        "notes": "Capture with some processes running to show real data"
    },
    {
        "filename": "maintenance-updates.png",
        "tab_path": "Manage > Maintenance",
        "description": "Show update workflow and cleanup options",
        "priority": 1,
        "notes": "Navigate to Updates sub-tab, show available updates if possible"
    },
    {
        "filename": "network-overview.png",
        "tab_path": "Network & Security > Network",
        "description": "Show connections view with active connection",
        "priority": 2,
        "notes": "Ensure at least one network connection is visible"
    },
    {
        "filename": "security-privacy.png",
        "tab_path": "Network & Security > Security & Privacy",
        "description": "Show security score and firewall status",
        "priority": 1,
        "notes": "Show security score prominently, firewall status clear"
    },
    {
        "filename": "ai-lab-models.png",
        "tab_path": "Developer > AI Lab",
        "description": "Show models list and AI features",
        "priority": 2,
        "notes": "Show Ollama integration, model list if available"
    },
    {
        "filename": "community-presets.png",
        "tab_path": "Automation > Community",
        "description": "Show presets tab with available presets",
        "priority": 2,
        "notes": "Navigate to Presets sub-tab within Community"
    },
    {
        "filename": "community-marketplace.png",
        "tab_path": "Automation > Community",
        "description": "Show marketplace tab with plugins",
        "priority": 2,
        "notes": "Navigate to Marketplace sub-tab within Community"
    },
    {
        "filename": "settings-appearance.png",
        "tab_path": "Personalize > Settings",
        "description": "Show appearance options and theme settings",
        "priority": 2,
        "notes": "Navigate to Appearance sub-tab, show theme options"
    }
]

# Additional screenshots to consider for v41+
ADDITIONAL_SCREENSHOTS = [
    {
        "filename": "extensions-tab.png",
        "tab_path": "Manage > Extensions",
        "description": "Show extensions management (new in v37)",
        "priority": 3,
        "notes": "New tab added in v37"
    },
    {
        "filename": "backup-tab.png",
        "tab_path": "Manage > Backup",
        "description": "Show backup features (new in v37)",
        "priority": 3,
        "notes": "New tab added in v37"
    },
    {
        "filename": "diagnostics-tab.png",
        "tab_path": "Developer > Diagnostics",
        "description": "Show system diagnostics tools",
        "priority": 3,
        "notes": "Show diagnostic checks and results"
    },
    {
        "filename": "agents-tab.png",
        "tab_path": "Automation > Agents",
        "description": "Show local agent dashboard",
        "priority": 3,
        "notes": "Show agent controls and status"
    }
]


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_instructions() -> None:
    """Print manual screenshot capture instructions."""
    print_header("Loofi Fedora Tweaks Screenshot Capture Guide")
    
    print("📸 PREPARATION:")
    print("  1. Launch the application:")
    print("     ./run.sh")
    print("     OR: PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py")
    print()
    print("  2. Set consistent window size:")
    print("     - Recommended: 1280x800 or 1440x900")
    print("     - Ensure window is not maximized (for consistent sizing)")
    print()
    print("  3. Use the default dark theme:")
    print("     - Abyss Dark (modern.qss)")
    print("     - Check Settings > Appearance if needed")
    print()
    print("  4. Screenshot tool ready:")
    print("     - GNOME: Press PrtSc or use Screenshot tool")
    print("     - KDE: Spectacle (spectacle -r)")
    print("     - CLI: scrot, flameshot, or import (ImageMagick)")
    print()
    
    print_header("REQUIRED SCREENSHOTS (Priority 1-2)")
    
    for i, shot in enumerate(SCREENSHOTS, 1):
        print(f"{i}. {shot['filename']}")
        print(f"   📍 Navigate to: {shot['tab_path']}")
        print(f"   📝 Capture: {shot['description']}")
        print(f"   ⚠️  Notes: {shot['notes']}")
        print(f"   💾 Save to: docs/images/user-guide/{shot['filename']}")
        print()
    
    print_header("OPTIONAL SCREENSHOTS (Priority 3)")
    
    for i, shot in enumerate(ADDITIONAL_SCREENSHOTS, 1):
        print(f"{i}. {shot['filename']}")
        print(f"   📍 Navigate to: {shot['tab_path']}")
        print(f"   📝 Capture: {shot['description']}")
        print(f"   💾 Save to: docs/images/user-guide/{shot['filename']}")
        print()
    
    print_header("POST-PROCESSING")
    
    print("📐 Image Optimization:")
    print("  cd docs/images/user-guide/")
    print("  optipng -o5 *.png")
    print("  OR: pngcrush -brute *.png")
    print()
    print("📏 Verify Image Sizes:")
    print("  - All screenshots should be similar dimensions")
    print("  - File size should be under 200KB after optimization")
    print("  - Check: ls -lh *.png")
    print()
    print("✅ Verification:")
    print("  - Preview in markdown: grip README.md")
    print("  - Check all docs render correctly:")
    print("    - docs/USER_GUIDE.md")
    print("    - docs/BEGINNER_QUICK_GUIDE.md")
    print("    - docs/ADVANCED_ADMIN_GUIDE.md")
    print("    - README.md")
    print()
    
    print_header("CLEANUP")
    
    print("🗑️  Remove outdated screenshots (if superseded):")
    print("  - docs/boot_tab.png (check if still referenced)")
    print("  - docs/dashboard.png (likely superseded by home-dashboard.png)")
    print("  - docs/marketplace.png (likely superseded by community-marketplace.png)")
    print()


def check_existing_screenshots() -> None:
    """Check which screenshots already exist."""
    print_header("Existing Screenshot Status")
    
    screenshot_dir = Path("docs/images/user-guide")
    
    if not screenshot_dir.exists():
        print(f"❌ Screenshot directory not found: {screenshot_dir}")
        return
    
    print("📊 Current Status:\n")
    
    for shot in SCREENSHOTS:
        filepath = screenshot_dir / shot["filename"]
        if filepath.exists():
            size = filepath.stat().st_size / 1024  # KB
            mtime = time.strftime('%Y-%m-%d', time.localtime(filepath.stat().st_mtime))
            status = f"✅ EXISTS ({size:.1f}KB, modified {mtime})"
        else:
            status = "❌ MISSING"
        
        print(f"  {shot['filename']:<35} {status}")
        print(f"    → {shot['tab_path']}")
        print()


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print("⚠️  Automated screenshot capture is not yet implemented.")
        print("    This would require PyAutoGUI or similar automation tools.")
        print("    For now, please use manual capture mode.\n")
        sys.exit(1)
    
    check_existing_screenshots()
    print_instructions()
    
    print_header("Next Steps")
    print("1. Follow the preparation steps above")
    print("2. Navigate to each tab and capture screenshots")
    print("3. Save with the exact filenames specified")
    print("4. Run optimization: optipng -o5 docs/images/user-guide/*.png")
    print("5. Verify docs render correctly")
    print("6. Commit changes with: 'Update screenshots to v41.0.0'")
    print()


if __name__ == "__main__":
    main()
