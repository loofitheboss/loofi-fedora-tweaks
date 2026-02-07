"""
Journal log utilities.
Part of v7.5 "Watchtower" update.

Provides focused journalctl access with a "Panic Button" for
exporting logs ready for support forums.
"""

import subprocess
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Result:
    """Operation result with message."""
    success: bool
    message: str
    data: Optional[dict] = None


class JournalManager:
    """
    Focused journalctl wrapper for error export.
    
    Unlike full log viewers (Cockpit, journalctl directly), this focuses on:
    - Current boot errors only
    - Forum-ready exports with system info
    - Quick access to common error scenarios
    """
    
    @classmethod
    def get_boot_errors(cls, priority: int = 3) -> str:
        """
        Get error messages from current boot.
        
        Args:
            priority: Maximum priority level (0=emerg, 3=err, 4=warning)
            
        Returns:
            Log output as string.
        """
        try:
            result = subprocess.run(
                ["journalctl", "-p", str(priority), "-xb", "--no-pager", "-n", "100"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    
    @classmethod
    def get_recent_errors(cls, since: str = "1 hour ago") -> str:
        """
        Get recent error messages.
        
        Args:
            since: Time specification (e.g., "1 hour ago", "today")
            
        Returns:
            Log output as string.
        """
        try:
            result = subprocess.run(
                ["journalctl", "-p", "3", "--since", since, "--no-pager", "-n", "200"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    
    @classmethod
    def get_service_logs(cls, service: str, lines: int = 50) -> str:
        """
        Get logs for a specific service.
        
        Args:
            service: Service unit name (e.g., "NetworkManager")
            lines: Number of lines to retrieve
            
        Returns:
            Log output as string.
        """
        try:
            result = subprocess.run(
                ["journalctl", "-u", f"{service}.service", "-n", str(lines), 
                 "--no-pager", "-b"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    
    @classmethod
    def get_kernel_messages(cls, lines: int = 100) -> str:
        """
        Get kernel messages (dmesg-like).
        
        Returns:
            Kernel log output.
        """
        try:
            result = subprocess.run(
                ["journalctl", "-k", "-b", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    
    @classmethod
    def _get_system_info(cls) -> str:
        """Gather system info for forum post."""
        info_lines = []
        
        # OS Release
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith(("NAME=", "VERSION_ID=", "VARIANT=")):
                        info_lines.append(line.strip())
        except Exception:
            pass
        
        # Kernel version
        try:
            result = subprocess.run(["uname", "-r"], capture_output=True, text=True)
            if result.returncode == 0:
                info_lines.append(f"KERNEL={result.stdout.strip()}")
        except Exception:
            pass
        
        # Desktop environment
        de = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
        info_lines.append(f"DESKTOP={de}")
        
        # GPU
        try:
            result = subprocess.run(
                ["lspci", "-nn"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "VGA" in line or "3D" in line:
                        info_lines.append(f"GPU={line.split(': ')[-1][:80]}")
                        break
        except Exception:
            pass
        
        return "\n".join(info_lines)
    
    @classmethod
    def export_panic_log(cls, output_path: Optional[Path] = None) -> Result:
        """
        Export a forum-ready panic log.
        
        Creates a formatted text file with:
        - System info
        - Current boot errors
        - Recent kernel messages
        - Failed services
        
        Args:
            output_path: Where to save (default: ~/loofi-panic-log-{timestamp}.txt)
            
        Returns:
            Result with path to created file.
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path.home() / f"loofi-panic-log-{timestamp}.txt"
        
        try:
            sections = []
            
            # Header
            sections.append("=" * 60)
            sections.append("LOOFI FEDORA TWEAKS - PANIC LOG")
            sections.append(f"Generated: {datetime.now().isoformat()}")
            sections.append("=" * 60)
            sections.append("")
            
            # System Info
            sections.append("## SYSTEM INFORMATION")
            sections.append("-" * 40)
            sections.append(cls._get_system_info())
            sections.append("")
            
            # Failed Services
            sections.append("## FAILED SERVICES")
            sections.append("-" * 40)
            try:
                result = subprocess.run(
                    ["systemctl", "--failed", "--no-pager", "--plain"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                sections.append(result.stdout.strip() if result.returncode == 0 else "Unable to query")
            except Exception:
                sections.append("Unable to query failed services")
            sections.append("")
            
            # Boot Errors
            sections.append("## BOOT ERRORS (Priority: Error and above)")
            sections.append("-" * 40)
            errors = cls.get_boot_errors()
            sections.append(errors if errors else "No errors found")
            sections.append("")
            
            # Kernel Messages
            sections.append("## RECENT KERNEL MESSAGES")
            sections.append("-" * 40)
            kernel = cls.get_kernel_messages(lines=50)
            sections.append(kernel if kernel else "Unable to retrieve")
            sections.append("")
            
            # Footer
            sections.append("=" * 60)
            sections.append("END OF LOG")
            sections.append("=" * 60)
            
            # Write file
            content = "\n".join(sections)
            with open(output_path, "w") as f:
                f.write(content)
            
            return Result(
                True,
                f"Panic log exported to: {output_path}",
                {"path": str(output_path), "size": len(content)}
            )
            
        except Exception as e:
            return Result(False, f"Failed to export log: {e}")
    
    @classmethod
    def get_quick_diagnostic(cls) -> dict:
        """
        Get a quick diagnostic summary.
        
        Returns dict with:
        - error_count: Number of errors in current boot
        - failed_services: List of failed service names
        - recent_errors: Last 5 error messages
        """
        diagnostic = {
            "error_count": 0,
            "failed_services": [],
            "recent_errors": []
        }
        
        try:
            # Count errors
            errors = cls.get_boot_errors()
            if errors:
                diagnostic["error_count"] = errors.count("\n")
                # Get last 5 unique messages
                lines = [l.strip() for l in errors.split("\n") if l.strip()]
                diagnostic["recent_errors"] = lines[-5:]
            
            # Failed services
            result = subprocess.run(
                ["systemctl", "--failed", "--no-pager", "--plain", "--no-legend"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split()
                        if parts:
                            diagnostic["failed_services"].append(parts[0])
        except Exception:
            pass
        
        return diagnostic
