"""
Software Tab - Consolidated tab merging Applications and Repositories.
Part of v11.0 "Aurora Update".

Uses QTabWidget for sub-navigation to preserve all features from the
original AppsTab and ReposTab.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QGroupBox, QScrollArea, QFrame, QTabWidget
)

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs
from utils.command_runner import CommandRunner
from core.plugins.metadata import PluginMetadata

import shlex
import subprocess


# ---------------------------------------------------------------------------
# Sub-tab: Applications
# ---------------------------------------------------------------------------

class _ApplicationsSubTab(QWidget):
    """Sub-tab containing all application management functionality.

    Preserves every feature from the original AppsTab:
    - Remote/cached app config loading via AppConfigFetcher
    - Scrollable app list with install status check
    - Per-app install buttons (green = installed, clickable = available)
    - Refresh Status button
    - Output log with command feedback
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header with Refresh Button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(self.tr("Essential Applications")))
        header_layout.addStretch()
        btn_refresh = QPushButton(self.tr("Refresh Status"))
        btn_refresh.clicked.connect(self.refresh_list)
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        # Scroll Area for apps list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        scroll.setWidget(self.scroll_content)

        layout.addWidget(scroll)

        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)

        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # Load Apps
        self.apps = self.load_apps()
        self.refresh_list()

        layout.addWidget(QLabel(self.tr("Output Log:")))
        layout.addWidget(self.output_area)

    def load_apps(self):
        """Start asynchronous loading of the app catalogue."""
        from utils.remote_config import AppConfigFetcher

        self.fetcher = AppConfigFetcher()
        self.fetcher.config_ready.connect(self.on_apps_loaded)
        self.fetcher.config_error.connect(self.on_apps_error)
        self.fetcher.start()
        return []  # Populated asynchronously

    def on_apps_loaded(self, apps):
        self.apps = apps
        self.refresh_list()
        self.append_output(self.tr("Apps list updated from remote/cache.\n"))

    def on_apps_error(self, error):
        self.append_output(self.tr("Error loading apps: {}\n").format(error))

    def refresh_list(self):
        """Clear and rebuild the apps list."""
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for app in self.apps:
            self.add_app_row(self.scroll_layout, app)
        self.scroll_layout.addStretch()

    def add_app_row(self, layout, app_data):
        """Add a single app row with name, description, and install button."""
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Shape.StyledPanel)
        row_layout = QHBoxLayout()
        row_widget.setLayout(row_layout)

        # Defensive access for potentially missing keys
        app_name = app_data.get("name", "Unknown App")
        app_desc = app_data.get("desc", app_data.get("description", ""))

        lbl_name = QLabel(f"<b>{app_name}</b>")
        lbl_desc = QLabel(app_desc)

        btn_install = QPushButton(self.tr("Install"))

        # Check if installed
        chk_cmd = app_data.get("check_cmd")
        is_installed = False
        if chk_cmd:
            is_installed = self.check_installed(chk_cmd)

        if is_installed:
            btn_install.setText(self.tr("Installed"))
            btn_install.setEnabled(False)
            btn_install.setStyleSheet(
                "background-color: #2ecc71; color: white;"
            )
        else:
            btn_install.clicked.connect(
                lambda checked, app=app_data: self.install_app(app)
            )

        row_layout.addWidget(lbl_name)
        row_layout.addWidget(lbl_desc)
        row_layout.addStretch()
        row_layout.addWidget(btn_install)

        layout.addWidget(row_widget)

    def check_installed(self, cmd):
        """Run a check command silently to determine installation status."""
        try:
            subprocess.run(
                shlex.split(cmd), check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def install_app(self, app_data):
        self.output_area.clear()
        self.append_output(
            self.tr("Installing {}...\n").format(app_data["name"])
        )
        self.runner.run_command(app_data["cmd"], app_data["args"])

    def append_output(self, text):
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )

    def command_finished(self, exit_code):
        self.append_output(
            self.tr("\nCommand finished with exit code: {}").format(exit_code)
        )
        # Refresh list to update status if installation succeeded
        if exit_code == 0:
            self.refresh_list()


# ---------------------------------------------------------------------------
# Sub-tab: Repositories
# ---------------------------------------------------------------------------

