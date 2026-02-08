"""
Loofi CLI - Command-line interface for Loofi Fedora Tweaks.
Enables headless operation and scripting.
v12.0.0 "Sovereign Update"
"""

import sys
import os
import argparse
import subprocess
import json as json_module
import shutil
from typing import List, Optional

# Add parent to path for imports
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.operations import (
    CleanupOps, TweakOps, AdvancedOps, NetworkOps,
    OperationResult, CLI_COMMANDS
)
from utils.system import SystemManager
from utils.disk import DiskManager
from utils.monitor import SystemMonitor
from utils.plugin_base import PluginLoader
from utils.performance import PerformanceCollector
from utils.processes import ProcessManager
from utils.temperature import TemperatureManager
from utils.network_monitor import NetworkMonitor
from utils.journal import JournalManager

from version import __version__, __version_codename__

# Global flag for JSON output
_json_output = False


def _print(text):
    """Print text (suppressed in JSON mode)."""
    if not _json_output:
        print(text)


def _output_json(data):
    """Output JSON data and exit."""
    print(json_module.dumps(data, indent=2, default=str))


def run_operation(op_result):
    """Execute an operation tuple (cmd, args, description)."""
    cmd, args, desc = op_result
    _print(f"🔄 {desc}")

    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True, text=True, check=False
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
            _print(f"💻 System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora")
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
        _print(f"🖥️  System: {'Atomic' if is_atomic else 'Traditional'} Fedora")
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
            mem_icon = "🟢" if health.memory_status == "ok" else ("🟡" if health.memory_status == "warning" else "🔴")
            _print(f"{mem_icon} Memory: {health.memory.used_human} / {health.memory.total_human} ({health.memory.percent_used}%)")
        else:
            _print("⚪ Memory: Unable to read")

        if health.cpu:
            cpu_icon = "🟢" if health.cpu_status == "ok" else ("🟡" if health.cpu_status == "warning" else "🔴")
            _print(f"{cpu_icon} CPU Load: {health.cpu.load_1min} / {health.cpu.load_5min} / {health.cpu.load_15min} ({health.cpu.core_count} cores, {health.cpu.load_percent}%)")
        else:
            _print("⚪ CPU: Unable to read")

        disk_level, disk_msg = DiskManager.check_disk_health("/")
        disk_icon = "🟢" if disk_level == "ok" else ("🟡" if disk_level == "warning" else "🔴")
        _print(f"{disk_icon} {disk_msg}")
        _print(f"⚡ Power Profile: {TweakOps.get_power_profile()}")
        _print(f"💻 System: {'Atomic' if SystemManager.is_atomic() else 'Traditional'} Fedora ({SystemManager.get_variant_name()})")

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
            icon = "🟢" if level == "ok" else ("🟡" if level == "warning" else "🔴")
            _print(f"\n{icon} Root (/)")
            _print(f"   Total: {usage.total_human}")
            _print(f"   Used:  {usage.used_human} ({usage.percent_used}%)")
            _print(f"   Free:  {usage.free_human}")
        else:
            _print("❌ Unable to read root filesystem")

        home_usage = DiskManager.get_disk_usage(os.path.expanduser("~"))
        if home_usage and home_usage.mount_point != "/":
            level, _ = DiskManager.check_disk_health(home_usage.mount_point)
            icon = "🟢" if level == "ok" else ("🟡" if level == "warning" else "🔴")
            _print(f"\n{icon} Home ({home_usage.mount_point})")
            _print(f"   Total: {home_usage.total_human}")
            _print(f"   Used:  {home_usage.used_human} ({home_usage.percent_used}%)")
            _print(f"   Free:  {home_usage.free_human}")

        if getattr(args, "details", False):
            home_dir = os.path.expanduser("~")
            _print(f"\n📂 Largest directories in {home_dir}:")
            large_dirs = DiskManager.find_large_directories(home_dir, max_depth=2, top_n=5)
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
        _print(f"\n📊 Total: {counts['total']} | Running: {counts['running']} | Sleeping: {counts['sleeping']} | Zombie: {counts['zombie']}")
        _print(f"\n🔍 Top {n} by {'Memory' if sort_by == 'memory' else 'CPU'}:")
        _print(f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'Memory':>10}  {'User':<12}  {'Name'}")
        _print("─" * 70)
        for p in processes:
            mem_human = ProcessManager.bytes_to_human(p.memory_bytes)
            _print(f"{p.pid:>7}  {p.cpu_percent:>5.1f}%  {p.memory_percent:>5.1f}%  {mem_human:>10}  {p.user:<12}  {p.name}")

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
            _print(f"\n📊 Summary: avg {avg_temp:.1f}°C | max {hottest.current:.1f}°C ({hottest.label})")

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
            _print(f"   RX: {NetworkMonitor.bytes_to_human(iface.bytes_recv)}  TX: {NetworkMonitor.bytes_to_human(iface.bytes_sent)}")
            if iface.recv_rate > 0 or iface.send_rate > 0:
                _print(f"   Rate: ↓{NetworkMonitor.bytes_to_human(int(iface.recv_rate))}/s  ↑{NetworkMonitor.bytes_to_human(int(iface.send_rate))}/s")

        summary = NetworkMonitor.get_bandwidth_summary()
        _print(f"\n📊 Total: ↓{NetworkMonitor.bytes_to_human(summary['total_recv'])} ↑{NetworkMonitor.bytes_to_human(summary['total_sent'])}")

        if getattr(args, "connections", False):
            connections = NetworkMonitor.get_active_connections()
            if connections:
                _print(f"\n🔗 Active Connections ({len(connections)}):")
                _print(f"{'Proto':<6} {'Local':>21} {'Remote':>21} {'State':<14} {'Process'}")
                _print("─" * 80)
                for conn in connections[:20]:
                    local = f"{conn.local_addr}:{conn.local_port}"
                    remote = f"{conn.remote_addr}:{conn.remote_port}" if conn.remote_addr != "0.0.0.0" else "*"
                    _print(f"{conn.protocol:<6} {local:>21} {remote:>21} {conn.state:<14} {conn.process_name}")

    return 0


