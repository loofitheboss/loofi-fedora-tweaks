"""
Permission Consent Dialog for Plugin Installation.
Part of v26.0 Plugin System.

Shows required permissions to user before plugin installation.
"""

from core.plugins.package import PluginPackage
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout


class PermissionConsentDialog(QDialog):
    """Dialog to show and request consent for plugin permissions."""

    def __init__(self, plugin_package: PluginPackage, parent=None):
        super().__init__(parent)
        self.plugin_package = plugin_package
        self.setWindowTitle(self.tr("Permission Request"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            self.tr("Plugin '{}' requests the following permissions:").format(
                self.plugin_package.metadata.name
            )
        )
        header.setWordWrap(True)
        header.setObjectName("consentHeader")
        layout.addWidget(header)

        # Permission list
        perms_text = QTextEdit()
        perms_text.setReadOnly(True)
        perms_text.setMinimumHeight(250)

        # Build permission description HTML
        perm_descriptions = {
            "system:execute": "Execute system commands with elevated privileges",
            "system:packages": "Install, update, or remove system packages",
            "system:services": "Manage system services (start, stop, enable, disable)",
            "system:files": "Read and modify system files outside the sandbox",
            "network:access": "Access the network (HTTP/HTTPS requests)",
            "network:sockets": "Create network sockets and listeners",
            "ui:integrate": "Add UI elements to the main application window",
            "ui:notifications": "Show system notifications",
            "data:config": "Read and modify application configuration",
            "data:logs": "Access application and system logs",
            "hardware:access": "Access hardware devices and sensors",
            "storage:write": "Write files to the filesystem",
        }

        html_lines = ["<ul>"]
        for perm in self.plugin_package.manifest.permissions:
            desc = perm_descriptions.get(perm, "Unknown permission")
            html_lines.append(f"<li><b>{perm}</b>: {desc}</li>")
        html_lines.append("</ul>")

        # Add warning if dangerous permissions
        dangerous_perms = {"system:execute", "system:packages", "system:services", "system:files"}
        if any(p in dangerous_perms for p in self.plugin_package.manifest.permissions):
            html_lines.append(
                "<p style='color: #e8556d; font-weight: bold;'>"
                "⚠️ Warning: This plugin requests elevated system permissions. "
                "Only grant access if you trust the plugin author."
                "</p>"
            )

        # Plugin info
        html_lines.append("<hr>")
        html_lines.append(f"<p><b>Author:</b> {self.plugin_package.metadata.author}</p>")
        html_lines.append(f"<p><b>Version:</b> {self.plugin_package.metadata.version}</p>")
        verified = bool(getattr(self.plugin_package.metadata, "verified_publisher", False))
        publisher_id = getattr(self.plugin_package.metadata, "publisher_id", "") or "unknown"
        publisher_badge = getattr(self.plugin_package.metadata, "publisher_badge", "") or ""
        publisher_state = "Verified" if verified else "Unverified"
        if publisher_badge:
            publisher_state = f"{publisher_state} ({publisher_badge})"
        publisher_color = "#3dd68c" if verified else "#e8556d"
        html_lines.append(
            f"<p><b>Publisher:</b> {publisher_id} "
            f"<span style='color: {publisher_color}; font-weight: bold;'>[{publisher_state}]</span></p>"
        )
        if self.plugin_package.metadata.homepage:
            html_lines.append(
                f"<p><b>Homepage:</b> <a href='{self.plugin_package.metadata.homepage}'>"
                f"{self.plugin_package.metadata.homepage}</a></p>"
            )

        perms_text.setHtml("\n".join(html_lines))
        layout.addWidget(perms_text)

        # Consent checkbox
        self.consent_checkbox = QCheckBox(
            self.tr("I understand and accept these permissions")
        )
        self.consent_checkbox.stateChanged.connect(self._on_consent_changed)
        layout.addWidget(self.consent_checkbox)

        # Buttons
        btn_layout = QHBoxLayout()

        self.install_btn = QPushButton(self.tr("Install"))
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.install_btn)

        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_consent_changed(self, state):
        """Enable/disable install button based on consent."""
        self.install_btn.setEnabled(state == Qt.CheckState.Checked.value)
