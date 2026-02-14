"""
First-Run Wizard - Guided onboarding experience.
Part of v11.0 "Aurora Update".

Detects hardware, lets user pick a use-case profile, and saves
the selection to ~/.config/loofi-fedora-tweaks/profile.json.
The wizard only appears once; after completion (Apply or Skip)
it writes a sentinel file so it never re-appears.
"""

import json
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QRadioButton, QButtonGroup,
    QFrame, QScrollArea, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.hardware_profiles import detect_hardware_profile
from utils.log import get_logger

logger = get_logger(__name__)

# Paths -----------------------------------------------------------------
_CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
_FIRST_RUN_SENTINEL = _CONFIG_DIR / "first_run_complete"
_PROFILE_PATH = _CONFIG_DIR / "profile.json"


def needs_first_run() -> bool:
    """Return True when the wizard has never been completed."""
    return not _FIRST_RUN_SENTINEL.exists()


def _mark_first_run_complete():
    """Create the sentinel file so the wizard is never shown again."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _FIRST_RUN_SENTINEL.touch()


def _save_profile(profile_data: dict):
    """Persist the chosen profile to disk."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(profile_data, fh, indent=2)
    logger.info("Saved first-run profile to %s", _PROFILE_PATH)


# Helpers for hardware detection -----------------------------------------