class _RepositoriesSubTab(QWidget):
    """Sub-tab containing all repository management functionality.

    Preserves every feature from the original ReposTab:
    - RPM Fusion enable (Free & Non-Free)
    - Multimedia Codecs install
    - Flathub remote enable
    - COPR repository enable (Loofi Fedora Tweaks)
    - Output log
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("Repository Management"))
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # RPM Fusion Group
        fusion_group = QGroupBox(
            self.tr("RPM Fusion (Essential for media codecs & drivers)")
        )
        fusion_layout = QVBoxLayout()
        fusion_group.setLayout(fusion_layout)

        self.btn_enable_fusion = QPushButton(
            self.tr("Enable RPM Fusion (Free & Non-Free)")
        )
        self.btn_enable_fusion.clicked.connect(self.enable_rpm_fusion)
        fusion_layout.addWidget(self.btn_enable_fusion)

        self.btn_install_codecs = QPushButton(
            self.tr("Install Multimedia Codecs (ffmpeg, gstreamer, etc.)")
        )
        self.btn_install_codecs.clicked.connect(self.install_multimedia_codecs)
        fusion_layout.addWidget(self.btn_install_codecs)

        layout.addWidget(fusion_group)

        # Flatpak Flathub
        flathub_group = QGroupBox(self.tr("Flathub (Flatpak)"))
        flathub_layout = QVBoxLayout()
        flathub_group.setLayout(flathub_layout)

        self.btn_enable_flathub = QPushButton(
            self.tr("Enable Flathub Remote")
        )
        self.btn_enable_flathub.clicked.connect(self.enable_flathub)
        flathub_layout.addWidget(self.btn_enable_flathub)

        layout.addWidget(flathub_group)

        # COPR Repos Section
        copr_group = QGroupBox(self.tr("COPR Repositories"))
        copr_layout = QVBoxLayout()
        copr_group.setLayout(copr_layout)

        copr_layout.addWidget(QLabel(self.tr("Common COPR Repositories:")))

        self.btn_copr_loofi = QPushButton(
            self.tr("Enable Loofi Fedora Tweaks COPR")
        )
        self.btn_copr_loofi.clicked.connect(
            lambda: self.run_command(
                "pkexec",
                ["dnf", "copr", "enable", "-y",
                 "loofitheboss/loofi-fedora-tweaks"],
                self.tr("Enabling Loofi COPR..."),
            )
        )
        copr_layout.addWidget(self.btn_copr_loofi)

        layout.addWidget(copr_group)

        # Output Area
        layout.addWidget(QLabel(self.tr("Output Log:")))
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        layout.addWidget(self.output_area)

        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

    # -- Repository actions ------------------------------------------------

    def enable_rpm_fusion(self):
        cmd = (
            "dnf install -y "
            "https://mirrors.rpmfusion.org/free/fedora/"
            "rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm "
            "https://mirrors.rpmfusion.org/nonfree/fedora/"
            "rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm; "
            "dnf groupupdate -y core;"
        )
        self.run_command(
            "pkexec", ["sh", "-c", cmd],
            self.tr("Enabling RPM Fusion repositories..."),
        )

    def install_multimedia_codecs(self):
        cmd = (
            "dnf groupupdate -y multimedia "
            "--setop='install_weak_deps=False' "
            "--exclude=PackageKit-gstreamer-plugin && "
            "dnf groupupdate -y sound-and-video"
        )
        self.run_command(
            "pkexec", ["sh", "-c", cmd],
            self.tr("Installing Multimedia Codecs..."),
        )

    def enable_flathub(self):
        self.run_command(
            "flatpak",
            ["remote-add", "--if-not-exists", "flathub",
             "https://flathub.org/repo/flathub.flatpakrepo"],
            self.tr("Enabling Flathub..."),
        )

    # -- Helpers -----------------------------------------------------------

    def run_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )

    def command_finished(self, exit_code):
        self.append_output(
            self.tr("\nCommand finished with exit code: {}").format(exit_code)
        )


# ---------------------------------------------------------------------------
# Main consolidated tab
# ---------------------------------------------------------------------------

class SoftwareTab(BaseTab):
    """Consolidated software tab merging Applications and Repositories.

    Uses a QTabWidget for sub-navigation between the app installer
    and the repository manager.
    """

    _METADATA = PluginMetadata(
        id="software",
        name="Software",
        description="Application installer and repository management for Fedora packages.",
        category="Software",
        icon="📦",
        badge="recommended",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        configure_top_tabs(self.tabs)
        self.tabs.addTab(_ApplicationsSubTab(), self.tr("Applications"))
        self.tabs.addTab(_RepositoriesSubTab(), self.tr("Repositories"))

        layout.addWidget(self.tabs)
