"""
Director Tab - Window management and workspaces interface.
Part of v9.0 "Director" update.

Features:
- Tiling compositor detection (KDE/Hyprland/Sway)
- Workspace templates
- Keybinding presets
- Dotfile sync
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QTextEdit, QScrollArea, QFrame, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt

from utils.tiling import TilingManager, DotfileManager
from utils.kwin_tiling import KWinManager


class DirectorTab(QWidget):
    """Director tab for window management and tiling."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(self.tr("🎬 Director - Window Management"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #9b59b6;")
        layout.addWidget(header)
        
        # Compositor detection
        layout.addWidget(self._create_compositor_section())
        
        # Tiling configuration
        layout.addWidget(self._create_tiling_section())
        
        # Workspace templates
        layout.addWidget(self._create_workspaces_section())
        
        # Dotfiles
        layout.addWidget(self._create_dotfiles_section())
        
        # Log
        log_group = QGroupBox(self.tr("Output"))
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        layout.addStretch()
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_compositor_section(self) -> QGroupBox:
        """Create compositor detection section."""
        group = QGroupBox(self.tr("🖥️ Compositor"))
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
        
        comp_label = QLabel(f"✅ Detected: {compositor_name}")
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
            info = QLabel(self.tr(f"Config: {config_path}"))
        else:
            info = QLabel(self.tr("Install Hyprland, Sway, or KDE for tiling support."))
        
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)
        
        return group
    
    def _create_tiling_section(self) -> QGroupBox:
        """Create tiling configuration section."""
        group = QGroupBox(self.tr("⊞ Tiling Configuration"))
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
            
            reconfigure_btn = QPushButton(self.tr("🔄 Reload KWin"))
            reconfigure_btn.clicked.connect(self._reconfigure_kwin)
            kde_layout.addWidget(reconfigure_btn)
            
            kde_layout.addStretch()
            layout.addLayout(kde_layout)
        
        # Hyprland/Sway reload
        elif self.compositor in ["hyprland", "sway"]:
            reload_btn = QPushButton(self.tr("🔄 Reload Config"))
            reload_btn.clicked.connect(self._reload_wm_config)
            layout.addWidget(reload_btn)
        
        return group
    
    def _create_workspaces_section(self) -> QGroupBox:
        """Create workspace templates section."""
        group = QGroupBox(self.tr("📋 Workspace Templates"))
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
        group = QGroupBox(self.tr("📦 Dotfile Sync"))
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
                btn = QPushButton(f"Sync {name}")
                btn.clicked.connect(lambda checked, n=name: self._sync_dotfile(n))
                btn.setMaximumWidth(100)
                sync_layout.addWidget(btn)
        
        sync_layout.addStretch()
        layout.addLayout(sync_layout)
        
        return group
    
    def _apply_keybinding_preset(self):
        """Apply selected keybinding preset."""
        preset = self.preset_combo.currentData()
        
        if self.compositor == "kde":
            result = KWinManager.apply_tiling_preset(preset)
        else:
            # For Hyprland/Sway, generate config snippet
            self.log(f"Generate keybindings for {preset} preset manually for {self.compositor}")
            return
        
        self.log(result.message)
    
    def _enable_kde_tiling(self):
        """Enable KDE quick tiling."""
        result = KWinManager.enable_quick_tiling()
        self.log(result.message)
    
    def _install_kwin_script(self):
        """Install KWin tiling script."""
        result = KWinManager.install_tiling_script()
        self.log(result.message)
    
    def _reconfigure_kwin(self):
        """Reconfigure KWin."""
        result = KWinManager.reconfigure_kwin()
        self.log(result.message)
    
    def _reload_wm_config(self):
        """Reload tiling WM config."""
        result = TilingManager.reload_config()
        self.log(result.message)
    
    def _preview_template(self):
        """Preview workspace template."""
        template_key = self.template_combo.currentData()
        template = TilingManager.WORKSPACE_TEMPLATES.get(template_key, {})
        
        preview_lines = [f"Template: {template.get('name', template_key)}"]
        
        for ws_num, ws_config in template.get("workspaces", {}).items():
            apps = ", ".join(ws_config.get("apps", []))
            preview_lines.append(f"  Workspace {ws_num} ({ws_config['name']}): {apps}")
        
        self.template_preview.setText("\n".join(preview_lines))
    
    def _generate_template_config(self):
        """Generate config for selected template."""
        template_key = self.template_combo.currentData()
        result = TilingManager.generate_workspace_template(template_key)
        
        if result.success:
            self.template_preview.setText(result.data.get("config", ""))
            self.log(f"Config generated for {template_key}. Copy to your config file.")
        else:
            self.log(result.message)
    
    def _create_dotfile_repo(self):
        """Create dotfile repository."""
        from pathlib import Path
        repo_path = Path(self.dotfile_path.text())
        
        result = DotfileManager.create_dotfile_repo(repo_path)
        self.log(result.message)
    
    def _sync_dotfile(self, name: str):
        """Sync a dotfile to repo."""
        from pathlib import Path
        repo_path = Path(self.dotfile_path.text())
        
        result = DotfileManager.sync_dotfile(name, repo_path)
        self.log(result.message)
    
    def log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)


# Need to import Path for the create/sync methods
from pathlib import Path
