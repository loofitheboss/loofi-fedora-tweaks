"""
Loofi CLI - Command-line interface for Loofi Fedora Tweaks.
Enables headless operation and scripting.
v18.0.0 "Sentinel"
"""

import argparse
import json as json_module
import os
import shutil
import subprocess
import sys
from typing import List, Optional

from services.hardware import BluetoothManager
from services.hardware import DiskManager
from utils.firewall_manager import FirewallManager
from utils.focus_mode import FocusMode
from utils.health_timeline import HealthTimeline
from utils.journal import JournalManager
from utils.monitor import SystemMonitor
from utils.network_monitor import NetworkMonitor
from utils.operations import AdvancedOps, CleanupOps, NetworkOps, TweakOps
from utils.package_explorer import PackageExplorer
from utils.plugin_base import PluginLoader
from utils.plugin_installer import PluginInstaller
from utils.plugin_marketplace import PluginMarketplace
from utils.ports import PortAuditor
from utils.presets import PresetManager
from services.system import ProcessManager
from utils.profiles import ProfileManager
from utils.service_explorer import ServiceExplorer, ServiceScope
from utils.storage import StorageManager
from services.system import SystemManager
from services.hardware import TemperatureManager
from utils.update_checker import UpdateChecker
from version import __version__, __version_codename__

