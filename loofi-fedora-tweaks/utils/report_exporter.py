"""
Report Exporter — v31.0 Smart UX
Exports system information as Markdown or HTML report.

v42.0.0 Sentinel: Replaced subprocess.getoutput() with safe alternatives.
"""

import logging
import os
import platform
import socket
import subprocess
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ReportExporter:
    """Exports system information in Markdown or HTML format."""

    @staticmethod
    def _read_file(path: str) -> Optional[str]:
        """Read a file safely, returning None on error.

        Args:
            path: Absolute file path.

        Returns:
            File contents stripped, or None on failure.
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
        except (OSError, IOError) as e:
            logger.debug("Failed to read %s: %s", path, e)
            return None

    @staticmethod
    def _run_cmd(cmd: list, timeout: int = 10) -> Optional[str]:
        """Run a command safely and return stdout.

        Args:
            cmd: Command as argument list (no shell).
            timeout: Subprocess timeout in seconds.

        Returns:
            Stripped stdout, or None on failure.
        """
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Command %s failed: %s", cmd, e)
            return None

    @staticmethod
    def gather_system_info() -> Dict[str, str]:
        """
        Collect all system information for the report.

        Returns:
            Dictionary of system info key-value pairs.
        """
        info: Dict[str, str] = {}

        # Hostname — use socket (no subprocess needed)
        try:
            info["hostname"] = socket.gethostname()
        except OSError as e:
            logger.debug("Failed to get hostname: %s", e)
            info["hostname"] = "Unknown"

        # Kernel — use platform (no subprocess needed)
        info["kernel"] = platform.release() or "Unknown"

        # Fedora release — read the file directly (not cat via shell)
        fedora_release = ReportExporter._read_file("/etc/fedora-release")
        info["fedora_version"] = fedora_release or "Unknown"

        # CPU model — parse lscpu output without shell pipes
        lscpu_out = ReportExporter._run_cmd(["lscpu"])
        cpu = "Unknown"
        if lscpu_out:
            for line in lscpu_out.splitlines():
                if "Model name" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        cpu = parts[1].strip()
                    break
        info["cpu"] = cpu

        # RAM — parse free output without awk
        free_out = ReportExporter._run_cmd(["free", "-h"])
        ram = "Unknown"
        if free_out:
            for line in free_out.splitlines():
                if line.startswith("Mem:"):
                    fields = line.split()
                    if len(fields) >= 3:
                        ram = f"{fields[1]} total, {fields[2]} used"
                    break
        info["ram"] = ram

        # Disk — parse df output without awk
        df_out = ReportExporter._run_cmd(["df", "-h", "/"])
        disk = "Unknown"
        if df_out:
            lines = df_out.splitlines()
            if len(lines) >= 2:
                fields = lines[1].split()
                if len(fields) >= 5:
                    disk = f"{fields[2]}/{fields[1]} ({fields[4]} used)"
        info["disk_root"] = disk

        # Uptime
        uptime_out = ReportExporter._run_cmd(["uptime", "-p"])
        info["uptime"] = uptime_out or "Unknown"

        # Battery — read sysfs directly (not cat via shell)
        bat_cap = ReportExporter._read_file("/sys/class/power_supply/BAT0/capacity")
        if bat_cap is not None:
            bat_status = (
                ReportExporter._read_file("/sys/class/power_supply/BAT0/status")
                or "Unknown"
            )
            info["battery"] = f"{bat_cap}% ({bat_status})"
        else:
            info["battery"] = "No battery detected"

        # Architecture — use platform (no subprocess needed)
        info["architecture"] = platform.machine() or "Unknown"

        # Desktop environment
        info["desktop"] = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")

        info["report_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return info

    @staticmethod
    def export_markdown(info: Dict[str, str]) -> str:
        """
        Format system info as a Markdown report.

        Args:
            info: Dictionary of system info key-value pairs.

        Returns:
            Formatted Markdown string.
        """
        lines = [
            "# System Report — Loofi Fedora Tweaks",
            "",
            f"**Generated:** {info.get('report_date', 'Unknown')}",
            "",
            "## System Information",
            "",
            "| Property | Value |",
            "|----------|-------|",
        ]

        field_labels = {
            "hostname": "Hostname",
            "kernel": "Kernel",
            "fedora_version": "Fedora Version",
            "cpu": "CPU",
            "ram": "RAM",
            "disk_root": "Disk Usage (/)",
            "uptime": "Uptime",
            "battery": "Battery",
            "architecture": "Architecture",
            "desktop": "Desktop Environment",
        }

        for key, label in field_labels.items():
            value = info.get(key, "Unknown")
            lines.append(f"| {label} | {value} |")

        lines.append("")
        lines.append("---")
        lines.append("*Report generated by Loofi Fedora Tweaks*")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def export_html(info: Dict[str, str]) -> str:
        """
        Format system info as a styled HTML report.

        Args:
            info: Dictionary of system info key-value pairs.

        Returns:
            Complete HTML document string.
        """
        field_labels = {
            "hostname": "Hostname",
            "kernel": "Kernel",
            "fedora_version": "Fedora Version",
            "cpu": "CPU",
            "ram": "RAM",
            "disk_root": "Disk Usage (/)",
            "uptime": "Uptime",
            "battery": "Battery",
            "architecture": "Architecture",
            "desktop": "Desktop Environment",
        }

        rows = ""
        for key, label in field_labels.items():
            value = info.get(key, "Unknown")
            rows += f"        <tr><td><b>{label}</b></td><td>{value}</td></tr>\n"

        report_date = info.get("report_date", "Unknown")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>System Report — Loofi Fedora Tweaks</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 800px; margin: 40px auto; padding: 0 20px;
               background: #0b0e14; color: #e6edf3; }}
        h1 {{ color: #39c5cf; border-bottom: 2px solid #1c2030; padding-bottom: 12px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ padding: 10px 16px; text-align: left; border-bottom: 1px solid #1c2030; }}
        th {{ background: #1c2030; color: #39c5cf; }}
        tr:hover {{ background: #1c2030; }}
        .footer {{ color: #6c7086; font-size: 0.85em; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>System Report — Loofi Fedora Tweaks</h1>
    <p><b>Generated:</b> {report_date}</p>
    <h2>System Information</h2>
    <table>
        <tr><th>Property</th><th>Value</th></tr>
{rows}    </table>
    <p class="footer">Report generated by Loofi Fedora Tweaks</p>
</body>
</html>"""

        return html

    @staticmethod
    def save_report(path: str, fmt: str, info: Optional[Dict[str, str]] = None) -> str:
        """
        Generate and save a system report to a file.

        Args:
            path: Output file path.
            fmt: Format — 'markdown' or 'html'.
            info: Optional pre-gathered info dict. If None, gathers fresh info.

        Returns:
            The path of the saved report.
        """
        if info is None:
            info = ReportExporter.gather_system_info()

        if fmt == "html":
            content = ReportExporter.export_html(info)
        else:
            content = ReportExporter.export_markdown(info)

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return path
