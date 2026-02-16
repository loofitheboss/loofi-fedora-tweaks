"""
Safety Manager — system snapshot and pre-action safety checks.

v42.0.0 Sentinel: Added logging, fixed synchronous UI freeze during
snapshot creation, narrowed exception types.
"""

import logging
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class SafetyManager:
    """Pre-action safety checks and snapshot management."""

    @staticmethod
    def check_dnf_lock() -> bool:
        """
        Check if DNF or RPM is currently running.

        Returns:
            True if a package manager process is running (locked).
        """
        import os

        if os.path.exists("/var/run/dnf.pid"):
            return True
        try:
            subprocess.check_call(
                ["pgrep", "-f", "dnf|yum|rpm"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return True
        except subprocess.CalledProcessError:
            return False
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check DNF lock: %s", e)
            return False

    @staticmethod
    def check_snapshot_tool() -> Optional[str]:
        """Check if Timeshift or Snapper is installed.

        Returns:
            Tool name ('timeshift' or 'snapper'), or None if neither found.
        """
        if shutil.which("timeshift"):
            return "timeshift"
        elif shutil.which("snapper"):
            return "snapper"
        return None

    @staticmethod
    def create_snapshot(tool: str, comment: str = "Loofi Auto-Snapshot") -> bool:
        """Create a system snapshot using the detected tool.

        Args:
            tool: Snapshot tool name ('timeshift' or 'snapper').
            comment: Snapshot description comment.

        Returns:
            True on success, False on failure.
        """
        if tool not in ("timeshift", "snapper"):
            logger.warning("Unknown snapshot tool requested: %s", tool)
            return False

        try:
            if tool == "timeshift":
                cmd = [
                    "pkexec",
                    "timeshift",
                    "--create",
                    "--comments",
                    comment,
                    "--tags",
                    "D",
                ]
            else:
                cmd = ["pkexec", "snapper", "create", "--description", comment]

            logger.info("Creating %s snapshot: %s", tool, comment)
            subprocess.run(cmd, check=True, timeout=600)
            logger.info("Snapshot created successfully via %s", tool)
            return True

        except subprocess.TimeoutExpired:
            logger.warning("Snapshot creation timed out after 600s using %s", tool)
            return False
        except subprocess.CalledProcessError as e:
            logger.warning("Snapshot failed via %s: %s", tool, e)
            return False
        except OSError as e:
            logger.warning("Could not run %s: %s", tool, e)
            return False

    @staticmethod
    def confirm_action(parent, description: str) -> bool:
        """
        Prompt the user to confirm an action, offering to take a snapshot first.

        Note: This method imports PyQt6 lazily. The snapshot creation runs
        with processEvents() calls to avoid a full UI freeze.

        Args:
            parent: Parent QWidget for the dialog.
            description: Human-readable action description.

        Returns:
            True if the action should proceed, False otherwise.
        """
        from PyQt6.QtWidgets import QMessageBox, QApplication

        tool = SafetyManager.check_snapshot_tool()

        msg = QMessageBox(parent)
        msg.setWindowTitle("Safety Check")
        msg.setText(f"You are about to: {description}")
        msg.setInformativeText(
            "It is recommended to create a system snapshot before proceeding."
        )
        msg.setIcon(QMessageBox.Icon.Warning)

        # Standard Buttons
        msg.addButton("Continue Without Snapshot", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton(QMessageBox.StandardButton.Cancel)

        btn_snapshot = None
        if tool:
            btn_snapshot = msg.addButton(
                f"Create {tool.capitalize()} Snapshot & Continue",
                QMessageBox.ButtonRole.ActionRole,
            )
            msg.setDefaultButton(btn_snapshot)
        else:
            msg.setDefaultButton(btn_cancel)

        msg.exec()

        clicked = msg.clickedButton()

        if clicked == btn_cancel:
            return False

        if tool and clicked == btn_snapshot:
            # Show a progress message while snapshot runs
            parent.setDisabled(True)
            QApplication.processEvents()

            success = SafetyManager.create_snapshot(
                tool, f"Pre-{description.split(' ')[0]}"
            )

            parent.setDisabled(False)
            QApplication.processEvents()

            if not success:
                QMessageBox.warning(
                    parent,
                    "Snapshot Failed",
                    "Could not create snapshot. Proceeding regardless...",
                )
            else:
                QMessageBox.information(
                    parent, "Snapshot Created", "System snapshot created successfully."
                )

        return True