# Add parent to path for imports
sys.path.insert(0, str(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# Global flag for JSON output
_json_output = False

# Global operation timeout (default 300s, configurable via --timeout)
_operation_timeout = 300

# Global dry-run flag (v35.0 Fortress)
_dry_run = False


def _print(text):
    """Print text (suppressed in JSON mode)."""
    if not _json_output:
        print(text)


def _output_json(data):
    """Output JSON data and exit."""
    print(json_module.dumps(data, indent=2, default=str))


def run_operation(op_result, timeout=None):
    """Execute an operation tuple (cmd, args, description).

    Args:
        op_result: Tuple of (cmd, args, description) from utils operations.
        timeout: Override timeout in seconds. Defaults to global _operation_timeout (300s).
    """
    cmd, args, desc = op_result
    full_cmd = [cmd] + args

    # Dry-run mode: show command without executing, audit-log it
    if _dry_run:
        _print(f"🔍 [DRY-RUN] Would execute: {' '.join(full_cmd)}")
        _print(f"   Description: {desc}")
        try:
            from utils.audit import AuditLogger
            AuditLogger().log(
                action=f"cli.{cmd}",
                params={"cmd": full_cmd, "description": desc},
                exit_code=None,
                dry_run=True,
            )
        except Exception:
            pass
        if _json_output:
            _output_json(
                {"dry_run": True, "command": full_cmd, "description": desc})
        return True

    _print(f"🔄 {desc}")

    op_timeout = timeout if timeout is not None else _operation_timeout

    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True, text=True, check=False,
            timeout=op_timeout,
        )
        if result.returncode == 0:
            _print("✅ Success")
            if result.stdout.strip():
                _print(result.stdout)
        else:
            _print(f"❌ Failed (exit code {result.returncode})")
            if result.stderr.strip():
                _print(result.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        _print(f"❌ Timed out after {op_timeout}s")
        return False
    except Exception as e:
        _print(f"❌ Error: {e}")
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
        _print(f"{'✅' if result.success else '❌'} {result.message}")
        return 0 if result.success else 1
    elif args.action == "status":
        profile = TweakOps.get_power_profile()
        if _json_output:
            _output_json({
                "power_profile": profile,
                "system_type": "Atomic" if SystemManager.is_atomic() else "Traditional",
            })
        else:
            _print(f"⚡ Power Profile: {profile}")
            _print(
                f"💻 System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora")
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
        _print(f"{'✅' if result.success else '❌'} {result.message}")
        return 0 if result.success else 1
    return 1


def cmd_info(args):
    """Show system information."""
    is_atomic = SystemManager.is_atomic()
    pm = SystemManager.get_package_manager()
    profile = TweakOps.get_power_profile()

    if _json_output:
        data = {
            "version": __version__,
            "codename": __version_codename__,
            "system_type": "Atomic" if is_atomic else "Traditional",
            "package_manager": pm,
            "power_profile": profile,
        }
        if is_atomic and SystemManager.has_pending_deployment():
            data["pending_deployment"] = True
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print(f"   Loofi Fedora Tweaks v{__version__} CLI")
        _print("═══════════════════════════════════════════")
        _print(
            f"🖥️  System: {'Atomic' if is_atomic else 'Traditional'} Fedora")
        _print(f"📦 Package Manager: {pm}")
        _print(f"⚡ Power Profile: {profile}")

        if is_atomic and SystemManager.has_pending_deployment():
            _print("🔄 Pending deployment: ⚠️  Reboot required")

    return 0


def cmd_health(args):
    """Show system health overview."""
    health = SystemMonitor.get_system_health()

    if _json_output:
        data = {
            "hostname": health.hostname,
            "uptime": health.uptime,
        }
        if health.memory:
            data["memory"] = {
                "used": health.memory.used_human,
                "total": health.memory.total_human,
                "percent": health.memory.percent_used,
                "status": health.memory_status,
            }
        if health.cpu:
            data["cpu"] = {
                "load_1min": health.cpu.load_1min,
                "load_5min": health.cpu.load_5min,
                "load_15min": health.cpu.load_15min,
                "cores": health.cpu.core_count,
                "load_percent": health.cpu.load_percent,
                "status": health.cpu_status,
            }
        disk_level, disk_msg = DiskManager.check_disk_health("/")
        data["disk"] = {"status": disk_level, "message": disk_msg}
        data["power_profile"] = TweakOps.get_power_profile()
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print("   System Health Check")
        _print("═══════════════════════════════════════════")
        _print(f"🖥️  Hostname: {health.hostname}")
        _print(f"⏱️  Uptime: {health.uptime}")

        if health.memory:
            mem_icon = "🟢" if health.memory_status == "ok" else (
                "🟡" if health.memory_status == "warning" else "🔴")
            _print(
                f"{mem_icon} Memory: {health.memory.used_human} / {health.memory.total_human} ({health.memory.percent_used}%)")
        else:
            _print("⚪ Memory: Unable to read")

        if health.cpu:
            cpu_icon = "🟢" if health.cpu_status == "ok" else (
                "🟡" if health.cpu_status == "warning" else "🔴")
            _print(f"{cpu_icon} CPU Load: {health.cpu.load_1min} / {health.cpu.load_5min} / {health.cpu.load_15min} ({health.cpu.core_count} cores, {health.cpu.load_percent}%)")
        else:
            _print("⚪ CPU: Unable to read")

        disk_level, disk_msg = DiskManager.check_disk_health("/")
        disk_icon = "🟢" if disk_level == "ok" else (
            "🟡" if disk_level == "warning" else "🔴")
        _print(f"{disk_icon} {disk_msg}")
        _print(f"⚡ Power Profile: {TweakOps.get_power_profile()}")
        _print(
            f"💻 System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora ({SystemManager.get_variant_name()})")

    return 0


def cmd_disk(args):
    """Show disk usage information."""
    usage = DiskManager.get_disk_usage("/")

    if _json_output:
        data = {"root": None, "home": None}
        if usage:
            level, msg = DiskManager.check_disk_health("/")
            data["root"] = {
                "total": usage.total_human,
                "used": usage.used_human,
                "free": usage.free_human,
                "percent": usage.percent_used,
                "status": level,
            }
        home_usage = DiskManager.get_disk_usage(os.path.expanduser("~"))
        if home_usage and home_usage.mount_point != "/":
            level, _ = DiskManager.check_disk_health(home_usage.mount_point)
            data["home"] = {
                "mount_point": home_usage.mount_point,
                "total": home_usage.total_human,
                "used": home_usage.used_human,
                "free": home_usage.free_human,
                "percent": home_usage.percent_used,
                "status": level,
            }
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print("   Disk Usage")
        _print("═══════════════════════════════════════════")

        if usage:
            level, msg = DiskManager.check_disk_health("/")
            icon = "🟢" if level == "ok" else (
                "🟡" if level == "warning" else "🔴")
            _print(f"\n{icon} Root (/)")
            _print(f"   Total: {usage.total_human}")
            _print(f"   Used:  {usage.used_human} ({usage.percent_used}%)")
            _print(f"   Free:  {usage.free_human}")
        else:
            _print("❌ Unable to read root filesystem")

        home_usage = DiskManager.get_disk_usage(os.path.expanduser("~"))
        if home_usage and home_usage.mount_point != "/":
            level, _ = DiskManager.check_disk_health(home_usage.mount_point)
            icon = "🟢" if level == "ok" else (
                "🟡" if level == "warning" else "🔴")
            _print(f"\n{icon} Home ({home_usage.mount_point})")
            _print(f"   Total: {home_usage.total_human}")
            _print(
                f"   Used:  {home_usage.used_human} ({home_usage.percent_used}%)")
            _print(f"   Free:  {home_usage.free_human}")

        if getattr(args, "details", False):
            home_dir = os.path.expanduser("~")
            _print(f"\n📂 Largest directories in {home_dir}:")
            large_dirs = DiskManager.find_large_directories(
                home_dir, max_depth=2, top_n=5)
            if large_dirs:
                for d in large_dirs:
                    _print(f"   {d.size_human:>10}  {d.path}")
            else:
                _print("   (no results)")

    return 0


def cmd_processes(args):
    """Show top processes."""
    counts = ProcessManager.get_process_count()
    n = getattr(args, "count", 10)
    sort_by = getattr(args, "sort", "cpu")

    if sort_by == "memory":
        processes = ProcessManager.get_top_by_memory(n)
    else:
        processes = ProcessManager.get_top_by_cpu(n)

    if _json_output:
        data = {
            "counts": counts,
            "sort_by": sort_by,
            "processes": [
                {
                    "pid": p.pid,
                    "name": p.name,
                    "cpu_percent": p.cpu_percent,
                    "memory_percent": p.memory_percent,
                    "memory_bytes": p.memory_bytes,
                    "user": p.user,
                }
                for p in processes
            ],
        }
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print("   Process Monitor")
        _print("═══════════════════════════════════════════")
        _print(
            f"\n📊 Total: {counts['total']} | Running: {counts['running']} | Sleeping: {counts['sleeping']} | Zombie: {counts['zombie']}")
        _print(f"\n🔍 Top {n} by {'Memory' if sort_by == 'memory' else 'CPU'}:")
        _print(
            f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'Memory':>10}  {'User':<12}  {'Name'}")
        _print("─" * 70)
        for p in processes:
            mem_human = ProcessManager.bytes_to_human(p.memory_bytes)
            _print(
                f"{p.pid:>7}  {p.cpu_percent:>5.1f}%  {p.memory_percent:>5.1f}%  {mem_human:>10}  {p.user:<12}  {p.name}")

    return 0


def cmd_temperature(args):
    """Show temperature readings."""
    sensors = TemperatureManager.get_all_sensors()

    if _json_output:
        data = {
            "sensors": [
                {
                    "label": s.label,
                    "current": s.current,
                    "high": s.high,
                    "critical": s.critical,
                }
                for s in sensors
            ]
        }
        if sensors:
            data["avg"] = sum(s.current for s in sensors) / len(sensors)
            data["max"] = max(s.current for s in sensors)
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print("   Temperature Monitor")
        _print("═══════════════════════════════════════════")

        if not sensors:
            _print("\n⚠️  No temperature sensors found.")
            _print("   Ensure lm_sensors is installed: sudo dnf install lm_sensors")
            return 1

        for sensor in sensors:
            if sensor.critical and sensor.current >= sensor.critical:
                icon = "🔴"
            elif sensor.high and sensor.current >= sensor.high:
                icon = "🟡"
            else:
                icon = "🟢"

            line = f"{icon} {sensor.label:<20} {sensor.current:>5.1f}°C"
            if sensor.high:
                line += f"  (high: {sensor.high:.0f}°C)"
            if sensor.critical:
                line += f"  (crit: {sensor.critical:.0f}°C)"
            _print(line)

        if len(sensors) > 1:
            avg_temp = sum(s.current for s in sensors) / len(sensors)
            hottest = max(sensors, key=lambda s: s.current)
            _print(
                f"\n📊 Summary: avg {avg_temp:.1f}°C | max {hottest.current:.1f}°C ({hottest.label})")

    return 0


def cmd_netmon(args):
    """Show network interface stats."""
    interfaces = NetworkMonitor.get_all_interfaces()

    if _json_output:
        data = {
            "interfaces": [
                {
                    "name": i.name,
                    "type": i.type,
                    "is_up": i.is_up,
                    "ip_address": i.ip_address if hasattr(i, "ip_address") else None,
                    "bytes_recv": i.bytes_recv,
                    "bytes_sent": i.bytes_sent,
                }
                for i in interfaces
            ],
            "summary": NetworkMonitor.get_bandwidth_summary(),
        }
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print("   Network Monitor")
        _print("═══════════════════════════════════════════")

        if not interfaces:
            _print("\n⚠️  No network interfaces found.")
            return 1

        for iface in interfaces:
            status = "UP" if iface.is_up else "DOWN"
            icon = "🟢" if iface.is_up else "🔴"
            _print(f"\n{icon} {iface.name} ({iface.type}) [{status}]")
            if iface.ip_address:
                _print(f"   IP: {iface.ip_address}")
            _print(
                f"   RX: {NetworkMonitor.bytes_to_human(iface.bytes_recv)}  TX: {NetworkMonitor.bytes_to_human(iface.bytes_sent)}")
            if iface.recv_rate > 0 or iface.send_rate > 0:
                _print(
                    f"   Rate: ↓{NetworkMonitor.bytes_to_human(int(iface.recv_rate))}/s  ↑{NetworkMonitor.bytes_to_human(int(iface.send_rate))}/s")

        summary = NetworkMonitor.get_bandwidth_summary()
        _print(
            f"\n📊 Total: ↓{NetworkMonitor.bytes_to_human(summary['total_recv'])} ↑{NetworkMonitor.bytes_to_human(summary['total_sent'])}")

        if getattr(args, "connections", False):
            connections = NetworkMonitor.get_active_connections()
            if connections:
                _print(f"\n🔗 Active Connections ({len(connections)}):")
                _print(
                    f"{'Proto':<6} {'Local':>21} {'Remote':>21} {'State':<14} {'Process'}")
                _print("─" * 80)
                for conn in connections[:20]:
                    local = f"{conn.local_addr}:{conn.local_port}"
                    remote = f"{conn.remote_addr}:{conn.remote_port}" if conn.remote_addr != "0.0.0.0" else "*"
                    _print(
                        f"{conn.protocol:<6} {local:>21} {remote:>21} {conn.state:<14} {conn.process_name}")

    return 0


def cmd_doctor(args):
    """Run system diagnostics and check dependencies."""
    critical_tools = ["dnf", "pkexec", "systemctl", "flatpak"]
    optional_tools = ["fwupdmgr", "timeshift", "nbfc",
                      "firejail", "ollama", "distrobox", "podman"]

    if _json_output:
        data = {"critical": {}, "optional": {}}
        for tool in critical_tools:
            data["critical"][tool] = shutil.which(tool) is not None
        for tool in optional_tools:
            data["optional"][tool] = shutil.which(tool) is not None
        data["all_critical_ok"] = all(data["critical"].values())
        _output_json(data)
    else:
        _print("═══════════════════════════════════════════")
        _print("   System Doctor")
        _print("═══════════════════════════════════════════")

        _print("\nCritical Tools:")
        all_ok = True
        for tool in critical_tools:
            found = shutil.which(tool) is not None
            icon = "✅" if found else "❌"
            _print(f"  {icon} {tool}")
            if not found:
                all_ok = False

        _print("\nOptional Tools:")
        for tool in optional_tools:
            found = shutil.which(tool) is not None
            icon = "✅" if found else "⚪"
            _print(f"  {icon} {tool}")

        if all_ok:
            _print("\n🟢 All critical dependencies found.")
        else:
            _print(
                "\n🔴 Some critical tools are missing. Install them for full functionality.")

    return 0 if all_ok else 1


def cmd_hardware(args):
    """Show detected hardware profile."""
    from services.hardware.hardware_profiles import detect_hardware_profile

    key, profile = detect_hardware_profile()

    if _json_output:
        _output_json({"profile_key": key, "profile": profile})
    else:
        _print("═══════════════════════════════════════════")
        _print("   Hardware Profile")
        _print("═══════════════════════════════════════════")
        _print(f"\n🖥️  Detected: {profile['label']}")
        _print(
            f"   Battery Limit:    {'✅' if profile.get('battery_limit') else '❌'}")
        _print(f"   Fan Control:      {'✅' if profile.get('nbfc') else '❌'}")
        _print(
            f"   Fingerprint:      {'✅' if profile.get('fingerprint') else '❌'}")
        _print(
            f"   Power Profiles:   {'✅' if profile.get('power_profiles') else '❌'}")
        thermal = profile.get('thermal_management', 'None')
        _print(f"   Thermal Driver:   {thermal or 'Generic'}")

    return 0


def cmd_self_update(args):
    """Check and run self-update flow."""
    package_manager = SystemManager.get_package_manager()
    preference = UpdateChecker.resolve_artifact_preference(
        package_manager, args.channel)
    use_cache = not args.no_cache

    if args.action == "check":
        info = UpdateChecker.check_for_updates(
            timeout=args.timeout, use_cache=use_cache)
        if _json_output:
            _output_json(
                {
                    "success": info is not None,
                    "stage": "check",
                    "update_available": bool(info and info.is_newer),
                    "offline": bool(info and info.offline),
                    "source": info.source if info else "network",
                    "current_version": info.current_version if info else __version__,
                    "latest_version": info.latest_version if info else None,
                    "selected_asset": info.selected_asset.name if info and info.selected_asset else None,
                }
            )
            return 0 if info is not None else 1

        if info is None:
            _print("❌ Update check failed")
            return 1
        if info.is_newer:
            _print(
                f"✅ Update available: {info.current_version} -> {info.latest_version}")
            if info.selected_asset:
                _print(f"📦 Selected asset: {info.selected_asset.name}")
        else:
            _print("✅ No update available")
        return 0

    result = UpdateChecker.run_auto_update(
        artifact_preference=preference,
        target_dir=os.path.expanduser(args.download_dir),
        timeout=args.timeout,
        use_cache=use_cache,
        expected_sha256=args.checksum,
        signature_path=args.signature_path,
        public_key_path=args.public_key_path,
    )

    if _json_output:
        _output_json(
            {
                "success": result.success,
                "stage": result.stage,
                "error": result.error,
                "offline": result.offline,
                "source": result.source,
                "selected_asset": result.selected_asset.name if result.selected_asset else None,
                "downloaded_file": result.download.file_path if result.download else None,
                "download_ok": result.download.ok if result.download else None,
                "verify_ok": result.verify.ok if result.verify else None,
            }
        )
    else:
        if result.success:
            _print("✅ Update package downloaded and verified")
            if result.download and result.download.file_path:
                _print(f"📁 File: {result.download.file_path}")
        else:
            _print(
                f"❌ Self-update failed at stage '{result.stage}': {result.error}")

    return 0 if result.success else 1


def cmd_plugins(args):
    """Manage plugins."""
    loader = PluginLoader()

    if args.action == "list":
        plugins = loader.list_plugins()
        if _json_output:
            _output_json({"plugins": plugins})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Plugins")
            _print("═══════════════════════════════════════════")
            if not plugins:
                _print("\n(no plugins found)")
                return 0
            for plugin in plugins:
                name = plugin["name"]
                enabled = plugin["enabled"]
                manifest = plugin.get("manifest") or {}
                status = "✅" if enabled else "❌"
                version = manifest.get("version", "unknown")
                desc = manifest.get("description", "")
                _print(f"{status} {name} v{version}")
                if desc:
                    _print(f"   {desc}")
        return 0

    if args.action in ("enable", "disable"):
        if not args.name:
            _print("❌ Plugin name required")
            return 1
        enabled = args.action == "enable"
        loader.set_enabled(args.name, enabled)
        if _json_output:
            _output_json({"plugin": args.name, "enabled": enabled})
        else:
            _print(
                f"{'✅' if enabled else '❌'} {args.name} {'enabled' if enabled else 'disabled'}")
        return 0

    return 1


def cmd_plugin_marketplace(args):
    """Plugin marketplace operations."""
    marketplace = PluginMarketplace()
    installer = PluginInstaller()
    use_json = getattr(args, 'json', False) or _json_output

    def _resolve_plugin_id():
        """Accept both modern `plugin_id` and legacy `plugin` argparse names."""
        plugin_id = getattr(args, 'plugin_id', None)
        if isinstance(plugin_id, str) and plugin_id:
            return plugin_id
        legacy = getattr(args, 'plugin', None)
        if isinstance(legacy, str) and legacy:
            return legacy
        return None

    if args.action == "search":
        query = getattr(args, 'query', None) or ""
        category = getattr(args, 'category', None)
        result = marketplace.search(query=query, category=category)

        if not result.success:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

        plugins = result.data or []
        if use_json:
            data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "version": p.version,
                    "author": p.author,
                    "category": p.category,
                    "description": p.description,
                    "verified_publisher": bool(getattr(p, "verified_publisher", False)),
                    "publisher_id": getattr(p, "publisher_id", None),
                    "publisher_badge": getattr(p, "publisher_badge", None),
                }
                for p in plugins
            ]
            print(json_module.dumps(
                {"plugins": data, "count": len(data)}, indent=2, default=str))
        else:
            if not plugins:
                print("No plugins found")
                return 0
            for p in plugins:
                print(f"📦 {p.name} v{p.version} by {p.author}")
                print(f"   Category: {p.category}")
                if getattr(p, "verified_publisher", False):
                    badge = getattr(p, "publisher_badge", None) or "verified"
                    publisher_id = getattr(p, "publisher_id", None)
                    publisher_suffix = f" ({publisher_id})" if publisher_id else ""
                    print(f"   Publisher: {badge}{publisher_suffix}")
                print(f"   {p.description}")
                print()
        return 0

    if args.action == "info":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        result = marketplace.get_plugin(plugin_id)

        if not result.success:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

        plugin = result.data[0] if isinstance(
            result.data, list) else result.data

        if use_json:
            data = {
                "id": plugin.id,
                "name": plugin.name,
                "version": plugin.version,
                "author": plugin.author,
                "category": plugin.category,
                "description": plugin.description,
                "homepage": getattr(plugin, 'homepage', None),
                "license": getattr(plugin, 'license', None),
                "verified_publisher": bool(getattr(plugin, "verified_publisher", False)),
                "publisher_id": getattr(plugin, "publisher_id", None),
                "publisher_badge": getattr(plugin, "publisher_badge", None),
            }
            print(json_module.dumps(data, indent=2, default=str))
        else:
            print(f"{plugin.name} v{plugin.version}")
            print(f"Author:      {plugin.author}")
            print(f"Category:    {plugin.category}")
            print(f"Description: {plugin.description}")
            if getattr(plugin, "verified_publisher", False):
                badge = getattr(plugin, "publisher_badge", None) or "verified"
                publisher_id = getattr(plugin, "publisher_id", None)
                if publisher_id:
                    print(f"Publisher:   {badge} ({publisher_id})")
                else:
                    print(f"Publisher:   {badge}")
            if getattr(plugin, 'homepage', None):
                print(f"Homepage:    {plugin.homepage}")
        return 0

    if args.action == "install":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        # Fetch plugin info
        info_result = marketplace.get_plugin(plugin_id)
        if not info_result.success:
            print(f"Error: {info_result.error}", file=sys.stderr)
            return 1

        plugin = info_result.data[0] if isinstance(
            info_result.data, list) else info_result.data

        # Check permissions consent
        permissions = getattr(plugin, 'requires', None) or []
        accept = getattr(args, 'accept_permissions', False)
        if permissions and not accept:
            print(
                f"Plugin '{plugin.name}' requires permissions: {', '.join(permissions)}")
            print("Re-run with --accept-permissions to install")
            return 1

        result = installer.install(plugin_id)

        if result.success:
            if use_json:
                print(json_module.dumps(
                    {"status": "success", "plugin": plugin_id}, indent=2, default=str))
            else:
                print(f"Successfully installed '{plugin.name}'")
            return 0
        else:
            print(
                f"Error: Installation failed: {result.error}", file=sys.stderr)
            return 1

    if args.action == "reviews":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        limit = getattr(args, "limit", 20)
        offset = getattr(args, "offset", 0)
        result = marketplace.fetch_reviews(
            plugin_id=plugin_id, limit=limit, offset=offset)

        if not result.success:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

        reviews = result.data or []
        if use_json:
            data = [
                {
                    "plugin_id": r.plugin_id,
                    "reviewer": r.reviewer,
                    "rating": r.rating,
                    "title": r.title,
                    "comment": r.comment,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                }
                for r in reviews
            ]
            print(json_module.dumps({"plugin_id": plugin_id, "reviews": data, "count": len(
                data)}, indent=2, default=str))
        else:
            if not reviews:
                print("No reviews found")
                return 0
            for review in reviews:
                print(f"★ {review.rating}/5 by {review.reviewer}")
                if review.title:
                    print(f"  {review.title}")
                if review.comment:
                    print(f"  {review.comment}")
                if review.created_at:
                    print(f"  Date: {review.created_at}")
                print()
        return 0

    if args.action == "review-submit":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        reviewer = getattr(args, "reviewer", "")
        rating = getattr(args, "rating", None)
        title = getattr(args, "title", "") or ""
        comment = getattr(args, "comment", "") or ""

        result = marketplace.submit_review(
            plugin_id=plugin_id,
            reviewer=reviewer,
            rating=rating,
            title=title,
            comment=comment,
        )

        if not result.success:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

        if use_json:
            print(json_module.dumps(
                {"status": "success", "plugin_id": plugin_id, "review": result.data}, indent=2, default=str))
        else:
            print(f"Review submitted for '{plugin_id}'")
        return 0

    if args.action == "rating":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        result = marketplace.get_rating_aggregate(plugin_id=plugin_id)
        if not result.success:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

        aggregate = result.data
        if use_json:
            print(
                json_module.dumps(
                    {
                        "plugin_id": aggregate.plugin_id,
                        "average_rating": aggregate.average_rating,
                        "rating_count": aggregate.rating_count,
                        "review_count": aggregate.review_count,
                        "breakdown": aggregate.breakdown,
                    },
                    indent=2,
                    default=str,
                )
            )
        else:
            print(
                f"Rating for {aggregate.plugin_id}: {aggregate.average_rating:.2f}/5")
            print(f"Ratings: {aggregate.rating_count}")
            print(f"Reviews: {aggregate.review_count}")
            if aggregate.breakdown:
                print("Breakdown:")
                for stars in sorted(aggregate.breakdown.keys(), reverse=True):
                    print(f"  {stars}★: {aggregate.breakdown[stars]}")
        return 0

    if args.action == "uninstall":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        result = installer.uninstall(plugin_id)

        if result.success:
            if use_json:
                print(json_module.dumps(
                    {"status": "success", "plugin": plugin_id}, indent=2, default=str))
            else:
                print(f"Successfully uninstalled '{plugin_id}'")
            return 0
        else:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

    if args.action == "update":
        plugin_id = _resolve_plugin_id()
        if not plugin_id:
            print("Error: Plugin ID required", file=sys.stderr)
            return 1

        # Check if update is available first
        check = installer.check_update(plugin_id)
        if check.success and check.data and not check.data.get("update_available", True):
            print(f"Plugin '{plugin_id}' is already up to date")
            return 0

        result = installer.update(plugin_id)

        if result.success:
            if use_json:
                print(json_module.dumps(
                    {"status": "success", "plugin": plugin_id}, indent=2, default=str))
            else:
                print(f"Successfully updated '{plugin_id}'")
            return 0
        else:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1

    if args.action == "list-installed":
        result = installer.list_installed()

        plugins = result.data or []
        if use_json:
            print(json_module.dumps(plugins, indent=2, default=str))
        else:
            if not plugins:
                print("No plugins installed")
                return 0
            for p in plugins:
                name = p.get("name", p.get("id", "unknown"))
                version = p.get("version", "unknown")
                print(f"📦 {name} v{version}")
        return 0

    return 1


