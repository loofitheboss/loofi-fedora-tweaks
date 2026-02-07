from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QHBoxLayout, QTextEdit, QComboBox
from utils.process import CommandRunner

class ThemingTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # KDE Global Theme Group
        theme_group = QGroupBox("KDE Plasma Global Theme")
        theme_layout = QVBoxLayout()
        theme_group.setLayout(theme_layout)
        
        theme_layout.addWidget(QLabel("Select a theme to apply:"))
        
        self.theme_combo = QComboBox()
        self.themes = {
            "Breeze Dark": "org.kde.breezedark.desktop",
            "Breeze Light": "org.kde.breeze.desktop",
            "Oxygen": "org.kde.oxygen"
        }
        for name in self.themes.keys():
            self.theme_combo.addItem(name)
        theme_layout.addWidget(self.theme_combo)
        
        btn_apply_theme = QPushButton("Apply Theme")
        btn_apply_theme.clicked.connect(self.apply_theme)
        theme_layout.addWidget(btn_apply_theme)
        
        layout.addWidget(theme_group)

        # Icon Theme Group
        icon_group = QGroupBox("Install Popular Icon Themes")
        icon_layout = QHBoxLayout()
        icon_group.setLayout(icon_layout)
        
        btn_papirus = QPushButton("Install Papirus Icons")
        btn_papirus.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "papirus-icon-theme"], "Installing Papirus Icons..."))
        icon_layout.addWidget(btn_papirus)
        
        btn_tela = QPushButton("Install Tela Icons")
        btn_tela.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "tela-icon-theme"], "Installing Tela Icons..."))
        icon_layout.addWidget(btn_tela)
        
        layout.addWidget(icon_group)

        # Fonts Group
        fonts_group = QGroupBox("Install Popular Fonts")
        fonts_layout = QHBoxLayout()
        fonts_group.setLayout(fonts_layout)
        
        btn_firacode = QPushButton("FiraCode Nerd Font")
        btn_firacode.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "fira-code-fonts"], "Installing FiraCode..."))
        fonts_layout.addWidget(btn_firacode)
        
        btn_jetbrains = QPushButton("JetBrains Mono")
        btn_jetbrains.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "jetbrains-mono-fonts"], "Installing JetBrains Mono..."))
        fonts_layout.addWidget(btn_jetbrains)
        
        layout.addWidget(fonts_group)

        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)

    def apply_theme(self):
        theme_name = self.theme_combo.currentText()
        theme_id = self.themes.get(theme_name, "org.kde.breeze.desktop")
        # Use lookandfeeltool to apply the theme
        self.run_command("lookandfeeltool", ["-a", theme_id], f"Applying {theme_name} theme...")

    def run_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(f"\nCommand finished with exit code: {exit_code}")
