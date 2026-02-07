"""
Loofi CLI - Command-line interface for Loofi Fedora Tweaks.
Enables headless operation and scripting.
"""

import sys
import os
import argparse
import subprocess
from typing import List, Optional

# Add parent to path for imports
sys.path.insert(0, str(__file__.rsplit("/", 2)[0]))

from utils.operations import (
    CleanupOps, TweakOps, AdvancedOps, NetworkOps, 
    OperationResult, CLI_COMMANDS
)
from utils.system import SystemManager
from utils.disk import DiskManager
from utils.monitor import SystemMonitor
from utils.plugin_base import PluginLoader


def run_operation(op_result):
    """Execute an operation tuple (cmd, args, description)."""
    cmd, args, desc = op_result
    print(f"🔄 {desc}")
    
    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print(f"✅ Success")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print(f"❌ Failed (exit code {result.returncode})")
            if result.stderr.strip():
                print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def cmd_cleanup(args):
    """Handle cleanup subcommand."""
    if args.action == "all":
        actions = ["dnf", "journal", "trim"]
    else:
        actions = [args.action]
    
    success = True
    for action in actions:
        if action == "dnf":
            success &= run_operation(CleanupOps.clean_dnf_cache())
        elif action == "journal":
            success &= run_operation(CleanupOps.vacuum_journal(args.days))
        elif action == "trim":
            success &= run_operation(CleanupOps.trim_ssd())
        elif action == "autoremove":
            success &= run_operation(CleanupOps.autoremove())
        elif action == "rpmdb":
            success &= run_operation(CleanupOps.rebuild_rpmdb())
    
    return 0 if success else 1


def cmd_tweak(args):
    """Handle tweak subcommand."""
    if args.action == "power":
        return 0 if run_operation(TweakOps.set_power_profile(args.profile)) else 1
    elif args.action == "audio":
        return 0 if run_operation(TweakOps.restart_audio()) else 1
    elif args.action == "battery":
        result = TweakOps.set_battery_limit(args.limit)
        print(f"{'✅' if result.success else '❌'} {result.message}")
        return 0 if result.success else 1
    elif args.action == "status":
        profile = TweakOps.get_power_profile()
        print(f"⚡ Power Profile: {profile}")
        print(f"💻 System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora")
        return 0
    return 1


def cmd_advanced(args):
    """Handle advanced subcommand."""
    if args.action == "dnf-tweaks":
        return 0 if run_operation(AdvancedOps.apply_dnf_tweaks()) else 1
    elif args.action == "bbr":
        return 0 if run_operation(AdvancedOps.enable_tcp_bbr()) else 1
    elif args.action == "gamemode":
        return 0 if run_operation(AdvancedOps.install_gamemode()) else 1
    elif args.action == "swappiness":
        return 0 if run_operation(AdvancedOps.set_swappiness(args.value)) else 1
    return 1


def cmd_network(args):
    """Handle network subcommand."""
    if args.action == "dns":
        result = NetworkOps.set_dns(args.provider)
        print(f"{'✅' if result.success else '❌'} {result.message}")
        return 0 if result.success else 1
    return 1


def cmd_info(args):
    """Show system information."""
    print("═══════════════════════════════════════════")
    print("   Loofi Fedora Tweaks v9.0.0 CLI")
    print("═══════════════════════════════════════════")
    print(f"🖥️  System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora")
    print(f"📦 Package Manager: {SystemManager.get_package_manager()}")
    print(f"⚡ Power Profile: {TweakOps.get_power_profile()}")
    
    if SystemManager.is_atomic():
        if SystemManager.has_pending_deployment():
            print("🔄 Pending deployment: ⚠️  Reboot required")
    
    return 0


def cmd_health(args):
    """Show system health overview."""
    print("═══════════════════════════════════════════")
    print("   System Health Check")
    print("═══════════════════════════════════════════")

    health = SystemMonitor.get_system_health()
    print(f"🖥️  Hostname: {health.hostname}")
    print(f"⏱️  Uptime: {health.uptime}")

    # Memory
    if health.memory:
        mem_icon = "🟢" if health.memory_status == "ok" else ("🟡" if health.memory_status == "warning" else "🔴")
        print(f"{mem_icon} Memory: {health.memory.used_human} / {health.memory.total_human} ({health.memory.percent_used}%)")
    else:
        print("⚪ Memory: Unable to read")

    # CPU
    if health.cpu:
        cpu_icon = "🟢" if health.cpu_status == "ok" else ("🟡" if health.cpu_status == "warning" else "🔴")
        print(f"{cpu_icon} CPU Load: {health.cpu.load_1min} / {health.cpu.load_5min} / {health.cpu.load_15min} ({health.cpu.core_count} cores, {health.cpu.load_percent}%)")
    else:
        print("⚪ CPU: Unable to read")

    # Disk
    disk_level, disk_msg = DiskManager.check_disk_health("/")
    disk_icon = "🟢" if disk_level == "ok" else ("🟡" if disk_level == "warning" else "🔴")
    print(f"{disk_icon} {disk_msg}")

    # Power profile
    print(f"⚡ Power Profile: {TweakOps.get_power_profile()}")

    # System type
    print(f"💻 System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora ({SystemManager.get_variant_name()})")

    return 0