def cmd_support_bundle(args):
    """Export support bundle ZIP."""
    result = JournalManager.export_support_bundle()
    if _json_output:
        _output_json({"success": result.success,
                     "message": result.message, "data": result.data})
    else:
        _print(f"{'✅' if result.success else '❌'} {result.message}")
    return 0 if result.success else 1


# ==================== v11.5 / v12.0 COMMANDS ====================


def cmd_vm(args):
    """Handle VM subcommand."""
    from utils.vm_manager import VMManager

    if args.action == "list":
        vms = VMManager.list_vms()
        if _json_output:
            from dataclasses import asdict
            _output_json({"vms": [asdict(v) for v in vms]})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Virtual Machines")
            _print("═══════════════════════════════════════════")
            if not vms:
                _print("\n(no VMs found)")
            else:
                for vm in vms:
                    icon = "🟢" if vm.state == "running" else "⚪"
                    _print(
                        f"  {icon} {vm.name} [{vm.state}]  RAM: {vm.memory_mb}MB  vCPUs: {vm.vcpus}")
        return 0

    elif args.action == "status":
        status = VMManager.get_vm_info(args.name)
        if _json_output:
            _output_json(status if isinstance(status, dict)
                         else {"error": "VM not found"})
        else:
            if status:
                _print(
                    f"VM: {status.get('name', args.name)} [{status.get('state', 'unknown')}]")
            else:
                _print(f"❌ VM '{args.name}' not found")
        return 0

    elif args.action == "start":
        result = VMManager.start_vm(args.name)
        _print(f"{'✅' if result.success else '❌'} {result.message}")
        return 0 if result.success else 1

    elif args.action == "stop":
        result = VMManager.stop_vm(args.name)
        _print(f"{'✅' if result.success else '❌'} {result.message}")
        return 0 if result.success else 1

    return 1


def cmd_vfio(args):
    """Handle VFIO GPU passthrough subcommand."""
    from utils.vfio import VFIOAssistant

    if args.action == "check":
        prereqs = VFIOAssistant.check_prerequisites()
        if _json_output:
            _output_json(prereqs)
        else:
            _print("═══════════════════════════════════════════")
            _print("   VFIO Prerequisites Check")
            _print("═══════════════════════════════════════════")
            for key, val in prereqs.items():
                icon = "✅" if val else "❌"
                _print(f"  {icon} {key}")
        return 0

    elif args.action == "gpus":
        candidates = VFIOAssistant.get_passthrough_candidates()
        if _json_output:
            _output_json({"candidates": candidates})
        else:
            _print("═══════════════════════════════════════════")
            _print("   GPU Passthrough Candidates")
            _print("═══════════════════════════════════════════")
            if not candidates:
                _print("\n(no candidates found)")
            else:
                for gpu in candidates:
                    _print(f"\n  {gpu.get('name', 'Unknown GPU')}")
                    _print(f"    IOMMU Group: {gpu.get('iommu_group', '?')}")
                    _print(
                        f"    IDs: {gpu.get('vendor_id', '?')}:{gpu.get('device_id', '?')}")
        return 0

    elif args.action == "plan":
        plan = VFIOAssistant.get_step_by_step_plan()
        if _json_output:
            _output_json({"steps": plan})
        else:
            _print("═══════════════════════════════════════════")
            _print("   VFIO Setup Plan")
            _print("═══════════════════════════════════════════")
            for i, step in enumerate(plan, 1):
                _print(f"\n  Step {i}: {step}")
        return 0

    return 1


def cmd_mesh(args):
    """Handle mesh networking subcommand."""
    from utils.mesh_discovery import MeshDiscovery

    if args.action == "discover":
        peers = MeshDiscovery.discover_peers()
        if _json_output:
            from dataclasses import asdict
            _output_json({"peers": [asdict(p) for p in peers]})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Loofi Link - Nearby Devices")
            _print("═══════════════════════════════════════════")
            if not peers:
                _print("\n(no devices found on local network)")
            else:
                for peer in peers:
                    _print(f"  🔗 {peer.hostname} ({peer.ip_address})")
        return 0

    elif args.action == "status":
        device_id = MeshDiscovery.get_device_id()
        local_ips = MeshDiscovery.get_local_ips()
        if _json_output:
            _output_json({"device_id": device_id, "local_ips": local_ips})
        else:
            _print(f"Device ID: {device_id}")
            _print(f"Local IPs: {', '.join(local_ips)}")
        return 0

    return 1


def cmd_teleport(args):
    """Handle state teleport subcommand."""
    from utils.state_teleport import StateTeleportManager

    if args.action == "capture":
        workspace_path = getattr(args, "path", None) or os.getcwd()
        state = StateTeleportManager.capture_full_state(workspace_path)
        package = StateTeleportManager.create_teleport_package(
            state, target_device=getattr(args, "target", "unknown")
        )
        pkg_dir = StateTeleportManager.get_package_dir()
        filepath = os.path.join(pkg_dir, f"{package.package_id}.json")
        result = StateTeleportManager.save_package_to_file(package, filepath)

        if _json_output:
            _output_json({
                "success": result.success,
                "package_id": package.package_id,
                "file": filepath,
            })
        else:
            _print(f"{'✅' if result.success else '❌'} {result.message}")
            if result.success:
                _print(f"   Package ID: {package.package_id}")
                _print(f"   Size: {package.size_bytes} bytes")
        return 0 if result.success else 1

    elif args.action == "list":
        packages = StateTeleportManager.list_saved_packages()
        if _json_output:
            _output_json({"packages": packages})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Saved Teleport Packages")
            _print("═══════════════════════════════════════════")
            if not packages:
                _print("\n(no packages found)")
            else:
                for pkg in packages:
                    _print(
                        f"  📦 {pkg['package_id'][:8]}... from {pkg['source_device']}")
                    _print(f"     Size: {pkg['size_bytes']} bytes")
        return 0

    elif args.action == "restore":
        if not args.package_id:
            _print("❌ Package ID required for restore")
            return 1
        pkg_dir = StateTeleportManager.get_package_dir()
        # Find matching package file
        for filename in os.listdir(pkg_dir):
            if args.package_id in filename:
                filepath = os.path.join(pkg_dir, filename)
                package = StateTeleportManager.load_package_from_file(filepath)
                result = StateTeleportManager.apply_teleport(package)
                _print(f"{'✅' if result.success else '❌'} {result.message}")
                return 0 if result.success else 1
        _print(f"❌ Package '{args.package_id}' not found")
        return 1

    return 1


def cmd_ai_models(args):
    """Handle AI models subcommand."""
    from utils.ai_models import AIModelManager

    if args.action == "list":
        installed = AIModelManager.get_installed_models()
        recommended = AIModelManager.RECOMMENDED_MODELS
        if _json_output:
            _output_json(
                {"installed": installed, "recommended": list(recommended.keys())})
        else:
            _print("═══════════════════════════════════════════")
            _print("   AI Models")
            _print("═══════════════════════════════════════════")
            _print("\nInstalled:")
            if not installed:
                _print("  (none - install Ollama first)")
            else:
                for model in installed:
                    _print(f"  ✅ {model}")
            _print("\nRecommended:")
            for name, info in recommended.items():
                status = "✅" if name in installed else "⚪"
                _print(f"  {status} {name} - {info.get('description', '')}")
        return 0

    elif args.action == "recommend":
        model = AIModelManager.get_recommended_model()
        if _json_output:
            _output_json({"recommended": model})
        else:
            if model:
                _print(f"Recommended model for this system: {model}")
            else:
                _print("Unable to determine recommended model")
        return 0

    return 1


def cmd_preset(args):
    """Handle preset subcommand."""
    manager = PresetManager()

    if args.action == "list":
        presets = manager.list_presets()
        if _json_output:
            _output_json({"presets": presets})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Available Presets")
            _print("═══════════════════════════════════════════")
            if not presets:
                _print("\n(no presets found)")
            else:
                for name in presets:
                    _print(f"  📋 {name}")
        return 0

    elif args.action == "apply":
        if not args.name:
            _print("❌ Preset name required")
            return 1
        result = manager.load_preset(args.name)
        if result:
            if _json_output:
                _output_json(
                    {"success": True, "applied": args.name, "settings": result})
            else:
                _print(f"✅ Applied preset: {args.name}")
            return 0
        else:
            if _json_output:
                _output_json(
                    {"success": False, "error": f"Preset '{args.name}' not found"})
            else:
                _print(f"❌ Preset '{args.name}' not found")
            return 1

    elif args.action == "export":
        if not args.name or not args.path:
            _print("❌ Preset name and path required")
            return 1
        # First load the preset to get its data
        result = manager.load_preset(args.name)
        if not result:
            _print(f"❌ Preset '{args.name}' not found")
            return 1
        # Write to file
        try:
            with open(args.path, "w") as f:
                json_module.dump(result, f, indent=2)
            if _json_output:
                _output_json(
                    {"success": True, "exported": args.name, "path": args.path})
            else:
                _print(f"✅ Exported preset '{args.name}' to {args.path}")
            return 0
        except Exception as e:
            _print(f"❌ Export failed: {e}")
            return 1

    return 1


