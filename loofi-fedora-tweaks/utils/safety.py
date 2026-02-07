import shutil
import subprocess
from PyQt6.QtWidgets import QMessageBox

class SafetyManager:
    @staticmethod
    def check_snapshot_tool():
        """Check if Timeshift or Snapper is installed."""
        if shutil.which("timeshift"):
            return "timeshift"
        elif shutil.which("snapper"):
            return "snapper"
        return None

    @staticmethod
    def create_snapshot(tool, comment="Loofi Auto-Snapshot"):
        """Create a system snapshot using the detected tool."""
        try:
            if tool == "timeshift":
                # Timeshift needs root, but prompts usually handled by GUI or we run this via pkexec if needed.
                # Here we assume the user might need to enter password if not running as root.
                # However, for a CLI non-interactive snapshot:
                cmd = ["pkexec", "timeshift", "--create", "--comments", comment, "--tags", "D"]
                subprocess.run(cmd, check=True)
                return True
            elif tool == "snapper":
                cmd = ["pkexec", "snapper", "create", "--description", comment]
                subprocess.run(cmd, check=True)
                return True
        except subprocess.CalledProcessError:
            return False
        return False

    @staticmethod
    def confirm_action(parent, description):
        """
        Prompt the user to confirm an action, offering to take a snapshot first.
        Returns True if the action should proceed, False otherwise.
        """
        tool = SafetyManager.check_snapshot_tool()
        
        msg = QMessageBox(parent)
        msg.setWindowTitle("Safety Check")
        msg.setText(f"You are about to: {description}")
        msg.setInformativeText("It is recommended to create a system snapshot before proceeding.")
        msg.setIcon(QMessageBox.Icon.Warning)
        
        # Standard Buttons
        btn_continue = msg.addButton("Continue Without Snapshot", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton(QMessageBox.StandardButton.Cancel)
        
        btn_snapshot = None
        if tool:
            btn_snapshot = msg.addButton(f"Create {tool.capitalize()} Snapshot & Continue", QMessageBox.ButtonRole.ActionRole)
            msg.setDefaultButton(btn_snapshot)
        else:
            msg.setDefaultButton(btn_cancel)
            
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == btn_cancel:
            return False
            
        if tool and clicked == btn_snapshot:
            # Create snapshot
            parent.setDisabled(True) # Prevent interaction during snapshot
            success = SafetyManager.create_snapshot(tool, f"Pre-{description.split(' ')[0]}")
            parent.setDisabled(False)
            
            if not success:
               QMessageBox.warning(parent, "Snapshot Failed", "Could not create snapshot. Proceeding regardless...")
            else:
               QMessageBox.information(parent, "Snapshot Created", "System snapshot created successfully.")
               
        return True
