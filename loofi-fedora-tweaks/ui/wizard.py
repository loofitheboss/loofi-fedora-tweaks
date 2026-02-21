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

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from services.hardware.hardware_profiles import detect_hardware_profile
from utils.log import get_logger
from utils.wizard_health import WizardHealth

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
    return os.path.exists("/sys/class/power_supply/BAT0") or os.path.exists(
        "/sys/class/power_supply/BAT1"
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Loofi Fedora Tweaks - Setup Wizard"))
        self.setFixedSize(620, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

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
        self._step_label.setObjectName("wizardStepLabel")
        root_layout.addWidget(self._step_label)

        # Progress bar (v47.0)
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(6)
        self._progress_bar.setValue(1)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setObjectName("wizardProgressBar")
        root_layout.addWidget(self._progress_bar)

        # Stacked pages ------------------------------------------------
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step_experience_level())
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
        self._btn_next.setObjectName("wizardBtnNext")
        self._btn_next.setProperty("wizardMode", "next")
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
        desc.setObjectName("wizardDesc")
        layout.addWidget(desc)

        # Detection card
        card = QFrame()
        card.setObjectName("wizardDetectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        self._lbl_detected_summary = QLabel()
        self._lbl_detected_summary.setObjectName("wizardDetectedSummary")
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

    def _build_step_experience_level(self) -> QWidget:
        """Step 2 - Experience Level Selection (v47.0)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\U0001f393 Step 2: Experience Level"))
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        header.setFont(hfont)
        layout.addWidget(header)

        desc = QLabel(
            self.tr(
                "Choose your experience level. This controls which tabs are "
                "visible in the sidebar. You can change this later in Settings."
            )
        )
        desc.setWordWrap(True)
        desc.setObjectName("wizardDesc")
        layout.addWidget(desc)

        self._exp_button_group = QButtonGroup(self)
        levels = [
            (
                "beginner",
                self.tr("\U0001f331 Beginner"),
                self.tr("Essential tools only — ideal for new Fedora users. Shows 12 core tabs."),
            ),
            (
                "intermediate",
                self.tr("\U0001f4bb Intermediate"),
                self.tr("Core tools plus development, extensions, and customization. Shows 20 tabs."),
            ),
            (
                "advanced",
                self.tr("\U0001f680 Advanced"),
                self.tr("Full access to all 28 tabs and every feature."),
            ),
        ]
        self._exp_radios: dict[str, QRadioButton] = {}
        for idx, (key, label, tip) in enumerate(levels):
            radio = QRadioButton(f"  {label}")
            radio.setToolTip(tip)
            radio.setObjectName("wizardUseCaseRadio")
            if key == "beginner":
                radio.setChecked(True)
            self._exp_button_group.addButton(radio, idx)
            self._exp_radios[key] = radio
            layout.addWidget(radio)

            tip_label = QLabel(f"    {tip}")
            tip_label.setWordWrap(True)
            tip_label.setObjectName("wizardDesc")
            layout.addWidget(tip_label)

        layout.addStretch()
        return page

    def _capture_experience_level(self):
        """Read selected experience level and apply it."""
        try:
            from utils.experience_level import ExperienceLevel, ExperienceLevelManager
            level_map = {
                "beginner": ExperienceLevel.BEGINNER,
                "intermediate": ExperienceLevel.INTERMEDIATE,
                "advanced": ExperienceLevel.ADVANCED,
            }
            for key, radio in self._exp_radios.items():
                if radio.isChecked():
                    ExperienceLevelManager.set_level(level_map[key])
                    return
            ExperienceLevelManager.set_level(ExperienceLevel.BEGINNER)
        except (ImportError, RuntimeError) as e:
            logger.debug("Failed to set experience level: %s", e)

    def _build_step2(self) -> QWidget:
        """Step 3 - Use Case Selection."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = QLabel(self.tr("\U0001f3af Step 3: Choose Your Use Case"))
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
        desc.setObjectName("wizardDesc")
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
            radio.setObjectName("wizardUseCaseRadio")
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

        header = QLabel(self.tr("\u2705 Step 6: Review & Apply"))
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
        desc.setObjectName("wizardDesc")
        layout.addWidget(desc)

        # Summary card
        card = QFrame()
        card.setObjectName("wizardSummaryCard")
        card_layout = QVBoxLayout(card)

        self._lbl_summary = QLabel()
        self._lbl_summary.setWordWrap(True)
        self._lbl_summary.setObjectName("wizardSummaryText")
        self._lbl_summary.setTextFormat(Qt.TextFormat.PlainText)
        card_layout.addWidget(self._lbl_summary)

        layout.addWidget(card, 1)

        # Apply feedback label (v47.0)
        self._apply_feedback_label = QLabel()
        self._apply_feedback_label.setWordWrap(True)
        self._apply_feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._apply_feedback_label)

        return page

    # -- Navigation logic -----------------------------------------------

    def _set_step(self, index: int):
        """Switch visible step and update buttons."""
        index = max(0, min(index, 5))
        self._stack.setCurrentIndex(index)

        step_names = [
            self.tr("Step 1 of 6: Detection"),
            self.tr("Step 2 of 6: Experience Level"),
            self.tr("Step 3 of 6: Use Case"),
            self.tr("Step 4 of 6: Health Check"),
            self.tr("Step 5 of 6: Recommendations"),
            self.tr("Step 6 of 6: Apply"),
        ]
        self._step_label.setText(step_names[index])
        self._progress_bar.setValue(index + 1)

        self._btn_back.setVisible(index > 0)

        if index < 5:
            self._btn_next.setText(self.tr("Next \u2192"))
            self._btn_next.setProperty("wizardMode", "next")
        else:
            self._btn_next.setText(self.tr("\u2705 Apply"))
            self._btn_next.setProperty("wizardMode", "apply")
        style = self._btn_next.style()
        if style is not None:
            style.unpolish(self._btn_next)
            style.polish(self._btn_next)

        # Populate contents when entering a step
        if index == 0:
            self._populate_step1()
        elif index == 3:
            self._populate_health()
        elif index == 4:
            self._populate_actions()
        elif index == 5:
            self._populate_step3()

    def _go_next(self):
        current = self._stack.currentIndex()
        if current == 1:
            self._capture_experience_level()
        if current == 2:
            self._capture_use_case()
        if current < 5:
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

        # Show apply feedback (v47.0)
        if hasattr(self, "_apply_feedback_label"):
            self._apply_feedback_label.setText(
                self.tr("\u2705 Setup complete! Your preferences have been saved.")
            )
            self._apply_feedback_label.setStyleSheet(
                "color: #2ecc71; font-weight: bold; padding: 8px;"
            )

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
        form_factor = (
            self.tr("Laptop (battery detected)")
            if self._is_laptop
            else self.tr("Desktop")
        )
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

        header = QLabel(self.tr("\U0001fa7a Step 4: System Health Check"))
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
        desc.setObjectName("wizardDesc")
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

        header = QLabel(self.tr("\U0001f4cb Step 5: Recommended Actions"))
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
        desc.setObjectName("wizardDesc")
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
        # Clear previous results
        while self._health_layout.count() > 1:
            item = self._health_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        checks, self._health_results = WizardHealth.run_health_checks()

        # Display results
        for icon, text, level in checks:
            lbl = QLabel(f"  {icon}  {text}")
            lbl.setWordWrap(True)
            _health_names = {
                "ok": "wizardHealthOk",
                "warning": "wizardHealthWarning",
                "info": "wizardHealthInfo",
                "unknown": "wizardHealthUnknown",
            }
            lbl.setObjectName(_health_names.get(level, "wizardHealthUnknown"))
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
            recommendations.append(
                {
                    "text": "Run disk cleanup (remove old kernels, clear caches)",
                    "risk": "LOW",
                    "checked": True,
                }
            )

        if results.get("pkg_healthy") is False:
            recommendations.append(
                {
                    "text": "Fix package duplicates (dnf check --duplicates)",
                    "risk": "MEDIUM",
                    "checked": True,
                }
            )

        if results.get("firewall_running") is False:
            recommendations.append(
                {
                    "text": "Enable firewall (firewalld)",
                    "risk": "LOW",
                    "checked": True,
                }
            )

        if results.get("backup_tool") is None:
            recommendations.append(
                {
                    "text": "Install backup tool (timeshift recommended)",
                    "risk": "LOW",
                    "checked": True,
                }
            )

        selinux = results.get("selinux", "")
        if selinux and selinux != "Enforcing":
            recommendations.append(
                {
                    "text": f"SELinux is {selinux} — consider enabling Enforcing mode",
                    "risk": "MEDIUM",
                    "checked": False,
                }
            )

        # Always suggest these
        recommendations.append(
            {
                "text": "Configure automatic system snapshots before updates",
                "risk": "LOW",
                "checked": True,
            }
        )

        if not recommendations:
            lbl = QLabel(self.tr("  ✅ Your system looks great! No actions needed."))
            lbl.setObjectName("wizardNoActions")
            self._actions_layout.insertWidget(0, lbl)
            return

        for rec in recommendations:
            _action_names = {
                "LOW": "wizardActionLow",
                "MEDIUM": "wizardActionMedium",
                "HIGH": "wizardActionHigh",
            }
            cb = QCheckBox(f"  [{rec['risk']}] {rec['text']}")
            cb.setChecked(rec["checked"])
            cb.setObjectName(_action_names.get(rec["risk"], "wizardActionLow"))
            self._action_checkboxes.append(cb)
            self._actions_layout.insertWidget(self._actions_layout.count() - 1, cb)