def cmd_focus_mode(args):
    """Handle focus-mode subcommand."""
    if args.action == "on":
        profile = getattr(args, "profile", "default")
        result = FocusMode.enable(profile)
        if _json_output:
            _output_json(result)
        else:
            icon = "✅" if result["success"] else "❌"
            _print(f"{icon} {result['message']}")
            if result.get("hosts_modified"):
                _print("   🌐 Domains blocked via /etc/hosts")
            if result.get("dnd_enabled"):
                _print("   🔕 Do Not Disturb enabled")
            if result.get("processes_killed"):
                _print(
                    f"   💀 Killed processes: {', '.join(result['processes_killed'])}")
        return 0 if result["success"] else 1

    elif args.action == "off":
        result = FocusMode.disable()
        if _json_output:
            _output_json(result)
        else:
            icon = "✅" if result["success"] else "❌"
            _print(f"{icon} {result['message']}")
        return 0 if result["success"] else 1

    elif args.action == "status":
        is_active = FocusMode.is_active()
        active_profile = FocusMode.get_active_profile()
        profiles = FocusMode.list_profiles()

        if _json_output:
            _output_json({
                "active": is_active,
                "active_profile": active_profile,
                "profiles": profiles
            })
        else:
            _print("═══════════════════════════════════════════")
            _print("   Focus Mode Status")
            _print("═══════════════════════════════════════════")
            status_icon = "🟢 Active" if is_active else "⚪ Inactive"
            _print(f"\nStatus: {status_icon}")
            if active_profile:
                _print(f"Profile: {active_profile}")
            _print(f"\nAvailable profiles: {', '.join(profiles)}")
        return 0

    return 1


def cmd_security_audit(args):
    """Handle security-audit subcommand."""
    score_data = PortAuditor.get_security_score()

    if _json_output:
        _output_json(score_data)
    else:
        score = score_data["score"]
        rating = score_data["rating"]

        # Color based on score
        if score >= 90:
            icon = "🟢"
        elif score >= 70:
            icon = "🟡"
        elif score >= 50:
            icon = "🟠"
        else:
            icon = "🔴"

        _print("═══════════════════════════════════════════")
        _print("   Security Audit")
        _print("═══════════════════════════════════════════")
        _print(f"\n{icon} Security Score: {score}/100 ({rating})")
        _print(f"\n📊 Open Ports: {score_data['open_ports']}")
        _print(f"⚠️  Risky Ports: {score_data['risky_ports']}")

        fw_status = "Running" if PortAuditor.is_firewalld_running() else "Not Running"
        fw_icon = "✅" if PortAuditor.is_firewalld_running() else "❌"
        _print(f"{fw_icon} Firewall: {fw_status}")

        if score_data["recommendations"]:
            _print("\n📋 Recommendations:")
            for rec in score_data["recommendations"]:
                _print(f"   • {rec}")

    return 0


def cmd_profile(args):
    """Handle profile subcommand."""
    if args.action == "list":
        profiles = ProfileManager.list_profiles()
        if _json_output:
            _output_json({"profiles": profiles})
        else:
            _print("═══════════════════════════════════════════")
            _print("   System Profiles")
            _print("═══════════════════════════════════════════")
            if not profiles:
                _print("\n(no profiles found)")
            else:
                active = ProfileManager.get_active_profile()
                for p in profiles:
                    badge = " [ACTIVE]" if p["key"] == active else ""
                    ptype = "built-in" if p["builtin"] else "custom"
                    _print(f"\n  {p['icon']}  {p['name']}{badge}")
                    _print(f"      Key: {p['key']} ({ptype})")
                    _print(f"      {p['description']}")
        return 0

    elif args.action == "apply":
        if not args.name:
            _print("❌ Profile name required")
            return 1
        result = ProfileManager.apply_profile(
            args.name,
            create_snapshot=not getattr(args, "no_snapshot", False),
        )
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "create":
        if not args.name:
            _print("❌ Profile name required")
            return 1
        result = ProfileManager.capture_current_as_profile(args.name)
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "delete":
        if not args.name:
            _print("❌ Profile name required")
            return 1
        result = ProfileManager.delete_custom_profile(args.name)
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "export":
        if not args.name or not args.path:
            _print("❌ Profile name and export path required")
            return 1
        result = ProfileManager.export_profile_json(args.name, args.path)
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "import":
        path = args.path or args.name
        if not path:
            _print("❌ Import path required")
            return 1
        result = ProfileManager.import_profile_json(
            path, overwrite=getattr(args, "overwrite", False))
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "export-all":
        path = args.path or args.name
        if not path:
            _print("❌ Export path required")
            return 1
        result = ProfileManager.export_bundle_json(
            path,
            include_builtins=getattr(args, "include_builtins", False),
        )
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "import-all":
        path = args.path or args.name
        if not path:
            _print("❌ Import bundle path required")
            return 1
        result = ProfileManager.import_bundle_json(
            path, overwrite=getattr(args, "overwrite", False))
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    return 1


def cmd_health_history(args):
    """Handle health-history subcommand."""
    timeline = HealthTimeline()

    if args.action == "show":
        summary = timeline.get_summary(hours=24)
        if _json_output:
            _output_json({"summary": summary})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Health Timeline (24h Summary)")
            _print("═══════════════════════════════════════════")
            if not summary:
                _print("\n(no metrics recorded)")
                _print("Run 'loofi health-history record' to capture a snapshot.")
            else:
                metric_labels = {
                    "cpu_temp": ("CPU Temp", "C"),
                    "ram_usage": ("RAM Usage", "%"),
                    "disk_usage": ("Disk Usage", "%"),
                    "load_avg": ("Load Avg", ""),
                }
                for metric_type, data in summary.items():
                    label, unit = metric_labels.get(
                        metric_type, (metric_type, ""))
                    _print(f"\n  {label}:")
                    _print(f"      Min: {data['min']:.1f}{unit}")
                    _print(f"      Max: {data['max']:.1f}{unit}")
                    _print(f"      Avg: {data['avg']:.1f}{unit}")
                    _print(f"      Samples: {data['count']}")
        return 0

    elif args.action == "record":
        result = timeline.record_snapshot()
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "export":
        if not args.path:
            _print("❌ Export path required")
            return 1
        # Determine format from extension
        if args.path.lower().endswith(".csv"):
            format_type = "csv"
        else:
            format_type = "json"
        result = timeline.export_metrics(args.path, format=format_type)
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "prune":
        result = timeline.prune_old_data()
        if _json_output:
            _output_json({
                "success": result.success,
                "message": result.message,
                "data": result.data,
            })
        else:
            icon = "✅" if result.success else "❌"
            _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    return 1


# ==================== v15.0 Nebula CLI commands ====================


def cmd_tuner(args):
    """Handle tuner subcommand."""
    from utils.auto_tuner import AutoTuner

    if args.action == "analyze":
        workload = AutoTuner.detect_workload()
        rec = AutoTuner.recommend(workload)
        current = AutoTuner.get_current_settings()
        if _json_output:
            _output_json({
                "workload": vars(workload),
                "recommendation": vars(rec),
                "current_settings": current,
            })
        else:
            _print("═══════════════════════════════════════════")
            _print("   Performance Auto-Tuner")
            _print("═══════════════════════════════════════════")
            _print(f"\n  Workload Detected: {workload.name}")
            _print(
                f"  CPU: {workload.cpu_percent:.1f}%  Memory: {workload.memory_percent:.1f}%")
            _print(f"  Description: {workload.description}")
            _print("\n  Current Settings:")
            for k, v in current.items():
                _print(f"    {k}: {v}")
            _print("\n  Recommendations:")
            _print(f"    Governor: {rec.governor}")
            _print(f"    Swappiness: {rec.swappiness}")
            _print(f"    I/O Scheduler: {rec.io_scheduler}")
            _print(f"    THP: {rec.thp}")
            _print(f"    Reason: {rec.reason}")
        return 0

    elif args.action == "apply":
        rec = AutoTuner.recommend()
        _print(
            f"🔄 Applying: governor={rec.governor}, swappiness={rec.swappiness}")
        success = run_operation(AutoTuner.apply_recommendation(rec))
        if success:
            run_operation(AutoTuner.apply_swappiness(rec.swappiness))
        return 0 if success else 1

    elif args.action == "history":
        history = AutoTuner.get_tuning_history()
        if _json_output:
            _output_json([vars(h) for h in history])
        else:
            _print("═══════════════════════════════════════════")
            _print("   Tuning History")
            _print("═══════════════════════════════════════════")
            if not history:
                _print("\n  (no tuning history)")
            else:
                import time
                for entry in history[-10:]:
                    ts = time.strftime(
                        "%Y-%m-%d %H:%M", time.localtime(entry.timestamp))
                    _print(
                        f"\n  {ts} — {entry.workload} (applied: {entry.applied})")
        return 0

    return 1


def cmd_snapshot(args):
    """Handle snapshot subcommand."""
    from utils.snapshot_manager import SnapshotManager

    if args.action == "list":
        snapshots = SnapshotManager.list_snapshots()
        if _json_output:
            _output_json([vars(s) for s in snapshots])
        else:
            _print("═══════════════════════════════════════════")
            _print("   System Snapshots")
            _print("═══════════════════════════════════════════")
            if not snapshots:
                _print("\n  (no snapshots found)")
            else:
                import time
                for s in snapshots[:20]:
                    ts = time.strftime(
                        "%Y-%m-%d %H:%M", time.localtime(s.timestamp)) if s.timestamp else "unknown"
                    _print(
                        f"  [{s.backend}] {s.id}: {s.label or '(no label)'} — {ts}")
        return 0

    elif args.action == "create":
        label = args.label or "manual-snapshot"
        _print(f"🔄 Creating snapshot: {label}")
        success = run_operation(SnapshotManager.create_snapshot(label))
        return 0 if success else 1

    elif args.action == "delete":
        if not args.snapshot_id:
            _print("❌ Snapshot ID required")
            return 1
        success = run_operation(
            SnapshotManager.delete_snapshot(args.snapshot_id))
        return 0 if success else 1

    elif args.action == "backends":
        backends = SnapshotManager.detect_backends()
        if _json_output:
            _output_json([vars(b) for b in backends])
        else:
            _print("═══════════════════════════════════════════")
            _print("   Snapshot Backends")
            _print("═══════════════════════════════════════════")
            for b in backends:
                status = "✅" if b.available else "❌"
                _print(
                    f"  {status} {b.name}: {b.version if b.available else 'not installed'}")
        return 0

    return 1


def cmd_logs(args):
    """Handle logs subcommand."""
    from utils.smart_logs import SmartLogViewer

    if args.action == "show":
        entries = SmartLogViewer.get_logs(
            unit=args.unit,
            priority=args.priority,
            since=args.since,
            lines=args.lines,
        )
        if _json_output:
            _output_json([vars(e) for e in entries])
        else:
            for e in entries:
                marker = "⚠️ " if e.pattern_match else ""
                _print(
                    f"  {e.timestamp} [{e.priority_label}] {e.unit}: {marker}{e.message[:120]}")
                if e.pattern_match:
                    _print(f"    ↳ {e.pattern_match}")
        return 0

    elif args.action == "errors":
        summary = SmartLogViewer.get_error_summary(
            since=args.since or "24h ago")
        if _json_output:
            _output_json(vars(summary))
        else:
            _print("═══════════════════════════════════════════")
            _print("   Log Error Summary")
            _print("═══════════════════════════════════════════")
            _print(f"  Total entries: {summary.total_entries}")
            _print(f"  Critical: {summary.critical_count}")
            _print(f"  Errors: {summary.error_count}")
            _print(f"  Warnings: {summary.warning_count}")
            if summary.top_units:
                _print("\n  Top Units:")
                for unit, count in summary.top_units:
                    _print(f"    {unit}: {count}")
            if summary.detected_patterns:
                _print("\n  Detected Patterns:")
                for pattern, count in summary.detected_patterns:
                    _print(f"    {pattern}: {count}")
        return 0

    elif args.action == "export":
        if not args.path:
            _print("❌ Export path required")
            return 1
        entries = SmartLogViewer.get_logs(
            since=args.since, lines=args.lines or 500)
        fmt = "json" if args.path.endswith(".json") else "text"
        success = SmartLogViewer.export_logs(entries, args.path, format=fmt)
        icon = "✅" if success else "❌"
        _print(f"{icon} Exported {len(entries)} entries to {args.path}")
        return 0 if success else 1

    return 1


