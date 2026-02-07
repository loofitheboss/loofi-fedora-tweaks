"""
Pulse - Event-driven automation system.
Listens for DBus signals (Power, Network, Monitor) and emits PyQt signals.
Runs in a separate thread to avoid freezing the GUI.
"""

import os
import subprocess
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QThread

# DBus imports with graceful fallback
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    dbus = None
    GLib = None


class PowerState(Enum):
    """Power source states."""
    AC = "ac"
    BATTERY = "battery"
    UNKNOWN = "unknown"


class NetworkState(Enum):
    """Network connection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"


@dataclass
class MonitorInfo:
    """Information about a connected monitor."""
    name: str
    width: int
    height: int
    is_primary: bool
    is_ultrawide: bool  # Aspect ratio > 2.0


class SystemPulse(QObject):
    """
    Event-driven automation core.
    Listens for system events via DBus and emits PyQt signals.
    Thread-safe for GUI integration.
    """
    
    # Power signals
    power_state_changed = pyqtSignal(str)  # PowerState value
    battery_level_changed = pyqtSignal(int)  # 0-100
    
    # Network signals
    network_state_changed = pyqtSignal(str)  # NetworkState value
    wifi_ssid_changed = pyqtSignal(str)  # SSID name
    vpn_state_changed = pyqtSignal(bool)  # Connected/Disconnected
    
    # Monitor signals
    monitor_connected = pyqtSignal(dict)  # MonitorInfo as dict
    monitor_disconnected = pyqtSignal(str)  # Monitor name
    monitor_count_changed = pyqtSignal(int)  # Number of monitors
    
    # Generic event signal for extensibility
    event_triggered = pyqtSignal(str, dict)  # event_name, event_data
    
    def __init__(self):
        super().__init__()
        self._loop: Optional[Any] = None
        self._running = False
        self._system_bus = None
        self._last_power_state: Optional[str] = None
        self._last_network_state: Optional[str] = None
        self._last_monitor_count: int = 0
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if DBus is available on this system."""
        return DBUS_AVAILABLE
    
    def start(self):
        """Start the DBus listener loop. Call from QThread."""
        if not DBUS_AVAILABLE:
            print("[Pulse] DBus not available, falling back to polling")
            self._run_polling_fallback()
            return
        
        try:
            DBusGMainLoop(set_as_default=True)
            self._system_bus = dbus.SystemBus()
            self._running = True
            
            # Register signal handlers
            self._register_upower_signals()
            self._register_networkmanager_signals()
            self._register_monitor_signals()
            
            print("[Pulse] Event listeners registered, starting main loop")
            
            # Start GLib main loop
            self._loop = GLib.MainLoop()
            self._loop.run()
            
        except Exception as e:
            print(f"[Pulse] Error starting DBus listener: {e}")
            self._run_polling_fallback()
    
    def stop(self):
        """Stop the DBus listener loop."""
        self._running = False
        if self._loop:
            self._loop.quit()
            
    # -------------------------------------------------------------------------
    # UPower (Power Management)
    # -------------------------------------------------------------------------
    
    def _register_upower_signals(self):
        """Register for UPower property change signals."""
        if not self._system_bus:
            return
            
        try:
            self._system_bus.add_signal_receiver(
                self._on_upower_properties_changed,
                bus_name="org.freedesktop.UPower",
                path="/org/freedesktop/UPower",
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged"
            )
            
            # Also watch battery level changes
            self._system_bus.add_signal_receiver(
                self._on_battery_properties_changed,
                bus_name="org.freedesktop.UPower",
                path="/org/freedesktop/UPower/devices/DisplayDevice",
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged"
            )
            
            print("[Pulse] UPower signals registered")
        except dbus.exceptions.DBusException as e:
            print(f"[Pulse] Could not register UPower signals: {e}")
    
    def _on_upower_properties_changed(self, interface, changed, invalidated):
        """Handle UPower property changes."""
        if "OnBattery" in changed:
            on_battery = bool(changed["OnBattery"])
            new_state = PowerState.BATTERY.value if on_battery else PowerState.AC.value
            
            if new_state != self._last_power_state:
                self._last_power_state = new_state
                print(f"[Pulse] Power state changed: {new_state}")
                self.power_state_changed.emit(new_state)
                self.event_triggered.emit("power_state", {"state": new_state})
    
    def _on_battery_properties_changed(self, interface, changed, invalidated):
        """Handle battery property changes."""
        if "Percentage" in changed:
            level = int(changed["Percentage"])
            self.battery_level_changed.emit(level)
    
    @classmethod
    def get_power_state(cls) -> str:
        """
        Get current power state (non-reactive, for polling fallback).
        
        Returns:
            PowerState value as string
        """
        try:
            # Try upower CLI first
            result = subprocess.run(
                ["upower", "-i", "/org/freedesktop/UPower/devices/line_power_AC0"],
                capture_output=True, text=True, check=False, timeout=5
            )
            if "online: yes" in result.stdout.lower():
                return PowerState.AC.value
            elif "online: no" in result.stdout.lower():
                return PowerState.BATTERY.value
        except Exception:
            pass
        
        # Fallback to sysfs
        try:
            for ac_path in ["/sys/class/power_supply/AC0/online",
                            "/sys/class/power_supply/AC/online",
                            "/sys/class/power_supply/ACAD/online"]:
                if os.path.exists(ac_path):
                    with open(ac_path, "r") as f:
                        return PowerState.AC.value if f.read().strip() == "1" else PowerState.BATTERY.value
        except Exception:
            pass
        
        return PowerState.UNKNOWN.value
    
    @classmethod
    def get_battery_level(cls) -> int:
        """
        Get current battery percentage.
        
        Returns:
            0-100 or -1 if no battery
        """
        try:
            result = subprocess.run(
                ["upower", "-i", "/org/freedesktop/UPower/devices/DisplayDevice"],
                capture_output=True, text=True, check=False, timeout=5
            )
            for line in result.stdout.splitlines():
                if "percentage:" in line.lower():
                    return int(line.split(":")[1].strip().rstrip("%"))
        except Exception:
            pass
        
        # Fallback to sysfs
        try:
            for bat_path in ["/sys/class/power_supply/BAT0/capacity",
                             "/sys/class/power_supply/BAT1/capacity"]:
                if os.path.exists(bat_path):
                    with open(bat_path, "r") as f:
                        return int(f.read().strip())
        except Exception:
            pass
        
        return -1
    
    # -------------------------------------------------------------------------
    # NetworkManager (Network State)
    # -------------------------------------------------------------------------
    
    def _register_networkmanager_signals(self):
        """Register for NetworkManager state change signals."""
        if not self._system_bus:
            return
            
        try:
            self._system_bus.add_signal_receiver(
                self._on_nm_state_changed,
                bus_name="org.freedesktop.NetworkManager",
                path="/org/freedesktop/NetworkManager",
                dbus_interface="org.freedesktop.NetworkManager",
                signal_name="StateChanged"
            )
            
            self._system_bus.add_signal_receiver(
                self._on_nm_properties_changed,
                bus_name="org.freedesktop.NetworkManager",
                path="/org/freedesktop/NetworkManager",
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged"
            )
            
            print("[Pulse] NetworkManager signals registered")
        except dbus.exceptions.DBusException as e:
            print(f"[Pulse] Could not register NetworkManager signals: {e}")
    
    def _on_nm_state_changed(self, state):
        """Handle NetworkManager state changes."""
        # NM_STATE: 70 = connected, 20 = disconnected
        if state >= 70:
            new_state = NetworkState.CONNECTED.value
        elif state >= 50:
            new_state = NetworkState.CONNECTING.value
        else:
            new_state = NetworkState.DISCONNECTED.value
        
        if new_state != self._last_network_state:
            self._last_network_state = new_state
            print(f"[Pulse] Network state changed: {new_state}")
            self.network_state_changed.emit(new_state)
            self.event_triggered.emit("network_state", {"state": new_state})
            
            # Check SSID on connection
            if new_state == NetworkState.CONNECTED.value:
                ssid = self.get_wifi_ssid()
                if ssid:
                    self.wifi_ssid_changed.emit(ssid)
                    self.event_triggered.emit("wifi_connected", {"ssid": ssid})
    
    def _on_nm_properties_changed(self, interface, changed, invalidated):
        """Handle NetworkManager property changes."""
        if "ActiveConnections" in changed:
            # Active connections changed, check for VPN
            has_vpn = self._check_vpn_active()
            self.vpn_state_changed.emit(has_vpn)
    
    def _check_vpn_active(self) -> bool:
        """Check if any VPN connection is active."""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE", "connection", "show", "--active"],
                capture_output=True, text=True, check=False, timeout=5
            )
            for line in result.stdout.splitlines():
                if "vpn" in line.lower() and "activated" in line.lower():
                    return True
        except Exception:
            pass
        return False
    
    @classmethod
    def get_network_state(cls) -> str:
        """
        Get current network connection state.
        
        Returns:
            NetworkState value as string
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "STATE", "general"],
                capture_output=True, text=True, check=False, timeout=5
            )
            state = result.stdout.strip().lower()
            if "disconnected" in state:
                return NetworkState.DISCONNECTED.value
            elif "connecting" in state:
                return NetworkState.CONNECTING.value
            elif "connected" in state:
                return NetworkState.CONNECTED.value
        except Exception:
            pass
        return NetworkState.DISCONNECTED.value
    
    @classmethod
    def get_wifi_ssid(cls) -> str:
        """
        Get current Wi-Fi SSID.
        
        Returns:
            SSID name or empty string
        """
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid", "device", "wifi"],
                capture_output=True, text=True, check=False, timeout=5
            )
            for line in result.stdout.splitlines():
                if line.startswith("yes:"):
                    return line.split(":", 1)[1]
        except Exception:
            pass
        return ""
    
    @classmethod
    def is_public_wifi(cls) -> bool:
        """
        Heuristic check if current Wi-Fi is likely public.
        Checks for common public network patterns.
        
        Returns:
            True if likely public network
        """
        ssid = cls.get_wifi_ssid().lower()
        public_patterns = [
            "guest", "public", "free", "open", "cafe", "coffee",
            "hotel", "airport", "library", "starbucks", "mcdonalds"
        ]
        return any(pattern in ssid for pattern in public_patterns)
    
    # -------------------------------------------------------------------------
    # Monitor Detection
    # -------------------------------------------------------------------------
    
    def _register_monitor_signals(self):
        """Register for display/monitor change signals."""
        if not self._system_bus:
            return
        
        # Try KDE first, then GNOME/Mutter
        try:
            # KDE Plasma uses kscreen
            session_bus = dbus.SessionBus()
            session_bus.add_signal_receiver(
                self._on_monitor_changed,
                bus_name="org.kde.KScreen",
                dbus_interface="org.kde.KScreen.Backend",
                signal_name="configChanged"
            )
            print("[Pulse] KDE monitor signals registered")
            return
        except Exception:
            pass
        
        try:
            # GNOME/Mutter uses org.gnome.Mutter.DisplayConfig
            session_bus = dbus.SessionBus()
            session_bus.add_signal_receiver(
                self._on_monitor_changed,
                bus_name="org.gnome.Mutter.DisplayConfig",
                dbus_interface="org.gnome.Mutter.DisplayConfig",
                signal_name="MonitorsChanged"
            )
            print("[Pulse] GNOME/Mutter monitor signals registered")
        except Exception as e:
            print(f"[Pulse] Could not register monitor signals: {e}")
    
    def _on_monitor_changed(self, *args):
        """Handle monitor configuration changes."""
        monitors = self.get_connected_monitors()
        count = len(monitors)
        
        if count != self._last_monitor_count:
            print(f"[Pulse] Monitor count changed: {self._last_monitor_count} -> {count}")
            self._last_monitor_count = count
            self.monitor_count_changed.emit(count)
            
            # Check for ultrawide
            for mon in monitors:
                if mon.get("is_ultrawide"):
                    self.event_triggered.emit("ultrawide_connected", mon)
                    break
            else:
                if count == 1:
                    self.event_triggered.emit("laptop_only", {})
    
    @classmethod
    def get_connected_monitors(cls) -> list:
        """
        Get list of connected monitors.
        
        Returns:
            List of MonitorInfo as dicts
        """
        monitors = []
        
        # Try xrandr (works on X11 and some XWayland)
        try:
            result = subprocess.run(
                ["xrandr", "--query"],
                capture_output=True, text=True, check=False, timeout=5
            )
            for line in result.stdout.splitlines():
                if " connected" in line:
                    parts = line.split()
                    name = parts[0]
                    is_primary = "primary" in line
                    
                    # Find resolution
                    width, height = 0, 0
                    for part in parts:
                        if "x" in part and "+" in part:
                            res = part.split("+")[0]
                            try:
                                width, height = map(int, res.split("x"))
                                break
                            except ValueError:
                                continue
                    
                    is_ultrawide = (width / height) > 2.0 if height > 0 else False
                    
                    monitors.append({
                        "name": name,
                        "width": width,
                        "height": height,
                        "is_primary": is_primary,
                        "is_ultrawide": is_ultrawide
                    })
        except Exception:
            pass
        
        # Fallback: try kscreen-doctor for KDE Wayland
        if not monitors:
            try:
                result = subprocess.run(
                    ["kscreen-doctor", "--outputs"],
                    capture_output=True, text=True, check=False, timeout=5
                )
                # Parse kscreen-doctor output
                current_output = None
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("Output:"):
                        if current_output:
                            monitors.append(current_output)
                        name = line.split(":", 1)[1].strip().split()[0]
                        current_output = {
                            "name": name,
                            "width": 0,
                            "height": 0,
                            "is_primary": False,
                            "is_ultrawide": False
                        }
                    elif current_output and "enabled" in line.lower():
                        current_output["enabled"] = "true" in line.lower()
                    elif current_output and "x" in line and "resolution" in line.lower():
                        try:
                            res_part = line.split(":")[1].strip().split("@")[0]
                            w, h = map(int, res_part.split("x"))
                            current_output["width"] = w
                            current_output["height"] = h
                            current_output["is_ultrawide"] = (w / h) > 2.0 if h > 0 else False
                        except (ValueError, IndexError):
                            pass
                
                if current_output:
                    monitors.append(current_output)
            except Exception:
                pass
        
        return monitors
    
    # -------------------------------------------------------------------------
    # Polling Fallback
    # -------------------------------------------------------------------------
    
    def _run_polling_fallback(self):
        """Fallback polling mode when DBus is unavailable."""
        import time
        
        print("[Pulse] Running in polling fallback mode")
        self._running = True
        
        while self._running:
            try:
                # Check power state
                power = self.get_power_state()
                if power != self._last_power_state:
                    self._last_power_state = power
                    self.power_state_changed.emit(power)
                
                # Check network state
                network = self.get_network_state()
                if network != self._last_network_state:
                    self._last_network_state = network
                    self.network_state_changed.emit(network)
                
                # Check monitors
                monitors = self.get_connected_monitors()
                if len(monitors) != self._last_monitor_count:
                    self._last_monitor_count = len(monitors)
                    self.monitor_count_changed.emit(len(monitors))
                
                time.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                print(f"[Pulse] Polling error: {e}")
                time.sleep(10)


class PulseThread(QThread):
    """Helper thread for running SystemPulse in the background."""
    
    def __init__(self, pulse: SystemPulse):
        super().__init__()
        self.pulse = pulse
    
    def run(self):
        """Start the pulse event loop."""
        self.pulse.start()
    
    def stop(self):
        """Stop the pulse event loop."""
        self.pulse.stop()
        self.quit()
        self.wait(5000)  # Wait up to 5 seconds


# Convenience function for creating and starting pulse
def create_pulse_listener() -> tuple:
    """
    Create and start a SystemPulse listener.
    
    Returns:
        (SystemPulse, PulseThread) tuple
    """
    pulse = SystemPulse()
    thread = PulseThread(pulse)
    pulse.moveToThread(thread)
    return pulse, thread
