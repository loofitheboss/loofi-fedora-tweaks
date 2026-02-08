Name:           loofi-fedora-tweaks
Version:        12.0.0
Release:        1%{?dist}
Summary:        Complete Fedora system management with AI, security, and window management

License:        MIT
URL:            https://github.com/loofitheboss/loofi-fedora-tweaks
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3
Requires:       python3-pyqt6
Requires:       polkit
Requires:       libnotify

%description
A comprehensive GUI application for Fedora 43+ (KDE Plasma) with system maintenance,
developer tooling, AI integration, security hardening, window management, virtualization,
mesh networking, and workspace state teleportation.
Features: VM Quick-Create, VFIO GPU Passthrough, Loofi Link Mesh, State Teleport,
AI Lab, Security Center, Director, Containers, Watchtower diagnostics, Replicator IaC.

%prep
%setup -q

%install
mkdir -p "%{buildroot}/usr/lib/%{name}"
mkdir -p "%{buildroot}/usr/bin"
mkdir -p "%{buildroot}/usr/share/applications"
mkdir -p "%{buildroot}/usr/share/polkit-1/actions"
mkdir -p "%{buildroot}/usr/lib/systemd/user"
mkdir -p "%{buildroot}/usr/share/icons/hicolor/128x128/apps"

cp -r loofi-fedora-tweaks/* "%{buildroot}/usr/lib/%{name}/"

cat > "%{buildroot}/usr/bin/%{name}" << 'EOF'
#!/bin/bash
cd /usr/lib/loofi-fedora-tweaks
exec python3 main.py "$@"
EOF
chmod +x "%{buildroot}/usr/bin/%{name}"

install -m 644 %{name}.desktop "%{buildroot}/usr/share/applications/"
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.policy "%{buildroot}/usr/share/polkit-1/actions/"
install -m 644 loofi-fedora-tweaks/config/loofi-fedora-tweaks.service "%{buildroot}/usr/lib/systemd/user/"
install -m 644 loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png "%{buildroot}/usr/share/icons/hicolor/128x128/apps/"

%files
/usr/lib/%{name}
/usr/bin/%{name}
/usr/share/applications/%{name}.desktop
/usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
/usr/lib/systemd/user/loofi-fedora-tweaks.service
/usr/share/icons/hicolor/128x128/apps/loofi-fedora-tweaks.png

%changelog
* Sun Feb 08 2026 Loofi <loofi@example.com> - 12.0.0-1
- Sovereign Update: Virtualization, mesh networking, and state teleportation
- VM Quick-Create wizard with 5 preset flavors (Windows 11, Fedora, Ubuntu, Kali, Arch)
- VFIO GPU Passthrough Assistant with IOMMU analysis and kernel cmdline generation
- Disposable VMs using QCOW2 overlay snapshots
- Loofi Link mesh device discovery via Avahi mDNS
- Encrypted clipboard sync and File Drop with checksum verification
- State Teleport workspace capture and cross-device restore
- AI Lite Model Library with RAM-based recommendations
- Voice Mode with whisper.cpp transcription
- Context RAG with TF-IDF local file indexing
- Virtualization and AI Lab refactored as first-party plugins
- 18-tab sidebar layout, 564 tests passing
- New CLI commands: vm, vfio, mesh, teleport, ai-models

* Sun Feb 08 2026 Loofi <loofi@example.com> - 11.0.0-1
- Aurora Update: Extensibility and diagnostics upgrades
- Plugin manifest support with enable/disable state and CLI management
- Plugin Manager UI under Community tab
- Support bundle ZIP export (Diagnostics + CLI)
- Automation rule validation and dry-run simulation
- Unified stylesheet loading and improved logging visibility

* Sat Feb 07 2026 Loofi <loofi@example.com> - 10.0.0-1
- Zenith Update: Major consolidation and modernization release
- Tab consolidation: 25 tabs reduced to 15 with sub-navigation
- New BaseTab class eliminates code duplication across UI layer
- First-run wizard with hardware auto-detection
- Command palette (Ctrl+K) for global feature search
- Hardware profiles: HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS
- Centralized command builder (PrivilegedCommand) for safe pkexec operations
- Error handling framework with recovery hints
- CI/CD pipeline with GitHub Actions
- New consolidated tabs: Maintenance, Software, Monitor, Desktop, Development, Community, Automation, Diagnostics
- Privacy features merged into Security Center
- HP Tweaks merged into Hardware tab (now hardware-agnostic)
- CLI version synced, new doctor and suggest commands
- 40+ new unit tests, shared test fixtures

* Sat Feb 07 2026 Loofi <loofi@example.com> - 9.2.0-1
- Pulse Update: Real-time performance monitoring and process management
- Performance tab: Live CPU, RAM, Network, Disk I/O graphs
- Process monitor tab: Top processes with kill/renice support
- Temperature monitoring via hwmon sensors
- Network traffic monitor with per-interface bandwidth
- Dashboard auto-refresh with CPU load indicator
- CLI commands: processes, temperature, netmon

* Sat Feb 07 2026 Loofi <loofi@example.com> - 9.0.0-1
- Director Update: Window management for KDE, Hyprland, Sway
- Director tab: Tiling presets, workspace templates, dotfile sync
- KWin script installer for advanced KDE tiling

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.5.0-1
- Sentinel Update: Proactive security hardening
- Security Center tab: Port auditor with security scoring
- USB Guard integration for BadUSB protection
- Firejail sandbox manager for application isolation

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.1.0-1
- Neural Update: AI-ready foundation
- AI Lab tab: Hardware detection, Ollama management
- Model downloads for Llama, Mistral, CodeLlama

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.0.0-1
- Replicator Update: Developer tools, diagnostics, and IaC exports

* Sat Feb 07 2026 Loofi <loofi@example.com> - 7.0.0-1
- Community Update: Marketplace and Drift Detection
- Preset Marketplace for community presets
- Configuration drift detection
- New marketplace tab UI

* Sat Feb 07 2026 Loofi <loofi@example.com> - 6.5.0-1
- Architect Update: CLI and Plugin System
- Full CLI mode with subcommands
- Plugin system for extensions
- Operations layer refactoring

* Sat Feb 07 2026 Loofi <loofi@example.com> - 6.2.0-1
- Engine Room Update: Boot management features
- Kernel parameter editor with grubby wrapper
- ZRAM tuner for memory compression
- Secure Boot MOK helper
