"""
Desktop Tab - Consolidated Window Management + Theming interface.
Part of v11.0 "Aurora Update" - merges Director and Theming tabs.

Sub-tabs:
- Window Manager: Compositor detection, tiling config, workspace templates, dotfile sync
- Theming: KDE global themes, icon themes, fonts
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QTextEdit, QScrollArea,
    QFrame, QLineEdit, QTabWidget
)

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs, CONTENT_MARGINS
from utils.tiling import TilingManager, DotfileManager
from utils.kwin_tiling import KWinManager
from core.plugins.metadata import PluginMetadata


class DesktopTab(BaseTab):
    """Consolidated Desktop tab: Window Manager + Theming."""

    _METADATA = PluginMetadata(
        id="desktop",
        name="Desktop",
        description="Window manager configuration, tiling setup, theming, and dotfile synchronization.",
        category="Personalize",
        icon="🎨",
        badge="",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the UI with sub-tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*CONTENT_MARGINS)

        # Sub-tab widget
        self.sub_tabs = QTabWidget()
        configure_top_tabs(self.sub_tabs)
        layout.addWidget(self.sub_tabs)

        # Sub-tab 1: Window Manager (from DirectorTab)
        self.sub_tabs.addTab(
            self._create_wm_tab(), self.tr("Window Manager")
        )

        # Sub-tab 2: Theming (from ThemingTab)
        self.sub_tabs.addTab(
            self._create_theming_tab(), self.tr("Theming")
        )

        # Shared output area at bottom
        self.add_output_section(layout)

    # ================================================================
    # WINDOW MANAGER SUB-TAB (from DirectorTab)
    # ================================================================

    def _create_wm_tab(self) -> QWidget:
        """Create the Window Manager sub-tab content."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        wm_layout = QVBoxLayout(container)
        wm_layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("Window Management"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        wm_layout.addWidget(header)

        # Compositor detection
        wm_layout.addWidget(self._create_compositor_section())

        # Tiling configuration
        wm_layout.addWidget(self._create_tiling_section())

        # Workspace templates
        wm_layout.addWidget(self._create_workspaces_section())

        # Dotfiles
        wm_layout.addWidget(self._create_dotfiles_section())

        wm_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_compositor_section(self) -> QGroupBox:
        """Create compositor detection section."""
        group = QGroupBox(self.tr("Compositor"))
        layout = QVBoxLayout(group)

        # Detect compositor
        compositor = "unknown"
        compositor_name = "Unknown"

        if KWinManager.is_kde():
            compositor = "kde"
            session_type = "Wayland" if KWinManager.is_wayland() else "X11"
            compositor_name = f"KDE Plasma ({session_type})"
        elif TilingManager.is_hyprland():
            compositor = "hyprland"
            compositor_name = "Hyprland"
        elif TilingManager.is_sway():
            compositor = "sway"
            compositor_name = "Sway"

        self.compositor = compositor

        comp_label = QLabel(self.tr("Detected: {}").format(compositor_name))
        comp_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(comp_label)

        # Quick actions based on compositor
        if compositor == "kde":
            info = QLabel(self.tr(
                "KWin provides native quick-tiling with keyboard shortcuts. "
                "Use Meta+Arrow keys or configure custom bindings below."
            ))
        elif compositor in ["hyprland", "sway"]:
            config_path = str(TilingManager.get_config_path())
            info = QLabel(self.tr("Config: {}").format(config_path))
        else:
            info = QLabel(self.tr("Install Hyprland, Sway, or KDE for tiling support."))

        info.setWordWrap(True)
        info.setStyleSheet("color: #9da7bf; font-size: 11px;")
        layout.addWidget(info)

        return group

    def _create_tiling_section(self) -> QGroupBox:
        """Create tiling configuration section."""
        group = QGroupBox(self.tr("Tiling Configuration"))
        layout = QVBoxLayout(group)

        # Keybinding presets
        layout.addWidget(QLabel(self.tr("Quick Tiling Keybinding Preset:")))

        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Vim Style (H/J/K/L)", "vim")
        self.preset_combo.addItem("Arrow Keys", "arrows")
        preset_layout.addWidget(self.preset_combo)

        apply_btn = QPushButton(self.tr("Apply Preset"))
        apply_btn.clicked.connect(self._apply_keybinding_preset)
        preset_layout.addWidget(apply_btn)

        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        # KDE-specific options
        if self.compositor == "kde":
            kde_layout = QHBoxLayout()

            enable_tiling_btn = QPushButton(self.tr("Enable Quick Tiling"))
            enable_tiling_btn.clicked.connect(self._enable_kde_tiling)
            kde_layout.addWidget(enable_tiling_btn)

            install_script_btn = QPushButton(self.tr("Install Tiling Script"))
            install_script_btn.clicked.connect(self._install_kwin_script)
            kde_layout.addWidget(install_script_btn)

            reconfigure_btn = QPushButton(self.tr("Reload KWin"))
            reconfigure_btn.clicked.connect(self._reconfigure_kwin)
            kde_layout.addWidget(reconfigure_btn)

            kde_layout.addStretch()
            layout.addLayout(kde_layout)

        # Hyprland/Sway reload
        elif self.compositor in ["hyprland", "sway"]:
            reload_btn = QPushButton(self.tr("Reload Config"))
            reload_btn.clicked.connect(self._reload_wm_config)
            layout.addWidget(reload_btn)

        return group

    def _create_workspaces_section(self) -> QGroupBox:
        """Create workspace templates section."""
        group = QGroupBox(self.tr("Workspace Templates"))
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel(self.tr("Apply a workspace template to organize apps:")))

        template_layout = QHBoxLayout()

        self.template_combo = QComboBox()
        for key, template in TilingManager.WORKSPACE_TEMPLATES.items():
            self.template_combo.addItem(template["name"], key)
        template_layout.addWidget(self.template_combo)

        preview_btn = QPushButton(self.tr("Preview"))
        preview_btn.clicked.connect(self._preview_template)
        template_layout.addWidget(preview_btn)

        apply_btn = QPushButton(self.tr("Generate Config"))
        apply_btn.clicked.connect(self._generate_template_config)
        template_layout.addWidget(apply_btn)

        template_layout.addStretch()
        layout.addLayout(template_layout)

        # Template preview
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setMaximumHeight(100)
        self.template_preview.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.template_preview)

        return group

    def _create_dotfiles_section(self) -> QGroupBox:
        """Create dotfiles sync section."""
        group = QGroupBox(self.tr("Dotfile Sync"))
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel(self.tr(
            "Sync your config files to a git repository for backup and sharing."
        )))

        # Repository path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel(self.tr("Repo Path:")))

        self.dotfile_path = QLineEdit()
        self.dotfile_path.setText(str(Path.home() / "dotfiles"))
        path_layout.addWidget(self.dotfile_path)

        create_btn = QPushButton(self.tr("Create Repo"))
        create_btn.clicked.connect(self._create_dotfile_repo)
        path_layout.addWidget(create_btn)

        layout.addLayout(path_layout)

        # Sync buttons
        sync_layout = QHBoxLayout()

        for name in ["hyprland", "sway", "kitty", "fish", "nvim"]:
            if name in DotfileManager.DOTFILES:
                btn = QPushButton(self.tr("Sync {}").format(name))
                btn.clicked.connect(lambda checked, n=name: self._sync_dotfile(n))
                btn.setMaximumWidth(100)
                sync_layout.addWidget(btn)

        sync_layout.addStretch()
        layout.addLayout(sync_layout)

        return group

    # -- Window Manager actions --

    def _apply_keybinding_preset(self):
        """Apply selected keybinding preset."""
        preset = self.preset_combo.currentData()

        if self.compositor == "kde":
            result = KWinManager.apply_tiling_preset(preset)
        else:
            self.append_output(
                self.tr("Generate keybindings for {} preset manually for {}\n").format(
                    preset, self.compositor
                )
            )
            return

        self.append_output(result.message + "\n")

    def _enable_kde_tiling(self):
        """Enable KDE quick tiling."""
        result = KWinManager.enable_quick_tiling()
        self.append_output(result.message + "\n")

    def _install_kwin_script(self):
        """Install KWin tiling script."""
        result = KWinManager.install_tiling_script()
        self.append_output(result.message + "\n")

    def _reconfigure_kwin(self):
        """Reconfigure KWin."""
        result = KWinManager.reconfigure_kwin()
        self.append_output(result.message + "\n")

    def _reload_wm_config(self):
        """Reload tiling WM config."""
        result = TilingManager.reload_config()
        self.append_output(result.message + "\n")

    def _preview_template(self):
        """Preview workspace template."""
        template_key = self.template_combo.currentData()
        template = TilingManager.WORKSPACE_TEMPLATES.get(template_key, {})

        preview_lines = [self.tr("Template: {}").format(template.get('name', template_key))]

        for ws_num, ws_config in template.get("workspaces", {}).items():
            apps = ", ".join(ws_config.get("apps", []))
            preview_lines.append(
                self.tr("  Workspace {} ({}): {}").format(ws_num, ws_config['name'], apps)
            )

        self.template_preview.setText("\n".join(preview_lines))

    def _generate_template_config(self):
        """Generate config for selected template."""
        template_key = self.template_combo.currentData()
        result = TilingManager.generate_workspace_template(template_key)

        if result.success:
            self.template_preview.setText(result.data.get("config", ""))
            self.append_output(
                self.tr("Config generated for {}. Copy to your config file.\n").format(template_key)
            )
        else:
            self.append_output(result.message + "\n")

    def _create_dotfile_repo(self):
        """Create dotfile repository."""
        repo_path = Path(self.dotfile_path.text())
        result = DotfileManager.create_dotfile_repo(repo_path)
        self.append_output(result.message + "\n")

    def _sync_dotfile(self, name: str):
        """Sync a dotfile to repo."""
        repo_path = Path(self.dotfile_path.text())
        result = DotfileManager.sync_dotfile(name, repo_path)
        self.append_output(result.message + "\n")

    # ================================================================
    # THEMING SUB-TAB (from ThemingTab)
    # ================================================================

    def _create_theming_tab(self) -> QWidget:
        """Create the Theming sub-tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # KDE Global Theme Group
        theme_group = QGroupBox(self.tr("KDE Plasma Global Theme"))
        theme_layout = QVBoxLayout()
        theme_group.setLayout(theme_layout)

        theme_layout.addWidget(QLabel(self.tr("Select a theme to apply:")))

        self.theme_combo = QComboBox()
        self.themes = {
            self.tr("Breeze Dark"): "org.kde.breezedark.desktop",
            self.tr("Breeze Light"): "org.kde.breeze.desktop",
            self.tr("Oxygen"): "org.kde.oxygen"
        }
        for name in self.themes.keys():
            self.theme_combo.addItem(name)
        theme_layout.addWidget(self.theme_combo)

        btn_apply_theme = QPushButton(self.tr("Apply Theme"))
        btn_apply_theme.clicked.connect(self._apply_theme)
        theme_layout.addWidget(btn_apply_theme)

        layout.addWidget(theme_group)

        # Icon Theme Group
        icon_group = QGroupBox(self.tr("Install Popular Icon Themes"))
        icon_layout = QHBoxLayout()
        icon_group.setLayout(icon_layout)

        btn_papirus = QPushButton(self.tr("Install Papirus Icons"))
        btn_papirus.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["dnf", "install", "-y", "papirus-icon-theme"],
                self.tr("Installing Papirus Icons...")
            )
        )
        icon_layout.addWidget(btn_papirus)

        btn_tela = QPushButton(self.tr("Install Tela Icons"))
        btn_tela.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["dnf", "install", "-y", "tela-icon-theme"],
                self.tr("Installing Tela Icons...")
            )
        )
        icon_layout.addWidget(btn_tela)

        layout.addWidget(icon_group)

        # Fonts Group
        fonts_group = QGroupBox(self.tr("Install Popular Fonts"))
        fonts_layout = QHBoxLayout()
        fonts_group.setLayout(fonts_layout)

        btn_firacode = QPushButton(self.tr("FiraCode Nerd Font"))
        btn_firacode.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["dnf", "install", "-y", "fira-code-fonts"],
                self.tr("Installing FiraCode...")
            )
        )
        fonts_layout.addWidget(btn_firacode)

        btn_jetbrains = QPushButton(self.tr("JetBrains Mono"))
        btn_jetbrains.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["dnf", "install", "-y", "jetbrains-mono-fonts"],
                self.tr("Installing JetBrains Mono...")
            )
        )
        fonts_layout.addWidget(btn_jetbrains)

        layout.addWidget(fonts_group)

        layout.addStretch()
        return widget

    # -- Theming actions --

    def _apply_theme(self):
        """Apply the selected KDE global theme."""
        theme_name = self.theme_combo.currentText()
        theme_id = self.themes.get(theme_name, "org.kde.breeze.desktop")
        self.run_command(
            "lookandfeeltool", ["-a", theme_id],
            self.tr("Applying {} theme...").format(theme_name)
        )
