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
        btn_apply_theme.clicked.connect(self.apply_theme)
        theme_layout.addWidget(btn_apply_theme)
        
        layout.addWidget(theme_group)

        # Icon Theme Group
        icon_group = QGroupBox(self.tr("Install Popular Icon Themes"))
        icon_layout = QHBoxLayout()
        icon_group.setLayout(icon_layout)
        
        btn_papirus = QPushButton(self.tr("Install Papirus Icons"))
        btn_papirus.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "papirus-icon-theme"], self.tr("Installing Papirus Icons...")))
        icon_layout.addWidget(btn_papirus)
        
        btn_tela = QPushButton(self.tr("Install Tela Icons"))
        btn_tela.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "tela-icon-theme"], self.tr("Installing Tela Icons...")))
        icon_layout.addWidget(btn_tela)
        
        layout.addWidget(icon_group)

        # Fonts Group
        fonts_group = QGroupBox(self.tr("Install Popular Fonts"))
        fonts_layout = QHBoxLayout()
        fonts_group.setLayout(fonts_layout)
        
        btn_firacode = QPushButton(self.tr("FiraCode Nerd Font"))
        btn_firacode.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "fira-code-fonts"], self.tr("Installing FiraCode...")))
        fonts_layout.addWidget(btn_firacode)
        
        btn_jetbrains = QPushButton(self.tr("JetBrains Mono"))
        btn_jetbrains.clicked.connect(lambda: self.run_command("pkexec", ["dnf", "install", "-y", "jetbrains-mono-fonts"], self.tr("Installing JetBrains Mono...")))
        fonts_layout.addWidget(btn_jetbrains)
        
        layout.addWidget(fonts_group)

        layout.addWidget(QLabel(self.tr("Output Log:")))
        layout.addWidget(self.output_area)

    def apply_theme(self):
        theme_name = self.theme_combo.currentText()
        theme_id = self.themes.get(theme_name, "org.kde.breeze.desktop")
        # Use lookandfeeltool to apply the theme
        self.run_command("lookandfeeltool", ["-a", theme_id], self.tr("Applying {} theme...").format(theme_name))

    def run_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(self.tr("\nCommand finished with exit code: {}").format(exit_code))