def cmd_doctor(args):
    """Run system diagnostics and check dependencies."""
    critical_tools = ["dnf", "pkexec", "systemctl", "flatpak"]
    optional_tools = ["fwupdmgr", "timeshift", "nbfc", "firejail", "ollama", "distrobox", "podman"]

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
            _print("\n🔴 Some critical tools are missing. Install them for full functionality.")

    return 0 if all_ok else 1


def cmd_hardware(args):
    """Show detected hardware profile."""
    from utils.hardware_profiles import detect_hardware_profile, get_profile_label

    key, profile = detect_hardware_profile()

    if _json_output:
        _output_json({"profile_key": key, "profile": profile})
    else:
        _print("═══════════════════════════════════════════")
        _print("   Hardware Profile")
        _print("═══════════════════════════════════════════")
        _print(f"\n🖥️  Detected: {profile['label']}")
        _print(f"   Battery Limit:    {'✅' if profile.get('battery_limit') else '❌'}")
        _print(f"   Fan Control:      {'✅' if profile.get('nbfc') else '❌'}")
        _print(f"   Fingerprint:      {'✅' if profile.get('fingerprint') else '❌'}")
        _print(f"   Power Profiles:   {'✅' if profile.get('power_profiles') else '❌'}")
        thermal = profile.get('thermal_management', 'None')
        _print(f"   Thermal Driver:   {thermal or 'Generic'}")

    return 0


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
            _print(f"{'✅' if enabled else '❌'} {args.name} {'enabled' if enabled else 'disabled'}")
        return 0

    return 1


def cmd_support_bundle(args):
    """Export support bundle ZIP."""
    result = JournalManager.export_support_bundle()
    if _json_output:
        _output_json({"success": result.success, "message": result.message, "data": result.data})
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
                    _print(f"  {icon} {vm.name} [{vm.state}]  RAM: {vm.memory_mb}MB  vCPUs: {vm.vcpus}")
        return 0

    elif args.action == "status":
        status = VMManager.get_vm_info(args.name)
        if _json_output:
            _output_json(status if isinstance(status, dict) else {"error": "VM not found"})
        else:
            if status:
                _print(f"VM: {status.get('name', args.name)} [{status.get('state', 'unknown')}]")
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
                    _print(f"    IDs: {gpu.get('vendor_id', '?')}:{gpu.get('device_id', '?')}")
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
                    _print(f"  📦 {pkg['package_id'][:8]}... from {pkg['source_device']}")
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
            _output_json({"installed": installed, "recommended": list(recommended.keys())})
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