def _read_file(path: str) -> str:
    """Safely read a sysfs / procfs file."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def _detect_cpu_model() -> str:
    """Return the CPU model string from /proc/cpuinfo."""
    cpuinfo = _read_file("/proc/cpuinfo")
    for line in cpuinfo.splitlines():
        if line.lower().startswith("model name"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return "Unknown CPU"


def _detect_gpu_vendor() -> str:
    """Best-effort GPU vendor detection from /proc and sysfs."""
    # Quick check via lspci-style sysfs
    drm_base = "/sys/class/drm"
    try:
        entries = os.listdir(drm_base)
    except OSError:
        entries = []
    for entry in sorted(entries):
        vendor_path = os.path.join(drm_base, entry, "device", "vendor")
        vendor_id = _read_file(vendor_path)
        if vendor_id == "0x8086":
            return "Intel"
        if vendor_id == "0x10de":
            return "NVIDIA"
        if vendor_id in ("0x1002", "0x1022"):
            return "AMD"
    return "Unknown"


def _has_battery() -> bool:
    """Return True if any battery sysfs node exists."""
    return (
        os.path.exists("/sys/class/power_supply/BAT0")
        or os.path.exists("/sys/class/power_supply/BAT1")
    )


# Use-case definitions ---------------------------------------------------

USE_CASES = {
    "gaming": {
        "label": "Gaming",
        "emoji": "\U0001f3ae",  # controller
        "description": "Optimize for gaming performance (GameMode, shader cache, etc.)",
    },
    "development": {
        "label": "Development",
        "emoji": "\U0001f6e0\ufe0f",  # hammer and wrench
        "description": "Setup development tools and containers",
    },
    "daily": {
        "label": "Daily Driver",
        "emoji": "\U0001f4bb",  # laptop
        "description": "Balanced setup for everyday use",
    },
    "server": {
        "label": "Server",
        "emoji": "\U0001f5a5\ufe0f",  # desktop computer
        "description": "Minimal services, security hardening",
    },
    "minimal": {
        "label": "Minimal",
        "emoji": "\u2728",  # sparkles
        "description": "Skip automatic optimizations",
    },
}


# Summary of what gets configured per use-case + hardware ----------------

def _build_summary(hw_profile_key: str, hw_profile: dict, use_case: str) -> str:
    """Return a human-readable summary of planned configuration."""
    lines = []
    lines.append(f"Hardware profile: {hw_profile.get('label', hw_profile_key)}")

    if hw_profile.get("battery_limit"):
        lines.append("  - Battery charge limit support enabled")
    if hw_profile.get("nbfc"):
        lines.append("  - Fan control (NBFC) profiles available")
    if hw_profile.get("fingerprint"):
        lines.append("  - Fingerprint reader support enabled")
    if hw_profile.get("power_profiles"):
        lines.append("  - Power profile switching enabled")
    thermal = hw_profile.get("thermal_management")
    if thermal:
        lines.append(f"  - Thermal management via {thermal}")

    lines.append("")
    uc = USE_CASES.get(use_case, {})
    lines.append(f"Use case: {uc.get('emoji', '')} {uc.get('label', use_case)}")

    if use_case == "gaming":
        lines.append("  - Enable GameMode integration")
        lines.append("  - Configure shader cache directory")
        lines.append("  - Install MangoHud overlay")
        lines.append("  - Set performance power profile by default")
    elif use_case == "development":
        lines.append("  - Pre-configure Podman / Distrobox")
        lines.append("  - Enable container-related services")
        lines.append("  - Suggest VS Code and dev tool installation")
    elif use_case == "daily":
        lines.append("  - Balanced power profile")
        lines.append("  - Multimedia codec installation")
        lines.append("  - Flatpak / Flathub setup")
    elif use_case == "server":
        lines.append("  - Disable unused desktop services")
        lines.append("  - Enable firewall hardening")
        lines.append("  - Minimal resource footprint")
    elif use_case == "minimal":
        lines.append("  - No automatic changes will be applied")
        lines.append("  - You can configure everything manually later")

    return "\n".join(lines)


# =======================================================================
# Wizard dialog
# =======================================================================

class FirstRunWizard(QDialog):
    """Five-step first-run wizard v2: Detect -> Choose -> Health -> Actions -> Apply."""

    # Sentinel for v2 completion
    _V2_SENTINEL = _CONFIG_DIR / "wizard_v2.json"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Loofi Fedora Tweaks - Setup Wizard"))
        self.setFixedSize(620, 560)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        # Detected hardware (populated in step 1)
        self._hw_key = ""
        self._hw_profile: dict = {}
        self._product_name = ""
        self._cpu_model = ""
        self._gpu_vendor = ""
        self._is_laptop = False
        self._selected_use_case = "daily"  # default

        # -- Root layout ------------------------------------------------
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 16)
        root_layout.setSpacing(12)

        # Title
        title_label = QLabel(self.tr("\U0001f680 Welcome to Loofi Fedora Tweaks"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(title_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(sep)

        # Step indicator
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_label.setStyleSheet("color: #39c5cf; font-weight: bold;")
        root_layout.addWidget(self._step_label)

        # Stacked pages ------------------------------------------------
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step4_health())
        self._stack.addWidget(self._build_step5_actions())
        self._stack.addWidget(self._build_step3())

        # Navigation buttons -------------------------------------------
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)

        self._btn_back = QPushButton(self.tr("\u2190 Back"))
        self._btn_back.setFixedWidth(100)
        self._btn_back.clicked.connect(self._go_back)
        nav_layout.addWidget(self._btn_back)

        nav_layout.addStretch()

        self._btn_skip = QPushButton(self.tr("Skip"))
        self._btn_skip.setFixedWidth(100)
        self._btn_skip.clicked.connect(self._skip)
        nav_layout.addWidget(self._btn_skip)

        self._btn_next = QPushButton(self.tr("Next \u2192"))
        self._btn_next.setFixedWidth(100)
        self._btn_next.setStyleSheet(
            "background-color: #39c5cf; color: #0b0e14; font-weight: bold; "
            "border-radius: 6px; padding: 6px;"
        )
        self._btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self._btn_next)

        root_layout.addLayout(nav_layout)

        # Kick off step 1
        self._set_step(0)

    # -- Step builders --------------------------------------------------

    def _build_step1(self) -> QWidget:
        """Step 1 - System Detection (auto-detected)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\U0001f50d Step 1: System Detection"))
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        header.setFont(hfont)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "We automatically detected your hardware so Loofi can "
                "apply the best settings for your machine."
            )
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        # Detection card
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #1c2030; border-radius: 10px; padding: 16px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        self._lbl_detected_summary = QLabel()
        self._lbl_detected_summary.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #3dd68c;"
        )
        card_layout.addWidget(self._lbl_detected_summary)

        self._lbl_hw_model = QLabel()
        self._lbl_hw_model.setWordWrap(True)
        card_layout.addWidget(self._lbl_hw_model)

        self._lbl_cpu = QLabel()
        self._lbl_cpu.setWordWrap(True)
        card_layout.addWidget(self._lbl_cpu)

        self._lbl_gpu = QLabel()
        card_layout.addWidget(self._lbl_gpu)

        self._lbl_form = QLabel()
        card_layout.addWidget(self._lbl_form)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _build_step2(self) -> QWidget:
        """Step 2 - Use Case Selection."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\U0001f3af Step 2: Choose Your Use Case"))
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        header.setFont(hfont)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "Select how you primarily use this computer. "
                "This helps Loofi suggest the right optimizations."
            )
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        # Scroll area for radio options (future-proof)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        options_layout = QVBoxLayout(scroll_content)
        options_layout.setSpacing(8)

        self._uc_button_group = QButtonGroup(self)
        self._uc_radios: dict[str, QRadioButton] = {}

        for idx, (key, uc) in enumerate(USE_CASES.items()):
            radio = QRadioButton(
                f"  {uc['emoji']}  {uc['label']}  \u2014  {uc['description']}"
            )
            radio.setStyleSheet(
                "QRadioButton { font-size: 13px; padding: 8px 4px; }"
                "QRadioButton::indicator { width: 16px; height: 16px; }"
            )
            if key == "daily":
                radio.setChecked(True)
            self._uc_button_group.addButton(radio, idx)
            self._uc_radios[key] = radio
            options_layout.addWidget(radio)

        options_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        return page

    def _build_step3(self) -> QWidget:
        """Step 3 - Confirmation / Apply."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\u2705 Step 3: Review & Apply"))
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        header.setFont(hfont)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "Here is a summary of what will be configured. "
                "Press Apply to save your profile, or Skip to configure manually later."
            )
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        # Summary card
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #1c2030; border-radius: 10px; padding: 16px; }"
        )
        card_layout = QVBoxLayout(card)

        self._lbl_summary = QLabel()
        self._lbl_summary.setWordWrap(True)
        self._lbl_summary.setStyleSheet("font-size: 12px; line-height: 1.5;")
        self._lbl_summary.setTextFormat(Qt.TextFormat.PlainText)
        card_layout.addWidget(self._lbl_summary)

        layout.addWidget(card, 1)
        return page

    # -- Navigation logic -----------------------------------------------

    def _set_step(self, index: int):
        """Switch visible step and update buttons."""
        index = max(0, min(index, 4))
        self._stack.setCurrentIndex(index)

        step_names = [
            self.tr("Step 1 of 5: Detection"),
            self.tr("Step 2 of 5: Use Case"),
            self.tr("Step 3 of 5: Health Check"),
            self.tr("Step 4 of 5: Recommendations"),
            self.tr("Step 5 of 5: Apply"),
        ]
        self._step_label.setText(step_names[index])

        self._btn_back.setVisible(index > 0)

        if index < 4:
            self._btn_next.setText(self.tr("Next \u2192"))
            self._btn_next.setStyleSheet(
                "background-color: #39c5cf; color: #0b0e14; font-weight: bold; "
                "border-radius: 6px; padding: 6px;"
            )
        else:
            self._btn_next.setText(self.tr("\u2705 Apply"))
            self._btn_next.setStyleSheet(
                "background-color: #3dd68c; color: #0b0e14; font-weight: bold; "
                "border-radius: 6px; padding: 6px;"
            )

        # Populate contents when entering a step
        if index == 0:
            self._populate_step1()
        elif index == 2:
            self._populate_health()
        elif index == 3:
            self._populate_actions()
        elif index == 4:
            self._populate_step3()

    def _go_next(self):
        current = self._stack.currentIndex()
        if current == 1:
            self._capture_use_case()
        if current < 4:
            self._set_step(current + 1)
        else:
            self._apply()

    def _go_back(self):
        current = self._stack.currentIndex()
        if current > 0:
            self._set_step(current - 1)

    def _skip(self):
        """Skip the wizard entirely."""
        _mark_first_run_complete()
        logger.info("First-run wizard skipped by user.")
        self.accept()

    def _apply(self):
        """Save profile, v2 data, and mark complete."""
        self._capture_use_case()

        profile_data = {
            "hardware_profile": self._hw_key,
            "hardware_label": self._hw_profile.get("label", self._hw_key),
            "product_name": self._product_name,
            "cpu": self._cpu_model,
            "gpu_vendor": self._gpu_vendor,
            "is_laptop": self._is_laptop,
            "use_case": self._selected_use_case,
        }

        # Collect v2 action selections
        v2_data = {
            "health_checks": getattr(self, "_health_results", {}),
            "selected_actions": [],
        }
        for cb in getattr(self, "_action_checkboxes", []):
            if cb.isChecked():
                v2_data["selected_actions"].append(cb.text())

        _save_profile(profile_data)
        _mark_first_run_complete()

        # Save v2 completion data
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self._V2_SENTINEL, "w", encoding="utf-8") as fh:
            json.dump(v2_data, fh, indent=2)

        logger.info("First-run wizard v2 completed. Profile: %s", profile_data)
        self.accept()

    # -- Data helpers ---------------------------------------------------

    def _populate_step1(self):
        """Run hardware detection and fill in step-1 labels."""
        self._hw_key, self._hw_profile = detect_hardware_profile()

        self._product_name = _read_file("/sys/class/dmi/id/product_name")
        product_family = _read_file("/sys/class/dmi/id/product_family")
        sys_vendor = _read_file("/sys/class/dmi/id/sys_vendor")
        self._cpu_model = _detect_cpu_model()
        self._gpu_vendor = _detect_gpu_vendor()
        self._is_laptop = _has_battery()

        hw_label = self._hw_profile.get("label", self._hw_key)
        display_name = self._product_name or product_family or hw_label
        if sys_vendor and sys_vendor.lower() not in display_name.lower():
            display_name = f"{sys_vendor} {display_name}"

        self._lbl_detected_summary.setText(
            self.tr("Detected: {name}").format(name=display_name)
        )
        self._lbl_hw_model.setText(
            self.tr("\U0001f4bb  Hardware profile: {profile}").format(profile=hw_label)
        )
        self._lbl_cpu.setText(
            self.tr("\U0001f9e0  CPU: {cpu}").format(cpu=self._cpu_model)
        )
        self._lbl_gpu.setText(
            self.tr("\U0001f3a8  GPU vendor: {gpu}").format(gpu=self._gpu_vendor)
        )
        form_factor = self.tr("Laptop (battery detected)") if self._is_laptop else self.tr("Desktop")
        self._lbl_form.setText(
            self.tr("\U0001f50c  Form factor: {form}").format(form=form_factor)
        )

    def _capture_use_case(self):
        """Read the currently selected radio button."""
        list(USE_CASES.keys())
        for key, radio in self._uc_radios.items():
            if radio.isChecked():
                self._selected_use_case = key
                return
        # Fallback if nothing checked (should not happen)
        self._selected_use_case = "daily"

    def _populate_step3(self):
        """Build the confirmation summary."""
        self._capture_use_case()
        summary = _build_summary(
            self._hw_key, self._hw_profile, self._selected_use_case
        )
        self._lbl_summary.setText(summary)

    # -- v2 Health Check & Actions pages --------------------------------

    def _build_step4_health(self) -> QWidget:
        """Step 3 (v2) - System Health Check."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\U0001fa7a Step 3: System Health Check"))
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        header.setFont(hfont)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "Quick diagnostics to identify potential issues. "
                "Problems will be flagged for your attention."
            )
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        # Health results card
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self._health_layout = QVBoxLayout(scroll_content)
        self._health_layout.setSpacing(6)
        self._health_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        return page

    def _build_step5_actions(self) -> QWidget:
        """Step 4 (v2) - Recommended Actions."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\U0001f4cb Step 4: Recommended Actions"))
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        header.setFont(hfont)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "Based on your system health check, here are recommended actions. "
                "Check the ones you'd like to apply."
            )
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self._actions_layout = QVBoxLayout(scroll_content)
        self._actions_layout.setSpacing(6)
        self._actions_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        return page

    def _populate_health(self):
        """Run health checks and display results."""
        import shutil
        import subprocess

        # Clear previous results
        while self._health_layout.count() > 1:
            item = self._health_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._health_results = {}
        checks = []

        # 1. Disk space
        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
            pct_used = ((total_gb - free_gb) / total_gb * 100) if total_gb else 0
            if free_gb < 5:
                checks.append(("⚠️", f"Low disk space: {free_gb:.1f} GB free ({pct_used:.0f}% used)", "warning"))
            else:
                checks.append(("✅", f"Disk space OK: {free_gb:.1f} GB free ({pct_used:.0f}% used)", "ok"))
            self._health_results["disk_free_gb"] = round(free_gb, 1)
        except OSError:
            checks.append(("❓", "Could not check disk space", "unknown"))

        # 2. Package manager state
        if shutil.which("dnf"):
            try:
                result = subprocess.run(
                    ["dnf", "check", "--duplicates"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    checks.append(("✅", "Package state healthy (no duplicates)", "ok"))
                else:
                    checks.append(("⚠️", "Package issues detected (duplicates found)", "warning"))
                self._health_results["pkg_healthy"] = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                checks.append(("❓", "Could not check package state", "unknown"))
        else:
            checks.append(("ℹ️", "DNF not found (atomic system?)", "info"))

        # 3. Firewall status
        if shutil.which("firewall-cmd"):
            try:
                result = subprocess.run(
                    ["firewall-cmd", "--state"],
                    capture_output=True, text=True, timeout=5
                )
                if "running" in result.stdout.lower():
                    checks.append(("✅", "Firewall is running", "ok"))
                else:
                    checks.append(("⚠️", "Firewall is NOT running", "warning"))
                self._health_results["firewall_running"] = "running" in result.stdout.lower()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                checks.append(("❓", "Could not check firewall status", "unknown"))
        else:
            checks.append(("❓", "firewall-cmd not found", "unknown"))

        # 4. Backup tool availability
        if shutil.which("timeshift") or shutil.which("snapper"):
            tool = "timeshift" if shutil.which("timeshift") else "snapper"
            checks.append(("✅", f"Backup tool available: {tool}", "ok"))
            self._health_results["backup_tool"] = tool
        else:
            checks.append(("⚠️", "No backup tool installed (timeshift/snapper)", "warning"))
            self._health_results["backup_tool"] = None

        # 5. SELinux status
        try:
            result = subprocess.run(
                ["getenforce"], capture_output=True, text=True, timeout=5
            )
            mode = result.stdout.strip()
            if mode == "Enforcing":
                checks.append(("✅", f"SELinux: {mode}", "ok"))
            else:
                checks.append(("ℹ️", f"SELinux: {mode}", "info"))
            self._health_results["selinux"] = mode
        except (FileNotFoundError, subprocess.TimeoutExpired):
            checks.append(("❓", "Could not check SELinux", "unknown"))

        # Display results
        for icon, text, level in checks:
            lbl = QLabel(f"  {icon}  {text}")
            lbl.setWordWrap(True)
            color = {"ok": "#3dd68c", "warning": "#f5a623", "info": "#39c5cf", "unknown": "#9da7bf"}.get(level, "#9da7bf")
            lbl.setStyleSheet(f"font-size: 13px; color: {color}; padding: 4px;")
            self._health_layout.insertWidget(self._health_layout.count() - 1, lbl)

    def _populate_actions(self):
        """Build recommendation checkboxes based on health results."""
        # Clear previous
        while self._actions_layout.count() > 1:
            item = self._actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._action_checkboxes = []
        results = getattr(self, "_health_results", {})

        recommendations = []

        # Based on health check results
        if results.get("disk_free_gb", 999) < 10:
            recommendations.append({
                "text": "Run disk cleanup (remove old kernels, clear caches)",
                "risk": "LOW",
                "checked": True,
            })

        if results.get("pkg_healthy") is False:
            recommendations.append({
                "text": "Fix package duplicates (dnf check --duplicates)",
                "risk": "MEDIUM",
                "checked": True,
            })

        if results.get("firewall_running") is False:
            recommendations.append({
                "text": "Enable firewall (firewalld)",
                "risk": "LOW",
                "checked": True,
            })

        if results.get("backup_tool") is None:
            recommendations.append({
                "text": "Install backup tool (timeshift recommended)",
                "risk": "LOW",
                "checked": True,
            })

        selinux = results.get("selinux", "")
        if selinux and selinux != "Enforcing":
            recommendations.append({
                "text": f"SELinux is {selinux} — consider enabling Enforcing mode",
                "risk": "MEDIUM",
                "checked": False,
            })

        # Always suggest these
        recommendations.append({
            "text": "Configure automatic system snapshots before updates",
            "risk": "LOW",
            "checked": True,
        })

        if not recommendations:
            lbl = QLabel(self.tr("  ✅ Your system looks great! No actions needed."))
            lbl.setStyleSheet("font-size: 13px; color: #3dd68c; padding: 8px;")
            self._actions_layout.insertWidget(0, lbl)
            return

        for rec in recommendations:
            risk_color = {"LOW": "#3dd68c", "MEDIUM": "#f5a623", "HIGH": "#e06c75"}.get(rec["risk"], "#9da7bf")
            cb = QCheckBox(f"  [{rec['risk']}] {rec['text']}")
            cb.setChecked(rec["checked"])
            cb.setStyleSheet(f"font-size: 12px; color: {risk_color}; padding: 4px;")
            self._action_checkboxes.append(cb)
            self._actions_layout.insertWidget(self._actions_layout.count() - 1, cb)
