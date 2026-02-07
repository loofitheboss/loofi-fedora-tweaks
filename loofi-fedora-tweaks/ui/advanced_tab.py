from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QHBoxLayout, QTextEdit
from utils.process import CommandRunner

class AdvancedTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # DNF Optimization Group
        dnf_group = QGroupBox("DNF Package Manager Optimization")
        dnf_layout = QVBoxLayout()
        dnf_group.setLayout(dnf_layout)
        
        btn_dnf_opt = QPushButton("Apply DNF Speed Tweaks (Parallel Downloads & Fastest Mirror)")
        # We'll use a shell script via pkexec sh -c to safely append/modify config
        dnf_cmd = "grep -q 'max_parallel_downloads' /etc/dnf/dnf.conf || echo 'max_parallel_downloads=10' >> /etc/dnf/dnf.conf; grep -q 'fastestmirror' /etc/dnf/dnf.conf || echo 'fastestmirror=True' >> /etc/dnf/dnf.conf"
        btn_dnf_opt.clicked.connect(lambda: self.run_command("pkexec", ["sh", "-c", dnf_cmd], "Applying DNF Optimizations..."))
        dnf_layout.addWidget(btn_dnf_opt)
        layout.addWidget(dnf_group)

        # Network Optimization Group
        net_group = QGroupBox("Network Optimization")
        net_layout = QVBoxLayout()
        net_group.setLayout(net_layout)
        
        btn_bbr = QPushButton("Enable TCP BBR Congestion Control")
        # Create a sysctl config file
        bbr_cmd = "echo 'net.core.default_qdisc=fq' > /etc/sysctl.d/99-bbr.conf && echo 'net.ipv4.tcp_congestion_control=bbr' >> /etc/sysctl.d/99-bbr.conf && sysctl --system"
        btn_bbr.clicked.connect(lambda: self.run_command("pkexec", ["sh", "-c", bbr_cmd], "Enabling TCP BBR..."))
        net_layout.addWidget(btn_bbr)
        layout.addWidget(net_group)

        # Gaming Optimization Group
        game_group = QGroupBox("Gaming Optimization")
        game_layout = QVBoxLayout()
        game_group.setLayout(game_layout)
        
        btn_gamemode = QPushButton("Install & Enable GameMode")
        # Install gamemode and add user to group. $USER might not work in pkexec sh -c directly as expected if not passed correctly, so we assume current user.
        # Actually $USER inside 'sh -c' wrapped in pkexec might be root. We need to pass the actual username.
        import getpass
        current_user = getpass.getuser()
        gamemode_cmd = f"dnf install -y gamemode && usermod -aG gamemode {current_user}"
        btn_gamemode.clicked.connect(lambda: self.run_command("pkexec", ["sh", "-c", gamemode_cmd], f"Installing GameMode for user {current_user}..."))
        game_layout.addWidget(btn_gamemode)
        layout.addWidget(game_group)
        
        # Swappiness
        swap_group = QGroupBox("Memory Management (Swappiness)")
        swap_layout = QVBoxLayout()
        swap_group.setLayout(swap_layout)
        
        btn_swap = QPushButton("Reduce Swappiness to 10 (Better for SSD/RAM)")
        swap_cmd = "echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf && sysctl --system"
        btn_swap.clicked.connect(lambda: self.run_command("pkexec", ["sh", "-c", swap_cmd], "Setting Swappiness to 10..."))
        swap_layout.addWidget(btn_swap)
        layout.addWidget(swap_group)

        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)

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