def main(argv: Optional[List[str]] = None):
    """Main CLI entrypoint."""
    global _json_output

    parser = argparse.ArgumentParser(
        prog="loofi",
        description=f"Loofi Fedora Tweaks v{__version__} \"{__version_codename__}\" - System management CLI"
    )
    parser.add_argument("-v", "--version", action="version", version=f"{__version__} \"{__version_codename__}\"")
    parser.add_argument("--json", action="store_true", help="Output in JSON format (for scripting)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Info command
    subparsers.add_parser("info", help="Show system information")

    # Health command
    subparsers.add_parser("health", help="System health check overview")

    # Disk command
    disk_parser = subparsers.add_parser("disk", help="Disk usage information")
    disk_parser.add_argument("--details", action="store_true", help="Show large directories")

    # Process monitor command
    proc_parser = subparsers.add_parser("processes", help="Show top processes")
    proc_parser.add_argument("-n", "--count", type=int, default=10, help="Number of processes to show")
    proc_parser.add_argument("--sort", choices=["cpu", "memory"], default="cpu", help="Sort by")

    # Temperature command
    subparsers.add_parser("temperature", help="Show temperature readings")

    # Network monitor command
    netmon_parser = subparsers.add_parser("netmon", help="Network interface monitoring")
    netmon_parser.add_argument("--connections", action="store_true", help="Show active connections")

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
    tweak_parser = subparsers.add_parser("tweak", help="Hardware tweaks (power, audio, battery)")
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

    # v10.0 new commands
    subparsers.add_parser("doctor", help="Check system dependencies and diagnostics")
    subparsers.add_parser("hardware", help="Show detected hardware profile")

    # Plugin management
    plugin_parser = subparsers.add_parser("plugins", help="Manage plugins")
    plugin_parser.add_argument("action", choices=["list", "enable", "disable"], help="Plugin action")
    plugin_parser.add_argument("name", nargs="?", help="Plugin name for enable/disable")

    # Support bundle
    subparsers.add_parser("support-bundle", help="Export support bundle ZIP")

    # ==================== v11.5 / v12.0 subparsers ====================

    # VM management
    vm_parser = subparsers.add_parser("vm", help="Virtual machine management")
    vm_parser.add_argument("action", choices=["list", "status", "start", "stop"], help="VM action")
    vm_parser.add_argument("name", nargs="?", help="VM name (for status/start/stop)")

    # VFIO GPU passthrough
    vfio_parser = subparsers.add_parser("vfio", help="GPU passthrough assistant")
    vfio_parser.add_argument("action", choices=["check", "gpus", "plan"], help="VFIO action")

    # Mesh networking
    mesh_parser = subparsers.add_parser("mesh", help="Loofi Link mesh networking")
    mesh_parser.add_argument("action", choices=["discover", "status"], help="Mesh action")

    # State Teleport
    teleport_parser = subparsers.add_parser("teleport", help="State Teleport workspace capture/restore")
    teleport_parser.add_argument("action", choices=["capture", "list", "restore"], help="Teleport action")
    teleport_parser.add_argument("--path", help="Workspace path for capture")
    teleport_parser.add_argument("--target", default="unknown", help="Target device name")
    teleport_parser.add_argument("package_id", nargs="?", help="Package ID for restore")

    # AI Models
    ai_models_parser = subparsers.add_parser("ai-models", help="AI model management")
    ai_models_parser.add_argument("action", choices=["list", "recommend"], help="AI models action")

    args = parser.parse_args(argv)

    # Set JSON mode
    _json_output = getattr(args, "json", False)

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
        "support-bundle": cmd_support_bundle,
        # v11.5 / v12.0
        "vm": cmd_vm,
        "vfio": cmd_vfio,
        "mesh": cmd_mesh,
        "teleport": cmd_teleport,
        "ai-models": cmd_ai_models,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
