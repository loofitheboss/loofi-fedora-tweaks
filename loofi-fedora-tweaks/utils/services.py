"""
Service management utilities for systemd.
Part of v7.5 "Watchtower" update.

Gaming-focused service manager - differentiates from Cockpit by
focusing on gaming-relevant services like GameMode, Steam, etc.
"""

import subprocess
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class UnitScope(Enum):
    """Systemd unit scope."""
    SYSTEM = "system"
    USER = "user"


class UnitState(Enum):
    """Service state."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    UNKNOWN = "unknown"


@dataclass
class ServiceUnit:
    """Represents a systemd service unit."""
    name: str
    state: UnitState
    scope: UnitScope
    description: str = ""
    is_gaming: bool = False


@dataclass
class Result:
    """Operation result with message."""
    success: bool
    message: str


class ServiceManager:
    """
    Gaming-focused systemd service manager.
    
    Unlike generic system admin tools, this focuses on:
    - Gaming services (GameMode, Steam)
    - User services
    - Failed services (troubleshooting)
    """
    
    # Gaming-relevant services to highlight
    GAMING_SERVICES = [
        "gamemoded",
        "steam",
        "gamemode",
        "mangohud",
        "nvidia-persistenced",
        "nvidia-powerd",
        "amdgpu-pro-core",
        "upower",  # Power management affects gaming
        "thermald",  # Thermal management
    ]
    
    @classmethod
    def list_units(cls, scope: UnitScope = UnitScope.USER, 
                   filter_type: str = "all") -> list[ServiceUnit]:
        """
        List systemd service units.
        
        Args:
            scope: System or user services
            filter_type: "all", "gaming", "failed", or "active"
            
        Returns:
            List of ServiceUnit objects.
        """
        try:
            cmd = ["systemctl"]
            if scope == UnitScope.USER:
                cmd.append("--user")
            cmd.extend(["list-units", "--type=service", "--all", "--no-pager", 
                       "--plain", "--no-legend"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            units = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) < 4:
                    continue
                
                name = parts[0].replace(".service", "")
                load_state = parts[1]
                active_state = parts[2].lower()
                sub_state = parts[3].lower()
                description = " ".join(parts[4:]) if len(parts) > 4 else ""
                
                # Parse state
                if active_state == "active":
                    state = UnitState.ACTIVE
                elif active_state == "failed":
                    state = UnitState.FAILED
                elif active_state == "inactive":
                    state = UnitState.INACTIVE
                elif active_state == "activating":
                    state = UnitState.ACTIVATING
                else:
                    state = UnitState.UNKNOWN
                
                # Check if gaming-related
                is_gaming = any(g in name.lower() for g in cls.GAMING_SERVICES)
                
                unit = ServiceUnit(
                    name=name,
                    state=state,
                    scope=scope,
                    description=description,
                    is_gaming=is_gaming
                )
                
                # Apply filter
                if filter_type == "gaming" and not is_gaming:
                    continue
                elif filter_type == "failed" and state != UnitState.FAILED:
                    continue
                elif filter_type == "active" and state != UnitState.ACTIVE:
                    continue
                
                units.append(unit)
            
            return units
            
        except Exception:
            return []
    
    @classmethod
    def get_failed_units(cls) -> list[ServiceUnit]:
        """Get all failed units across both user and system scopes."""
        failed = []
        
        # User failures
        failed.extend(cls.list_units(UnitScope.USER, "failed"))
        
        # System failures (may require auth to view all)
        try:
            failed.extend(cls.list_units(UnitScope.SYSTEM, "failed"))
        except Exception:
            pass
        
        return failed
    
    @classmethod
    def get_gaming_units(cls) -> list[ServiceUnit]:
        """Get gaming-related units."""
        gaming = []
        
        # Check both scopes
        gaming.extend(cls.list_units(UnitScope.USER, "gaming"))
        gaming.extend(cls.list_units(UnitScope.SYSTEM, "gaming"))
        
        # Remove duplicates by name
        seen = set()
        unique = []
        for unit in gaming:
            if unit.name not in seen:
                seen.add(unit.name)
                unique.append(unit)
        
        return unique
    
    @classmethod
    def start_unit(cls, name: str, scope: UnitScope = UnitScope.USER) -> Result:
        """Start a service unit."""
        cmd = ["systemctl"]
        if scope == UnitScope.USER:
            cmd.append("--user")
        else:
            cmd.insert(0, "pkexec")
        cmd.extend(["start", f"{name}.service"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return Result(True, f"Started {name}")
            else:
                return Result(False, f"Failed to start {name}: {result.stderr}")
        except Exception as e:
            return Result(False, f"Error: {e}")
    
    @classmethod
    def stop_unit(cls, name: str, scope: UnitScope = UnitScope.USER) -> Result:
        """Stop a service unit."""
        cmd = ["systemctl"]
        if scope == UnitScope.USER:
            cmd.append("--user")
        else:
            cmd.insert(0, "pkexec")
        cmd.extend(["stop", f"{name}.service"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return Result(True, f"Stopped {name}")
            else:
                return Result(False, f"Failed to stop {name}: {result.stderr}")
        except Exception as e:
            return Result(False, f"Error: {e}")
    
    @classmethod
    def restart_unit(cls, name: str, scope: UnitScope = UnitScope.USER) -> Result:
        """Restart a service unit."""
        cmd = ["systemctl"]
        if scope == UnitScope.USER:
            cmd.append("--user")
        else:
            cmd.insert(0, "pkexec")
        cmd.extend(["restart", f"{name}.service"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return Result(True, f"Restarted {name}")
            else:
                return Result(False, f"Failed to restart {name}: {result.stderr}")
        except Exception as e:
            return Result(False, f"Error: {e}")
    
    @classmethod
    def mask_unit(cls, name: str, scope: UnitScope = UnitScope.USER) -> Result:
        """Mask a service unit (prevent it from starting)."""
        cmd = ["systemctl"]
        if scope == UnitScope.USER:
            cmd.append("--user")
        else:
            cmd.insert(0, "pkexec")
        cmd.extend(["mask", f"{name}.service"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return Result(True, f"Masked {name}")
            else:
                return Result(False, f"Failed to mask {name}: {result.stderr}")
        except Exception as e:
            return Result(False, f"Error: {e}")
    
    @classmethod
    def unmask_unit(cls, name: str, scope: UnitScope = UnitScope.USER) -> Result:
        """Unmask a service unit."""
        cmd = ["systemctl"]
        if scope == UnitScope.USER:
            cmd.append("--user")
        else:
            cmd.insert(0, "pkexec")
        cmd.extend(["unmask", f"{name}.service"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return Result(True, f"Unmasked {name}")
            else:
                return Result(False, f"Failed to unmask {name}: {result.stderr}")
        except Exception as e:
            return Result(False, f"Error: {e}")
    
    @classmethod
    def get_unit_status(cls, name: str, scope: UnitScope = UnitScope.USER) -> str:
        """Get detailed status of a unit."""
        cmd = ["systemctl"]
        if scope == UnitScope.USER:
            cmd.append("--user")
        cmd.extend(["status", f"{name}.service", "--no-pager"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout
        except Exception:
            return ""