# ===== v16.0 Horizon commands =====

def cmd_service(args):
    """Handle service subcommand."""
    scope = ServiceScope.USER if args.user else ServiceScope.SYSTEM

    if args.action == "list":
        services = ServiceExplorer.list_services(
            scope=scope, filter_state=args.filter, search=args.search or ""
        )
        if _json_output:
            _output_json([s.to_dict() for s in services])
        else:
            _print(f"{'Name':<35} {'State':<12} {'Enabled':<10} Description")
            _print("─" * 90)
            for s in services:
                color = "✅" if s.is_running else "❌" if s.is_failed else "⬜"
                _print(
                    f"{color} {s.name:<33} {s.state.value:<12} {s.enabled:<10} {s.description[:40]}")
            _print(f"\nTotal: {len(services)} services")
        return 0

    elif args.action in ("start", "stop", "restart", "enable", "disable", "mask", "unmask"):
        name = args.name
        if not name:
            _print("❌ Service name required")
            return 1
        action_map = {
            "start": ServiceExplorer.start_service,
            "stop": ServiceExplorer.stop_service,
            "restart": ServiceExplorer.restart_service,
            "enable": ServiceExplorer.enable_service,
            "disable": ServiceExplorer.disable_service,
            "mask": ServiceExplorer.mask_service,
            "unmask": ServiceExplorer.unmask_service,
        }
        result = action_map[args.action](name, scope)
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        if _json_output:
            _output_json({"success": result.success,
                         "message": result.message})
        return 0 if result.success else 1

    elif args.action == "logs":
        name = args.name
        if not name:
            _print("❌ Service name required")
            return 1
        logs = ServiceExplorer.get_service_logs(name, scope, lines=args.lines)
        if _json_output:
            _output_json({"service": name, "logs": logs})
        else:
            _print(logs)
        return 0

    elif args.action == "status":
        name = args.name
        if not name:
            _print("❌ Service name required")
            return 1
        info = ServiceExplorer.get_service_details(name, scope)
        if _json_output:
            _output_json(info.to_dict())
        else:
            _print(f"Service: {info.name}")
            _print(f"Description: {info.description}")
            _print(f"State: {info.state.value} ({info.sub_state})")
            _print(f"Enabled: {info.enabled}")
            _print(f"Memory: {info.memory_human}")
            _print(f"PID: {info.main_pid}")
            _print(f"Active since: {info.active_enter}")
        return 0

    return 1


def cmd_package(args):
    """Handle package subcommand."""
    if args.action == "search":
        query = args.query or args.name
        if not query:
            _print("❌ Search query required")
            return 1
        results = PackageExplorer.search(query)
        if _json_output:
            _output_json([p.to_dict() for p in results])
        else:
            _print(f"{'Name':<40} {'Ver':<15} {'Source':<12} {'Inst':<6} Summary")
            _print("─" * 100)
            for p in results[:30]:
                inst = "✅" if p.installed else "  "
                _print(
                    f"{p.name:<40} {p.version:<15} {p.source:<12} {inst:<6} {p.summary[:35]}")
            _print(
                f"\nShowing {min(len(results), 30)} of {len(results)} results")
        return 0

    elif args.action == "install":
        name = args.name
        if not name:
            _print("❌ Package name required")
            return 1
        _print(f"🔄 Installing {name}...")
        result = PackageExplorer.install(name)
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        if _json_output:
            _output_json({"success": result.success,
                         "message": result.message})
        return 0 if result.success else 1

    elif args.action == "remove":
        name = args.name
        if not name:
            _print("❌ Package name required")
            return 1
        _print(f"🔄 Removing {name}...")
        result = PackageExplorer.remove(name)
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        if _json_output:
            _output_json({"success": result.success,
                         "message": result.message})
        return 0 if result.success else 1

    elif args.action == "list":
        source = args.source or "all"
        packages = PackageExplorer.list_installed(
            source=source, search=args.search or "")
        if _json_output:
            _output_json([p.to_dict() for p in packages])
        else:
            _print(f"Installed packages ({source}): {len(packages)}")
            for p in packages[:50]:
                _print(f"  {p.name:<40} {p.version:<20} [{p.source}]")
            if len(packages) > 50:
                _print(f"  ... and {len(packages) - 50} more")
        return 0

    elif args.action == "recent":
        packages = PackageExplorer.recently_installed(days=args.days)
        if _json_output:
            _output_json([p.to_dict() for p in packages])
        else:
            _print(
                f"Recently installed (last {args.days} days): {len(packages)}")
            for p in packages:
                _print(f"  {p.name:<40} {p.summary}")
        return 0

    return 1


def cmd_firewall(args):
    """Handle firewall subcommand."""
    if not FirewallManager.is_available():
        _print("❌ firewall-cmd not found. Install firewalld.")
        return 1

    if args.action == "status":
        info = FirewallManager.get_status()
        if _json_output:
            _output_json(info.to_dict())
        else:
            state = "🟢 Running" if info.running else "🔴 Stopped"
            _print(f"Firewall: {state}")
            _print(f"Default zone: {info.default_zone}")
            _print(f"Active zones: {info.active_zones}")
            _print(f"Open ports: {', '.join(info.ports) or 'none'}")
            _print(f"Services: {', '.join(info.services) or 'none'}")
            if info.rich_rules:
                _print("Rich rules:")
                for r in info.rich_rules:
                    _print(f"  {r}")
        return 0

    elif args.action == "ports":
        ports = FirewallManager.list_ports()
        if _json_output:
            _output_json({"ports": ports})
        else:
            if ports:
                _print("Open ports:")
                for p in ports:
                    _print(f"  {p}")
            else:
                _print("No ports open.")
        return 0

    elif args.action == "open-port":
        spec = args.spec
        if not spec:
            _print("❌ Port spec required (e.g. 8080/tcp)")
            return 1
        if "/" in spec:
            port, proto = spec.split("/", 1)
        else:
            port, proto = spec, "tcp"
        result = FirewallManager.open_port(port, proto)
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "close-port":
        spec = args.spec
        if not spec:
            _print("❌ Port spec required (e.g. 8080/tcp)")
            return 1
        if "/" in spec:
            port, proto = spec.split("/", 1)
        else:
            port, proto = spec, "tcp"
        result = FirewallManager.close_port(port, proto)
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action == "services":
        services = FirewallManager.list_services()
        if _json_output:
            _output_json({"services": services})
        else:
            _print("Allowed services:")
            for s in services:
                _print(f"  {s}")
        return 0

    elif args.action == "zones":
        zones = FirewallManager.get_zones()
        active = FirewallManager.get_active_zones()
        if _json_output:
            _output_json({"zones": zones, "active": active})
        else:
            _print("Available zones:")
            for z in zones:
                marker = " (active)" if z in active else ""
                _print(f"  {z}{marker}")
        return 0

    return 1


# ==================== v17.0 Atlas ====================


def cmd_bluetooth(args):
    """Handle bluetooth subcommand."""
    if args.action == "status":
        status = BluetoothManager.get_adapter_status()
        if _json_output:
            _output_json({
                "available": bool(status.adapter_name),
                "powered": status.powered,
                "discoverable": status.discoverable,
                "adapter_name": status.adapter_name,
                "adapter_address": status.adapter_address,
            })
        else:
            if not status.adapter_name:
                _print("❌ No Bluetooth adapter found")
                return 1
            power = "🟢 On" if status.powered else "🔴 Off"
            _print(f"Bluetooth: {power}")
            _print(
                f"Adapter: {status.adapter_name} ({status.adapter_address})")
            _print(f"Discoverable: {'yes' if status.discoverable else 'no'}")
        return 0

    elif args.action == "devices":
        paired_only = getattr(args, "paired", False)
        devices = BluetoothManager.list_devices(paired_only=paired_only)
        if _json_output:
            _output_json({"devices": [
                {"address": d.address, "name": d.name, "paired": d.paired,
                 "connected": d.connected, "trusted": d.trusted,
                 "device_type": d.device_type.value}
                for d in devices
            ]})
        else:
            if not devices:
                _print("No devices found.")
                return 0
            for d in devices:
                status_icons = []
                if d.connected:
                    status_icons.append("connected")
                if d.paired:
                    status_icons.append("paired")
                if d.trusted:
                    status_icons.append("trusted")
                status_str = ", ".join(
                    status_icons) if status_icons else "available"
                _print(f"  {d.name} ({d.address}) [{status_str}]")
        return 0

    elif args.action == "scan":
        timeout = getattr(args, "timeout", 10)
        _print(f"Scanning for {timeout} seconds...")
        devices = BluetoothManager.scan(timeout=timeout)
        if _json_output:
            _output_json({"devices": [
                {"address": d.address, "name": d.name,
                    "device_type": d.device_type.value}
                for d in devices
            ]})
        else:
            _print(f"Found {len(devices)} devices:")
            for d in devices:
                _print(f"  {d.name} ({d.address}) [{d.device_type.value}]")
        return 0

    elif args.action in ("power-on", "power-off"):
        result = BluetoothManager.power_on(
        ) if args.action == "power-on" else BluetoothManager.power_off()
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    elif args.action in ("connect", "disconnect", "pair", "unpair", "trust"):
        address = getattr(args, "address", None)
        if not address:
            _print("❌ Device address required")
            return 1
        action_map = {
            "connect": BluetoothManager.connect,
            "disconnect": BluetoothManager.disconnect,
            "pair": BluetoothManager.pair,
            "unpair": BluetoothManager.unpair,
            "trust": BluetoothManager.trust,
        }
        result = action_map[args.action](address)
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    return 1


# ==================== v18.0 Sentinel ====================