def cmd_disk(args):
    """Show disk usage information."""
    print("═══════════════════════════════════════════")
    print("   Disk Usage")
    print("═══════════════════════════════════════════")

    # Root filesystem
    usage = DiskManager.get_disk_usage("/")
    if usage:
        level, msg = DiskManager.check_disk_health("/")
        icon = "🟢" if level == "ok" else ("🟡" if level == "warning" else "🔴")
        print(f"\n{icon} Root (/)")
        print(f"   Total: {usage.total_human}")
        print(f"   Used:  {usage.used_human} ({usage.percent_used}%)")
        print(f"   Free:  {usage.free_human}")
    else:
        print("❌ Unable to read root filesystem")

    # Home directory
    home_usage = DiskManager.get_disk_usage(os.path.expanduser("~"))
    if home_usage and home_usage.mount_point != "/":
        level, _ = DiskManager.check_disk_health(home_usage.mount_point)
        icon = "🟢" if level == "ok" else ("🟡" if level == "warning" else "🔴")
        print(f"\n{icon} Home ({home_usage.mount_point})")
        print(f"   Total: {home_usage.total_human}")
        print(f"   Used:  {home_usage.used_human} ({home_usage.percent_used}%)")
        print(f"   Free:  {home_usage.free_human}")

    # Large directories (only if --details flag)
    if getattr(args, "details", False):
        home_dir = os.path.expanduser("~")
        print(f"\n📂 Largest directories in {home_dir}:")
        large_dirs = DiskManager.find_large_directories(home_dir, max_depth=2, top_n=5)
        if large_dirs:
            for d in large_dirs:
                print(f"   {d.size_human:>10}  {d.path}")
        else:
            print("   (no results)")

    return 0


def main(argv: Optional[List[str]] = None):
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="loofi",
        description="Loofi Fedora Tweaks - System management CLI"
    )
    parser.add_argument("-v", "--version", action="version", version="9.0.0")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show system information")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="System health check overview")
    
    # Disk command
    disk_parser = subparsers.add_parser("disk", help="Disk usage information")
    disk_parser.add_argument("--details", action="store_true", help="Show large directories")
    
    # Cleanup subcommand
    cleanup_parser = subparsers.add_parser("cleanup", help="System cleanup operations")
    cleanup_parser.add_argument(
        "action",
        choices=["all", "dnf", "journal", "trim", "autoremove", "rpmdb"],
        default="all",
        nargs="?",
        help="Cleanup action to perform"
    )
    cleanup_parser.add_argument("--days", type=int, default=14, help="Days to keep journal")
    
    # Tweak subcommand
    tweak_parser = subparsers.add_parser("tweak", help="HP Elitebook tweaks")
    tweak_parser.add_argument(
        "action",
        choices=["power", "audio", "battery", "status"],
        help="Tweak action"
    )
    tweak_parser.add_argument("--profile", choices=["performance", "balanced", "power-saver"], 
                              default="balanced", help="Power profile")
    tweak_parser.add_argument("--limit", type=int, default=80, help="Battery limit (50-100)")
    
    # Advanced subcommand
    adv_parser = subparsers.add_parser("advanced", help="Advanced optimizations")
    adv_parser.add_argument(
        "action",
        choices=["dnf-tweaks", "bbr", "gamemode", "swappiness"],
        help="Optimization action"
    )
    adv_parser.add_argument("--value", type=int, default=10, help="Value for swappiness")
    
    # Network subcommand
    net_parser = subparsers.add_parser("network", help="Network configuration")
    net_parser.add_argument("action", choices=["dns"], help="Network action")
    net_parser.add_argument("--provider", choices=["cloudflare", "google", "quad9", "opendns"],
                           default="cloudflare", help="DNS provider")
    
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "info":
        return cmd_info(args)
    elif args.command == "health":
        return cmd_health(args)
    elif args.command == "disk":
        return cmd_disk(args)
    elif args.command == "cleanup":
        return cmd_cleanup(args)
    elif args.command == "tweak":
        return cmd_tweak(args)
    elif args.command == "advanced":
        return cmd_advanced(args)
    elif args.command == "network":
        return cmd_network(args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