def cmd_agent(args):
    """Handle agent subcommand."""
    import time as time_mod

    from utils.agents import AgentRegistry

    registry = AgentRegistry.instance()

    if args.action == "list":
        agents = registry.list_agents()
        if _json_output:
            _output_json({"agents": [a.to_dict() for a in agents]})
        else:
            _print("═══════════════════════════════════════════")
            _print("   System Agents")
            _print("═══════════════════════════════════════════")
            if not agents:
                _print("\n(no agents found)")
            else:
                for a in agents:
                    state = registry.get_state(a.agent_id)
                    enabled = "✅" if a.enabled else "❌"
                    _print(f"\n  {enabled} {a.name} ({a.agent_id})")
                    _print(
                        f"      Type: {a.agent_type.value} | Status: {state.status.value}")
                    _print(
                        f"      Runs: {state.run_count} | Errors: {state.error_count}")
                    _print(f"      {a.description}")
        return 0

    elif args.action == "status":
        summary = registry.get_agent_summary()
        if _json_output:
            _output_json(summary)
        else:
            _print("═══════════════════════════════════════════")
            _print("   Agent Status")
            _print("═══════════════════════════════════════════")
            _print(f"\n  Total: {summary['total_agents']}")
            _print(f"  Enabled: {summary['enabled']}")
            _print(f"  Running: {summary['running']}")
            _print(f"  Errors: {summary['errors']}")
            _print(f"  Total Runs: {summary['total_runs']}")
        return 0

    elif args.action == "enable":
        if not args.agent_id:
            _print("❌ Agent ID required")
            return 1
        success = registry.enable_agent(args.agent_id)
        icon = "✅" if success else "❌"
        msg = f"Agent '{args.agent_id}' enabled" if success else f"Agent '{args.agent_id}' not found"
        _print(f"{icon} {msg}")
        if _json_output:
            _output_json({"success": success, "message": msg})
        return 0 if success else 1

    elif args.action == "disable":
        if not args.agent_id:
            _print("❌ Agent ID required")
            return 1
        success = registry.disable_agent(args.agent_id)
        icon = "✅" if success else "❌"
        msg = f"Agent '{args.agent_id}' disabled" if success else f"Agent '{args.agent_id}' not found"
        _print(f"{icon} {msg}")
        if _json_output:
            _output_json({"success": success, "message": msg})
        return 0 if success else 1

    elif args.action == "run":
        if not args.agent_id:
            _print("❌ Agent ID required")
            return 1
        from utils.agent_runner import AgentScheduler
        scheduler = AgentScheduler()
        _print(f"🔄 Running agent '{args.agent_id}'...")
        results = scheduler.run_agent_now(args.agent_id)
        if _json_output:
            _output_json({"results": [r.to_dict() for r in results]})
        else:
            for r in results:
                icon = "✅" if r.success else "❌"
                _print(f"  {icon} [{r.action_id}] {r.message}")
        return 0

    elif args.action == "create":
        goal = args.goal
        if not goal:
            _print("❌ Goal required (use --goal 'description')")
            return 1
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal(goal)
        config = plan.to_agent_config()
        registered = registry.register_agent(config)

        if _json_output:
            _output_json({
                "success": True,
                "agent_id": registered.agent_id,
                "name": registered.name,
                "plan": plan.to_dict(),
            })
        else:
            _print(
                f"✅ Created agent: {registered.name} (ID: {registered.agent_id})")
            _print(f"   Type: {plan.agent_type.value}")
            _print(f"   Confidence: {plan.confidence:.0%}")
            _print("   Steps:")
            for step in plan.steps:
                _print(f"     {step.step_number}. {step.description}")
            _print(
                f"\n   Agent starts in dry-run mode. Use 'agent enable {registered.agent_id}' to activate.")
        return 0

    elif args.action == "remove":
        if not args.agent_id:
            _print("❌ Agent ID required")
            return 1
        success = registry.remove_agent(args.agent_id)
        icon = "✅" if success else "❌"
        msg = f"Agent '{args.agent_id}' removed" if success else f"Cannot remove agent '{args.agent_id}' (built-in or not found)"
        _print(f"{icon} {msg}")
        if _json_output:
            _output_json({"success": success, "message": msg})
        return 0 if success else 1

    elif args.action == "logs":
        if not args.agent_id:
            # Show all recent activity
            activity = registry.get_recent_activity(limit=30)
            if _json_output:
                _output_json({"activity": activity})
            else:
                _print("═══════════════════════════════════════════")
                _print("   Recent Agent Activity")
                _print("═══════════════════════════════════════════")
                if not activity:
                    _print("\n(no activity)")
                else:
                    for item in activity:
                        ts = time_mod.strftime(
                            "%Y-%m-%d %H:%M:%S", time_mod.localtime(item["timestamp"]))
                        icon = "✅" if item["success"] else "❌"
                        _print(
                            f"  {ts} {icon} [{item['agent_name']}] {item['message'][:80]}")
        else:
            state = registry.get_state(args.agent_id)
            if _json_output:
                _output_json({"history": [h.to_dict() for h in state.history]})
            else:
                agent = registry.get_agent(args.agent_id)
                name = agent.name if agent else args.agent_id
                _print(
                    f"Agent: {name} (runs: {state.run_count}, errors: {state.error_count})")
                if not state.history:
                    _print("  (no history)")
                else:
                    for h in state.history[-20:]:
                        ts = time_mod.strftime(
                            "%H:%M:%S", time_mod.localtime(h.timestamp))
                        icon = "✅" if h.success else "❌"
                        _print(
                            f"  {ts} {icon} [{h.action_id}] {h.message[:80]}")
        return 0

    elif args.action == "templates":
        from utils.agent_planner import AgentPlanner
        templates = AgentPlanner.list_goal_templates()
        if _json_output:
            _output_json({"templates": templates})
        else:
            _print("═══════════════════════════════════════════")
            _print("   Agent Goal Templates")
            _print("═══════════════════════════════════════════")
            for t in templates:
                _print(f"\n  📋 {t['name']}")
                _print(f"     Goal: \"{t['goal']}\"")
                _print(f"     Type: {t['type']}")
                _print(f"     {t['description']}")
        return 0

    elif args.action == "notify":
        if not args.agent_id:
            # Show notification config for all agents
            agents = registry.list_agents()
            if _json_output:
                configs = {
                    a.agent_id: a.notification_config for a in agents
                }
                _output_json({"notification_configs": configs})
            else:
                _print("═══════════════════════════════════════════")
                _print("   Agent Notification Settings")
                _print("═══════════════════════════════════════════")
                for a in agents:
                    nc = a.notification_config
                    enabled = nc.get("enabled", False)
                    icon = "🔔" if enabled else "🔕"
                    _print(f"\n  {icon} {a.name} ({a.agent_id})")
                    _print(f"      Enabled: {enabled}")
                    if enabled:
                        _print(
                            f"      Min severity: {nc.get('min_severity', 'high')}")
                        _print(
                            f"      Channels: {', '.join(nc.get('channels', ['desktop', 'in_app']))}")
                        webhook = nc.get("webhook_url", "")
                        if webhook:
                            _print(f"      Webhook: {webhook}")
            return 0
        else:
            agent = registry.get_agent(args.agent_id)
            if not agent:
                _print(f"❌ Agent '{args.agent_id}' not found")
                return 1
            # Update notification config
            nc = dict(agent.notification_config)
            updated = False
            if args.webhook is not None:
                from utils.agent_notifications import AgentNotifier
                if args.webhook and not AgentNotifier.validate_webhook_url(args.webhook):
                    _print(
                        "❌ Invalid webhook URL (must start with http:// or https://)")
                    return 1
                nc["webhook_url"] = args.webhook or None
                if args.webhook:
                    if "webhook" not in nc.get("channels", []):
                        nc.setdefault(
                            "channels", ["desktop", "in_app"]).append("webhook")
                updated = True
            if args.min_severity is not None:
                valid = ["info", "low", "medium", "high", "critical"]
                if args.min_severity not in valid:
                    _print(
                        f"❌ Invalid severity. Choose from: {', '.join(valid)}")
                    return 1
                nc["min_severity"] = args.min_severity
                updated = True
            if not updated:
                # Toggle enable/disable
                nc["enabled"] = not nc.get("enabled", False)
            else:
                nc["enabled"] = True
            agent.notification_config = nc
            registry.save()
            icon = "🔔" if nc.get("enabled") else "🔕"
            _print(
                f"{icon} Notifications {'enabled' if nc.get('enabled') else 'disabled'} for '{agent.name}'")
            if _json_output:
                _output_json({"success": True, "notification_config": nc})
            return 0

    return 1


def cmd_storage(args):
    """Handle storage subcommand."""
    if args.action == "disks":
        disks = StorageManager.list_disks()
        if _json_output:
            _output_json({"disks": [
                {"name": d.name, "size": d.size, "type": d.device_type,
                 "model": d.model, "mountpoint": d.mountpoint,
                 "removable": d.rm}
                for d in disks
            ]})
        else:
            if not disks:
                _print("No disks found.")
                return 0
            _print("Physical Disks:")
            for d in disks:
                rm = " [removable]" if d.rm else ""
                _print(f"  {d.name}: {d.model or 'Unknown'} ({d.size}){rm}")
        return 0

    elif args.action == "mounts":
        mounts = StorageManager.list_mounts()
        if _json_output:
            _output_json({"mounts": [
                {"device": m.source, "mountpoint": m.target,
                 "fstype": m.fstype, "size": m.size,
                 "used": m.used, "available": m.avail,
                 "use_percent": m.use_percent}
                for m in mounts
            ]})
        else:
            _print("Mount Points:")
            for m in mounts:
                _print(f"  {m.source} -> {m.target} ({m.fstype}) "
                       f"[{m.used}/{m.size} = {m.use_percent}]")
        return 0

    elif args.action == "smart":
        device = getattr(args, "device", None)
        if not device:
            _print("❌ Device path required (e.g. /dev/sda)")
            return 1
        health = StorageManager.get_smart_health(device)
        if _json_output:
            _output_json({
                "device": device,
                "model": health.model,
                "serial": health.serial,
                "health": "PASSED" if health.health_passed else "FAILED",
                "temperature_c": health.temperature_c,
                "power_on_hours": health.power_on_hours,
                "reallocated_sectors": health.reallocated_sectors,
                "raw_output": health.raw_output,
            })
        else:
            _print(f"SMART Health for {device}:")
            _print(f"  Model: {health.model}")
            _print(f"  Serial: {health.serial}")
            _print(
                f"  Health: {'PASSED' if health.health_passed else 'FAILED'}")
            _print(f"  Temperature: {health.temperature_c}°C")
            _print(f"  Power-on hours: {health.power_on_hours}")
            _print(f"  Reallocated sectors: {health.reallocated_sectors}")
        return 0

    elif args.action == "usage":
        summary = StorageManager.get_usage_summary()
        if _json_output:
            _output_json(summary)
        else:
            _print(f"Total: {summary.get('total_size', 'N/A')}")
            _print(f"Used:  {summary.get('total_used', 'N/A')}")
            _print(f"Free:  {summary.get('total_available', 'N/A')}")
            _print(f"Disks: {summary.get('disk_count', 0)}")
            _print(f"Mounts: {summary.get('mount_count', 0)}")
        return 0

    elif args.action == "trim":
        result = StorageManager.trim_ssd()
        icon = "✅" if result.success else "❌"
        _print(f"{icon} {result.message}")
        return 0 if result.success else 1

    return 1


def cmd_audit_log(args):
    """Show recent audit log entries."""
    from utils.audit import AuditLogger

    audit = AuditLogger()
    count = getattr(args, "count", 20)
    entries = audit.get_recent(count)

    if _json_output:
        _output_json({"entries": entries, "count": len(
            entries), "log_path": str(audit.log_path)})
        return 0

    if not entries:
        _print("No audit log entries found.")
        _print(f"Log path: {audit.log_path}")
        return 0

    _print(f"📋 Recent Audit Log ({len(entries)} entries)")
    _print(f"   Log: {audit.log_path}")
    _print("─" * 72)

    for entry in entries:
        ts = entry.get("ts", "?")[:19].replace("T", " ")
        action = entry.get("action", "?")
        exit_code = entry.get("exit_code")
        dry_run = entry.get("dry_run", False)

        status = "DRY" if dry_run else (
            "✅" if exit_code == 0 else f"❌ ({exit_code})")
        _print(f"  {ts}  {action:30s}  {status}")

    return 0


# ==================== v37.0 Pinnacle ====================


def cmd_updates(args):
    """Handle smart updates subcommand."""
    from utils.update_manager import UpdateManager

    if args.action == "check":
        updates = UpdateManager.check_updates()
        if _json_output:
            _output_json([{"name": u.name, "old": u.old_version,
                           "new": u.new_version, "source": u.source} for u in updates])
        else:
            _print("═══════════════════════════════════════════")
            _print("   Available Updates")
            _print("═══════════════════════════════════════════")
            if not updates:
                _print("  System is up to date.")
            for u in updates:
                _print(f"  {u.name}: {u.old_version} → {u.new_version} ({u.source})")
        return 0

    elif args.action == "conflicts":
        conflicts = UpdateManager.preview_conflicts()
        if _json_output:
            _output_json([{"package": c.package, "type": c.conflict_type,
                           "desc": c.description} for c in conflicts])
        else:
            if not conflicts:
                _print("  No conflicts detected.")
            for c in conflicts:
                _print(f"  ⚠ {c.package}: {c.conflict_type} — {c.description}")
        return 0

    elif args.action == "schedule":
        time_str = getattr(args, "time", "02:00") or "02:00"
        scheduled = UpdateManager.schedule_update(time_str)
        cmds = UpdateManager.get_schedule_commands(scheduled)
        for binary, cmd_args, desc in cmds:
            run_operation((binary, cmd_args, desc))
        return 0

    elif args.action == "rollback":
        return 0 if run_operation(UpdateManager.rollback_last()) else 1

    elif args.action == "history":
        history = UpdateManager.get_update_history()
        if _json_output:
            _output_json([{"date": h.date, "name": h.name,
                           "version": h.new_version, "source": h.source} for h in history])
        else:
            for h in history:
                _print(f"  {h.date}: {h.name} → {h.new_version} ({h.source})")
        return 0

    return 1


def cmd_extension(args):
    """Handle extension management subcommand."""
    from utils.extension_manager import ExtensionManager

    if args.action == "list":
        extensions = ExtensionManager.list_installed()
        if _json_output:
            _output_json([{"uuid": e.uuid, "name": e.name, "enabled": e.enabled,
                           "desktop": e.desktop} for e in extensions])
        else:
            for e in extensions:
                status = "✅" if e.enabled else "❌"
                _print(f"  {status} {e.name or e.uuid} ({e.desktop})")
        return 0

    elif args.action == "install":
        if not args.uuid:
            _print("❌ Extension UUID required")
            return 1
        return 0 if run_operation(ExtensionManager.install(args.uuid)) else 1

    elif args.action == "remove":
        if not args.uuid:
            _print("❌ Extension UUID required")
            return 1
        return 0 if run_operation(ExtensionManager.remove(args.uuid)) else 1

    elif args.action == "enable":
        if not args.uuid:
            _print("❌ Extension UUID required")
            return 1
        return 0 if run_operation(ExtensionManager.enable(args.uuid)) else 1

    elif args.action == "disable":
        if not args.uuid:
            _print("❌ Extension UUID required")
            return 1
        return 0 if run_operation(ExtensionManager.disable(args.uuid)) else 1

    return 1


def cmd_flatpak_manage(args):
    """Handle Flatpak management subcommand."""
    from utils.flatpak_manager import FlatpakManager

    if args.action == "sizes":
        sizes = FlatpakManager.get_flatpak_sizes()
        if _json_output:
            _output_json([{"app_id": s.app_id, "size": s.size_str} for s in sizes])
        else:
            _print("═══════════════════════════════════════════")
            _print("   Flatpak Sizes")
            _print("═══════════════════════════════════════════")
            for s in sizes:
                _print(f"  {s.app_id}: {s.size_str}")
            _print(f"\n  Total: {FlatpakManager.get_total_size()}")
        return 0

    elif args.action == "permissions":
        all_perms = FlatpakManager.get_all_permissions()
        if _json_output:
            _output_json([{"app_id": a.app_id,
                           "permissions": [{"type": p.permission_type, "value": p.value}
                                           for p in a.permissions]}
                          for a in all_perms])
        else:
            for a in all_perms:
                _print(f"  {a.app_id}: {len(a.permissions)} permissions")
        return 0

    elif args.action == "orphans":
        orphans = FlatpakManager.find_orphan_runtimes()
        if _json_output:
            _output_json({"orphans": orphans})
        else:
            if not orphans:
                _print("  No orphan runtimes found.")
            for o in orphans:
                _print(f"  🗑 {o}")
        return 0

    elif args.action == "cleanup":
        return 0 if run_operation(FlatpakManager.cleanup_unused()) else 1

    return 1


def cmd_boot(args):
    """Handle boot configuration subcommand."""
    from utils.boot_config import BootConfigManager

    if args.action == "config":
        config = BootConfigManager.get_grub_config()
        if _json_output:
            _output_json({"default": config.default_entry, "timeout": config.timeout,
                          "theme": config.theme, "cmdline": config.cmdline_linux})
        else:
            _print(f"  Default: {config.default_entry}")
            _print(f"  Timeout: {config.timeout}s")
            _print(f"  Theme: {config.theme or 'none'}")
            _print(f"  Cmdline: {config.cmdline_linux}")
        return 0

    elif args.action == "kernels":
        kernels = BootConfigManager.list_kernels()
        if _json_output:
            _output_json([{"title": k.title, "version": k.version,
                           "default": k.is_default} for k in kernels])
        else:
            for k in kernels:
                marker = "→ " if k.is_default else "  "
                _print(f"  {marker}{k.title} ({k.version})")
        return 0

    elif args.action == "timeout":
        seconds = getattr(args, "seconds", None)
        if seconds is None:
            _print("❌ --seconds required")
            return 1
        return 0 if run_operation(BootConfigManager.set_timeout(seconds)) else 1

    elif args.action == "apply":
        return 0 if run_operation(BootConfigManager.apply_grub_changes()) else 1

    return 1


def cmd_display(args):
    """Handle display configuration subcommand."""
    from utils.wayland_display import WaylandDisplayManager

    if args.action == "list":
        displays = WaylandDisplayManager.get_displays()
        if _json_output:
            _output_json([{"name": d.name, "resolution": d.resolution,
                           "scale": d.scale, "refresh": d.refresh_rate,
                           "primary": d.primary} for d in displays])
        else:
            for d in displays:
                primary = " ★" if d.primary else ""
                _print(f"  {d.name}: {d.resolution} @{d.scale}x {d.refresh_rate}Hz{primary}")
        return 0

    elif args.action == "session":
        info = WaylandDisplayManager.get_session_info()
        if _json_output:
            _output_json(info)
        else:
            for k, v in info.items():
                _print(f"  {k}: {v}")
        return 0

    elif args.action == "fractional-on":
        return 0 if run_operation(WaylandDisplayManager.enable_fractional_scaling()) else 1

    elif args.action == "fractional-off":
        return 0 if run_operation(WaylandDisplayManager.disable_fractional_scaling()) else 1

    return 1


def cmd_backup(args):
    """Handle backup subcommand."""
    from utils.backup_wizard import BackupWizard

    if args.action == "detect":
        tool = BackupWizard.detect_backup_tool()
        available = BackupWizard.get_available_tools()
        if _json_output:
            _output_json({"active": tool, "available": available})
        else:
            _print(f"  Active tool: {tool}")
            _print(f"  Available: {', '.join(available)}")
        return 0

    elif args.action == "create":
        desc = getattr(args, "description", None) or "CLI backup"
        tool = getattr(args, "tool", None)
        return 0 if run_operation(BackupWizard.create_snapshot(tool=tool, description=desc)) else 1

    elif args.action == "list":
        tool = getattr(args, "tool", None)
        snapshots = BackupWizard.list_snapshots(tool=tool)
        if _json_output:
            _output_json([{"id": s.id, "date": s.date, "description": s.description,
                           "tool": s.tool} for s in snapshots])
        else:
            if not snapshots:
                _print("  No snapshots found.")
            for s in snapshots:
                _print(f"  [{s.tool}] {s.id}: {s.description} ({s.date})")
        return 0

    elif args.action == "restore":
        snap_id = getattr(args, "snapshot_id", None)
        if not snap_id:
            _print("❌ Snapshot ID required")
            return 1
        tool = getattr(args, "tool", None)
        return 0 if run_operation(BackupWizard.restore_snapshot(snap_id, tool=tool)) else 1

    elif args.action == "delete":
        snap_id = getattr(args, "snapshot_id", None)
        if not snap_id:
            _print("❌ Snapshot ID required")
            return 1
        tool = getattr(args, "tool", None)
        return 0 if run_operation(BackupWizard.delete_snapshot(snap_id, tool=tool)) else 1

    elif args.action == "status":
        status = BackupWizard.get_backup_status()
        if _json_output:
            _output_json(status)
        else:
            for k, v in status.items():
                _print(f"  {k}: {v}")
        return 0

    return 1


def main(argv: Optional[List[str]] = None):
    """Main CLI entrypoint."""
    global _json_output

    parser = argparse.ArgumentParser(
        prog="loofi",
        description=f"Loofi Fedora Tweaks v{__version__} \"{__version_codename__}\" - System management CLI"
    )
    parser.add_argument("-v", "--version", action="version",
                        version=f"{__version__} \"{__version_codename__}\"")
    parser.add_argument("--json", action="store_true",
                        help="Output in JSON format (for scripting)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Operation timeout in seconds (default: 300)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show commands without executing them (v35.0)")

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # Info command
    subparsers.add_parser("info", help="Show system information")

    # Health command
    subparsers.add_parser("health", help="System health check overview")

    # Disk command
    disk_parser = subparsers.add_parser("disk", help="Disk usage information")
    disk_parser.add_argument(
        "--details", action="store_true", help="Show large directories")

    # Process monitor command
    proc_parser = subparsers.add_parser("processes", help="Show top processes")
    proc_parser.add_argument("-n", "--count", type=int,
                             default=10, help="Number of processes to show")
    proc_parser.add_argument(
        "--sort", choices=["cpu", "memory"], default="cpu", help="Sort by")

    # Temperature command
    subparsers.add_parser("temperature", help="Show temperature readings")

    # Network monitor command
    netmon_parser = subparsers.add_parser(
        "netmon", help="Network interface monitoring")
    netmon_parser.add_argument(
        "--connections", action="store_true", help="Show active connections")

    # Cleanup subcommand
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="System cleanup operations")
    cleanup_parser.add_argument(
        "action",
        choices=["all", "dnf", "journal", "trim", "autoremove", "rpmdb"],
        default="all",
        nargs="?",
        help="Cleanup action to perform"
    )
    cleanup_parser.add_argument(
        "--days", type=int, default=14, help="Days to keep journal")

    # Tweak subcommand
    tweak_parser = subparsers.add_parser(
        "tweak", help="Hardware tweaks (power, audio, battery)")
    tweak_parser.add_argument(
        "action",
        choices=["power", "audio", "battery", "status"],
        help="Tweak action"
    )
    tweak_parser.add_argument("--profile", choices=["performance", "balanced", "power-saver"],
                              default="balanced", help="Power profile")
    tweak_parser.add_argument(
        "--limit", type=int, default=80, help="Battery limit (50-100)")

    # Advanced subcommand
    adv_parser = subparsers.add_parser(
        "advanced", help="Advanced optimizations")
    adv_parser.add_argument(
        "action",
        choices=["dnf-tweaks", "bbr", "gamemode", "swappiness"],
        help="Optimization action"
    )
    adv_parser.add_argument("--value", type=int,
                            default=10, help="Value for swappiness")

    # Network subcommand
    net_parser = subparsers.add_parser("network", help="Network configuration")
    net_parser.add_argument("action", choices=["dns"], help="Network action")
    net_parser.add_argument(
        "--provider",
        choices=["cloudflare", "google", "quad9", "opendns"],
        default="cloudflare",
        help="DNS provider",
    )

    # v10.0 new commands
    subparsers.add_parser(
        "doctor", help="Check system dependencies and diagnostics")
    subparsers.add_parser("hardware", help="Show detected hardware profile")

    # Plugin management
    plugin_parser = subparsers.add_parser("plugins", help="Manage plugins")
    plugin_parser.add_argument(
        "action", choices=["list", "enable", "disable"], help="Plugin action")
    plugin_parser.add_argument(
        "name", nargs="?", help="Plugin name for enable/disable")

    # v26.0 - Plugin marketplace
    marketplace_parser = subparsers.add_parser(
        "plugin-marketplace", help="Plugin marketplace operations")
    marketplace_parser.add_argument(
        "action",
        choices=["search", "install", "uninstall", "update", "info",
                 "list-installed", "reviews", "review-submit", "rating"],
        help="Marketplace action"
    )
    marketplace_parser.add_argument(
        "plugin", nargs="?", help="Plugin name or ID")
    marketplace_parser.add_argument("--category", help="Filter by category")
    marketplace_parser.add_argument("--query", help="Search query")
    marketplace_parser.add_argument(
        "--limit", type=int, default=20, help="Review fetch limit (for reviews)")
    marketplace_parser.add_argument(
        "--offset", type=int, default=0, help="Review fetch offset (for reviews)")
    marketplace_parser.add_argument(
        "--reviewer", help="Reviewer name (for review-submit)")
    marketplace_parser.add_argument(
        "--rating", type=int, help="Rating 1-5 (for review-submit)")
    marketplace_parser.add_argument(
        "--title", help="Review title (for review-submit)")
    marketplace_parser.add_argument(
        "--comment", help="Review comment (for review-submit)")
    marketplace_parser.add_argument(
        "--accept-permissions", action="store_true",
        help="Auto-accept permissions (non-interactive)")

    # Support bundle
    subparsers.add_parser("support-bundle", help="Export support bundle ZIP")

    # ==================== v11.5 / v12.0 subparsers ====================

    # VM management
    vm_parser = subparsers.add_parser("vm", help="Virtual machine management")
    vm_parser.add_argument(
        "action", choices=["list", "status", "start", "stop"], help="VM action")
    vm_parser.add_argument(
        "name", nargs="?", help="VM name (for status/start/stop)")

    # VFIO GPU passthrough
    vfio_parser = subparsers.add_parser(
        "vfio", help="GPU passthrough assistant")
    vfio_parser.add_argument(
        "action", choices=["check", "gpus", "plan"], help="VFIO action")

    # Mesh networking
    mesh_parser = subparsers.add_parser(
        "mesh", help="Loofi Link mesh networking")
    mesh_parser.add_argument(
        "action", choices=["discover", "status"], help="Mesh action")

    # State Teleport
    teleport_parser = subparsers.add_parser(
        "teleport", help="State Teleport workspace capture/restore")
    teleport_parser.add_argument(
        "action", choices=["capture", "list", "restore"], help="Teleport action")
    teleport_parser.add_argument("--path", help="Workspace path for capture")
    teleport_parser.add_argument(
        "--target", default="unknown", help="Target device name")
    teleport_parser.add_argument(
        "package_id", nargs="?", help="Package ID for restore")

    # AI Models
    ai_models_parser = subparsers.add_parser(
        "ai-models", help="AI model management")
    ai_models_parser.add_argument(
        "action", choices=["list", "recommend"], help="AI models action")

    # Preset management
    preset_parser = subparsers.add_parser(
        "preset", help="Manage system presets")
    preset_parser.add_argument(
        "action", choices=["list", "apply", "export"], help="Preset action")
    preset_parser.add_argument(
        "name", nargs="?", help="Preset name (for apply/export)")
    preset_parser.add_argument(
        "path", nargs="?", help="Export path (for export)")

    # Focus mode
    focus_parser = subparsers.add_parser(
        "focus-mode", help="Focus mode distraction blocking")
    focus_parser.add_argument(
        "action", choices=["on", "off", "status"], help="Focus mode action")
    focus_parser.add_argument(
        "--profile", default="default", help="Profile to use (default: default)")

    # Security audit
    subparsers.add_parser(
        "security-audit", help="Run security audit and show score")

    # v13.0 Nexus Update - Profile management
    profile_parser = subparsers.add_parser(
        "profile", help="System profile management")
    profile_parser.add_argument(
        "action",
        choices=["list", "apply", "create", "delete",
                 "export", "import", "export-all", "import-all"],
        help="Profile action",
    )
    profile_parser.add_argument(
        "name", nargs="?", help="Profile name (for apply/create/delete/export)")
    profile_parser.add_argument(
        "path", nargs="?", help="Import/export file path")
    profile_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing custom profiles on import")
    profile_parser.add_argument("--no-snapshot", action="store_true",
                                help="Skip snapshot creation when applying profiles")
    profile_parser.add_argument("--include-builtins", action="store_true",
                                help="Include built-in profiles in export-all bundle")

    # v13.0 Nexus Update - Health history
    health_history_parser = subparsers.add_parser(
        "health-history", help="Health timeline metrics")
    health_history_parser.add_argument("action", choices=["show", "record", "export", "prune"],
                                       help="Health history action")
    health_history_parser.add_argument(
        "path", nargs="?", help="Export path (for export)")

    # ==================== v15.0 Nebula subparsers ====================

    # Performance auto-tuner
    tuner_parser = subparsers.add_parser(
        "tuner", help="Performance auto-tuner")
    tuner_parser.add_argument("action", choices=["analyze", "apply", "history"],
                              help="Tuner action")

    # Snapshot management
    snapshot_parser = subparsers.add_parser(
        "snapshot", help="System snapshot management")
    snapshot_parser.add_argument("action", choices=["list", "create", "delete", "backends"],
                                 help="Snapshot action")
    snapshot_parser.add_argument("--label", help="Snapshot label (for create)")
    snapshot_parser.add_argument(
        "snapshot_id", nargs="?", help="Snapshot ID (for delete)")

    # Smart log viewer
    logs_parser = subparsers.add_parser(
        "logs", help="Smart log viewer with pattern detection")
    logs_parser.add_argument("action", choices=["show", "errors", "export"],
                             help="Logs action")
    logs_parser.add_argument("--unit", help="Filter by systemd unit")
    logs_parser.add_argument("--priority", type=int,
                             help="Max priority level (0-7)")
    logs_parser.add_argument(
        "--since", help="Time filter (e.g. '1h ago', '2024-01-01')")
    logs_parser.add_argument(
        "--lines", type=int, default=100, help="Number of lines")
    logs_parser.add_argument(
        "path", nargs="?", help="Export path (for export)")

    # ==================== v16.0 Horizon subparsers ====================

    # Service management
    service_parser = subparsers.add_parser(
        "service", help="Systemd service management")
    service_parser.add_argument(
        "action",
        choices=["list", "start", "stop", "restart", "enable", "disable",
                 "mask", "unmask", "logs", "status"],
        help="Service action"
    )
    service_parser.add_argument("name", nargs="?", help="Service name")
    service_parser.add_argument(
        "--user", action="store_true", help="User scope (default: system)")
    service_parser.add_argument("--filter", choices=["active", "inactive", "failed"],
                                help="Filter by state (for list)")
    service_parser.add_argument("--search", help="Search filter (for list)")
    service_parser.add_argument(
        "--lines", type=int, default=50, help="Log lines (for logs)")

    # Package management
    package_parser = subparsers.add_parser(
        "package", help="Package search and management")
    package_parser.add_argument(
        "action",
        choices=["search", "install", "remove", "list", "recent"],
        help="Package action"
    )
    package_parser.add_argument(
        "name", nargs="?", help="Package name (for install/remove)")
    package_parser.add_argument("--query", help="Search query (for search)")
    package_parser.add_argument("--source", choices=["dnf", "flatpak", "all"],
                                help="Package source filter")
    package_parser.add_argument("--search", help="Filter installed packages")
    package_parser.add_argument(
        "--days", type=int, default=30, help="Days for recent")

    # Firewall management
    firewall_parser = subparsers.add_parser(
        "firewall", help="Firewall management")
    firewall_parser.add_argument(
        "action",
        choices=["status", "ports", "open-port",
                 "close-port", "services", "zones"],
        help="Firewall action"
    )
    firewall_parser.add_argument(
        "spec", nargs="?", help="Port spec (e.g. 8080/tcp)")

    # v17.0 Atlas - Bluetooth management
    bt_parser = subparsers.add_parser("bluetooth", help="Bluetooth management")
    bt_parser.add_argument(
        "action",
        choices=["status", "devices", "scan", "power-on", "power-off",
                 "connect", "disconnect", "pair", "unpair", "trust"],
        help="Bluetooth action"
    )
    bt_parser.add_argument("address", nargs="?", help="Device MAC address")
    bt_parser.add_argument(
        "--paired", action="store_true", help="Show paired only")
    bt_parser.add_argument("--timeout", type=int,
                           default=10, help="Scan timeout")

    # v17.0 Atlas - Storage management
    storage_parser = subparsers.add_parser(
        "storage", help="Storage & disk management")
    storage_parser.add_argument(
        "action",
        choices=["disks", "mounts", "smart", "usage", "trim"],
        help="Storage action"
    )
    storage_parser.add_argument(
        "device", nargs="?", help="Device path (e.g. /dev/sda)")

    update_parser = subparsers.add_parser(
        "self-update", help="Check/download verified Loofi updates")
    update_parser.add_argument(
        "action", choices=["check", "run"], default="run", nargs="?")
    update_parser.add_argument(
        "--channel", choices=["auto", "rpm", "flatpak", "appimage"], default="auto")
    update_parser.add_argument(
        "--download-dir", default="~/.cache/loofi-fedora-tweaks/updates")
    update_parser.add_argument("--timeout", type=int, default=30)
    update_parser.add_argument("--no-cache", action="store_true")
    update_parser.add_argument("--checksum", default="")
    update_parser.add_argument("--signature-path")
    update_parser.add_argument("--public-key-path")

    # v18.0 Sentinel - Agent management
    agent_parser = subparsers.add_parser(
        "agent", help="Autonomous system agent management")
    agent_parser.add_argument(
        "action",
        choices=["list", "status", "enable", "disable", "run", "create",
                 "remove", "logs", "templates", "notify"],
        help="Agent action"
    )
    agent_parser.add_argument(
        "agent_id", nargs="?", help="Agent ID (for enable/disable/run/remove/logs/notify)")
    agent_parser.add_argument(
        "--goal", help="Natural language goal (for create)")
    agent_parser.add_argument(
        "--webhook", help="Webhook URL for notifications (for notify)")
    agent_parser.add_argument(
        "--min-severity", help="Minimum severity to notify: info/low/medium/high/critical")

    # v35.0 Fortress - Audit log viewer
    audit_parser = subparsers.add_parser(
        "audit-log", help="View recent audit log entries")
    audit_parser.add_argument(
        "--count", type=int, default=20, help="Number of entries to show (default: 20)")

    # v37.0 Pinnacle - Smart Updates
    updates_parser = subparsers.add_parser(
        "updates", help="Smart update management")
    updates_parser.add_argument(
        "action", choices=["check", "conflicts", "schedule", "rollback", "history"],
        help="Update action to perform")
    updates_parser.add_argument(
        "--time", default="02:00", help="Schedule time (HH:MM, default: 02:00)")

    # v37.0 Pinnacle - Extensions
    ext_parser = subparsers.add_parser(
        "extension", help="Desktop extension management")
    ext_parser.add_argument(
        "action", choices=["list", "install", "remove", "enable", "disable"],
        help="Extension action")
    ext_parser.add_argument(
        "--uuid", help="Extension UUID for install/remove/enable/disable")

    # v37.0 Pinnacle - Flatpak Manager
    flatpak_parser = subparsers.add_parser(
        "flatpak-manage", help="Flatpak management tools")
    flatpak_parser.add_argument(
        "action", choices=["sizes", "permissions", "orphans", "cleanup"],
        help="Flatpak action")

    # v37.0 Pinnacle - Boot Configuration
    boot_parser = subparsers.add_parser(
        "boot", help="Boot configuration management")
    boot_parser.add_argument(
        "action", choices=["config", "kernels", "timeout", "apply"],
        help="Boot action")
    boot_parser.add_argument(
        "--seconds", type=int, help="Timeout in seconds (for timeout action)")

    # v37.0 Pinnacle - Display
    display_parser = subparsers.add_parser(
        "display", help="Display and Wayland configuration")
    display_parser.add_argument(
        "action", choices=["list", "session", "fractional-on", "fractional-off"],
        help="Display action")

    # v37.0 Pinnacle - Backup
    backup_parser = subparsers.add_parser(
        "backup", help="Snapshot backup management")
    backup_parser.add_argument(
        "action", choices=["detect", "create", "list", "restore", "delete", "status"],
        help="Backup action")
    backup_parser.add_argument(
        "--tool", help="Backup tool (timeshift/snapper)")
    backup_parser.add_argument(
        "--description", help="Snapshot description (for create)")
    backup_parser.add_argument(
        "--snapshot-id", help="Snapshot ID (for restore/delete)")

    args = parser.parse_args(argv)

    # Set JSON mode
    _json_output = getattr(args, "json", False)

    # Set operation timeout from --timeout flag
    _operation_timeout = getattr(args, "timeout", 300)  # noqa: F841

    # Set dry-run mode from --dry-run flag
    _dry_run = getattr(args, "dry_run", False)  # noqa: F841

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "info": cmd_info,
        "health": cmd_health,
        "disk": cmd_disk,
        "processes": cmd_processes,
        "temperature": cmd_temperature,
        "netmon": cmd_netmon,
        "cleanup": cmd_cleanup,
        "tweak": cmd_tweak,
        "advanced": cmd_advanced,
        "network": cmd_network,
        "doctor": cmd_doctor,
        "hardware": cmd_hardware,
        "plugins": cmd_plugins,
        "plugin-marketplace": cmd_plugin_marketplace,
        "support-bundle": cmd_support_bundle,
        # v11.5 / v12.0
        "vm": cmd_vm,
        "vfio": cmd_vfio,
        "mesh": cmd_mesh,
        "teleport": cmd_teleport,
        "ai-models": cmd_ai_models,
        # New commands
        "preset": cmd_preset,
        "focus-mode": cmd_focus_mode,
        "security-audit": cmd_security_audit,
        # v13.0 Nexus Update
        "profile": cmd_profile,
        "health-history": cmd_health_history,
        # v15.0 Nebula
        "tuner": cmd_tuner,
        "snapshot": cmd_snapshot,
        "logs": cmd_logs,
        # v16.0 Horizon
        "service": cmd_service,
        "package": cmd_package,
        "firewall": cmd_firewall,
        # v17.0 Atlas
        "bluetooth": cmd_bluetooth,
        "storage": cmd_storage,
        # v18.0 Sentinel
        "agent": cmd_agent,
        "self-update": cmd_self_update,
        # v35.0 Fortress
        "audit-log": cmd_audit_log,
        # v37.0 Pinnacle
        "updates": cmd_updates,
        "extension": cmd_extension,
        "flatpak-manage": cmd_flatpak_manage,
        "boot": cmd_boot,
        "display": cmd_display,
        "backup": cmd_backup,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
