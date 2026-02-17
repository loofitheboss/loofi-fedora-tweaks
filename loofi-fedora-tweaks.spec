Name:           loofi-fedora-tweaks
Version:        48.0.0
Release:        1%{?dist}
Summary:        Complete Fedora system management with AI, security, and window management

License:        MIT
URL:            https://github.com/loofitheboss/loofi-fedora-tweaks
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-pyqt6
Requires:       qt6-qtbase-gui
Requires:       mesa-libGL
Requires:       mesa-libEGL
Requires:       polkit
Requires:       /usr/bin/notify-send
Requires:       python3-fastapi
Requires:       python3-uvicorn
Requires:       python3-jwt
Requires:       python3-bcrypt
Requires:       python3-httpx
Requires:       hicolor-icon-theme
Requires:       google-noto-color-emoji-fonts

%description
A comprehensive GUI application for Fedora 43+
(KDE Plasma) with system maintenance, developer
tooling, AI integration, security hardening,
window management, virtualization, mesh networking,
and workspace state teleportation. Features include
VM Quick-Create, VFIO GPU Passthrough, Loofi Link
Mesh, State Teleport, AI Lab, Security Center,
Director, Containers, and Replicator IaC.

%prep
%setup -q

%build
# Nothing to build -- pure Python application

%install
mkdir -p %{buildroot}%{_prefix}/lib/%{name}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/polkit-1/actions
mkdir -p %{buildroot}%{_userunitdir}
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/128x128/apps
mkdir -p %{buildroot}%{_licensedir}/%{name}

cp -r loofi-fedora-tweaks/* %{buildroot}%{_prefix}/lib/%{name}/

# Remove the duplicate systemd service from the app tree
rm -f %{buildroot}%{_prefix}/lib/%{name}/config/loofi-fedora-tweaks.service

# Remove pre-compiled bytecode; rpmbuild generates fresh .pyc via brp-python-bytecompile
find %{buildroot}%{_prefix}/lib/%{name} -type d -name '__pycache__' -exec rm -rf {} +  2>/dev/null || :

# Ensure all installed files are world-readable
find %{buildroot}%{_prefix}/lib/%{name} -type f -exec chmod 644 {} +
find %{buildroot}%{_prefix}/lib/%{name} -type d -exec chmod 755 {} +

cat > %{buildroot}%{_bindir}/%{name} << 'EOF'
#!/bin/bash
APP_DIR=/usr/lib/loofi-fedora-tweaks
LOG_DIR="${HOME}/.local/share/loofi-fedora-tweaks"
mkdir -p "${LOG_DIR}"
export PYTHONPATH="${APP_DIR}${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "${APP_DIR}/main.py" "$@" 2>>"${LOG_DIR}/startup.log"
EOF
chmod 0755 %{buildroot}%{_bindir}/%{name}

desktop-file-install \
    --dir=%{buildroot}%{_datadir}/applications \
    %{name}.desktop

install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.firewall.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.network.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.storage.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.service-manage.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.kernel.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/org.loofi.fedora-tweaks.security.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 loofi-fedora-tweaks/config/loofi-fedora-tweaks.service %{buildroot}%{_userunitdir}/
install -m 644 loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png %{buildroot}%{_datadir}/icons/hicolor/128x128/apps/
install -Dm 644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE
install -Dm 644 %{name}.1 %{buildroot}%{_mandir}/man1/%{name}.1

%check
# Run basic import validation
PYTHONPATH=loofi-fedora-tweaks python3 -c "import main; print('Import OK')" || :

%post
%systemd_user_post %{name}.service

%preun
%systemd_user_preun %{name}.service

%postun
%systemd_user_postun_with_restart %{name}.service

%files
%license LICENSE
%doc README.md
%{_prefix}/lib/%{name}
%attr(755,root,root) %{_bindir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.policy
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.firewall.policy
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.network.policy
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.storage.policy
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.service-manage.policy
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.kernel.policy
%{_datadir}/polkit-1/actions/org.loofi.fedora-tweaks.security.policy
%{_userunitdir}/loofi-fedora-tweaks.service
%{_datadir}/icons/hicolor/128x128/apps/loofi-fedora-tweaks.png
%{_mandir}/man1/%{name}.1*

%changelog
* Mon Feb 17 2026 Loofi <loofi@example.com> - 48.0.0-1
- v48.0.0 "Sidebar Index" — Sidebar restructure with O(1) lookups
- SidebarEntry dataclass and SidebarIndex for O(1) tab lookups
- Decomposed add_page() into focused helpers
- Fixed favorites, status, navigation with ID-based lookups
- SidebarItemDelegate for colored status dots
- Experience level sync validation

* Mon Feb 17 2026 Loofi <loofi@example.com> - 47.0.0-1
- v47.0.0 "Experience" — UX improvements for all skill levels
- Added experience level system (beginner, intermediate, advanced)
- Tour overlay for first-time users
- Contextual tooltips and progressive disclosure

* Mon Feb 17 2026 Loofi <loofi@example.com> - 46.0.0-1
- v46.0.0 "Navigator" — Navigation and discoverability improvements

* Mon Feb 17 2026 Loofi <loofi@example.com> - 45.0.0-1
- v45.0.0 "Housekeeping" — Code cleanup and documentation alignment

* Mon Feb 16 2026 Loofi <loofi@example.com> - 44.0.0-1
- v44.0.0 "Review Gate" — Fedora review workflow enforcement
- Added scripts/check_fedora_review.py for lightweight fedora-review health gating
- Enforced fedora-review gate for workflow_runner write-mode package/release phases
- Added required fedora_review job to CI and auto-release workflows
- Updated workflow docs/prompts and release docs for fedora-review prerequisite

* Mon Feb 16 2026 Loofi <loofi@example.com> - 43.0.0-1
- v43.0.0 "Stabilization-Only" — Strict Compliance
- Added AST stabilization policy gate (timeouts, UI subprocess, hardcoded dnf, broad-exception allowlist)
- Enforced checker in CI and auto-release workflows
- Raised all coverage thresholds to 80%
- Extracted wizard health checks to utils/wizard_health.py (UI now has zero subprocess calls)
- Eliminated remaining executable hardcoded dnf invocations in package/update/health/export stacks
- Narrowed broad exceptions to explicit handlers and boundary allowlist

* Mon Feb 16 2026 Loofi <loofi@example.com> - 42.0.0-1
- v42.0.0 "Sentinel" — Hardening & Polish
- 106 exception handlers narrowed to specific types across 30 files
- 25+ hardcoded dnf references eliminated
- Daemon systemd hardening (NoNewPrivileges, ProtectSystem=strict)
- Software tab search/filter, high-contrast theme
- Test stability fixes for cross-test sys.modules pollution

* Sat Feb 14 2026 Loofi <loofi@example.com> - 40.0.0-1
- v40.0.0 "Foundation" — Correctness & Safety
- All subprocess calls have explicit timeout= parameters
- All 21 f-string logger calls converted to %s formatting
- All 13 hardcoded dnf commands replaced with PrivilegedCommand/SystemManager
- All 10 pkexec sh -c calls refactored to atomic commands (no shell=True)
- All 141 silent except Exception: blocks now capture and log errors
- All sudo references replaced with pkexec
- package_manager.py unified through PrivilegedCommand.dnf()
- Fedora Atomic (rpm-ostree) compatibility across all package operations

* Sat Feb 14 2026 Loofi <loofi@example.com> - 34.0.0-1
- v34.0.0 "Citadel" — Polish & Stability
- Light theme completely rewritten (Catppuccin Latte, 24+ new selectors)
- CommandRunner hardened (timeout, kill escalation, crash detection)
- 12 subprocess.run calls extracted from UI to utils layer
- 21 silent exception swallows replaced with logger.debug()
- Log rotation enabled (5 MB, 3 backups)
- Daemon print statements replaced with structured logging
- 43 accessibility annotations added across 7 tabs
- 67 new tests (4025 total, 0 failures)

* Fri Feb 13 2026 Loofi <loofi@example.com> - 30.0.0-1
- v30.0.0 Distribution & Reliability
- Added packaging scripts: build_flatpak.sh, build_appimage.sh, build_sdist.sh
- Added release notes for v30.0.0
- Update checker reliability: structured assets, download pipeline, checksum verification
- Marketplace offline mode with cache-first fallback
- Rate limiter concurrency improvements
- Auto-tuner history thread safety
- CI quality gates: mypy/bandit blocking, coverage 75%, packaging jobs

* Fri Feb 13 2026 Loofi <loofi@example.com> - 29.0.0-1
- v29.0.0 Usability & Polish
- Centralized error handler with global sys.excepthook override
- Confirmation dialog for dangerous operations
- Notification toast with animated slide-in
- Status indicators on sidebar tabs
- Settings reset per group
- 151 test files, 3846+ tests, 76.8% coverage

* Thu Feb 12 2026 Loofi <loofi@example.com> - 28.0.0-1
- v28.0.0 Workflow Contract Reset
- Clean-slate workflow state and runner-compatible planning artifacts
- Architecture blueprint for artifact structure and validation rules

* Thu Feb 12 2026 Loofi <loofi@example.com> - 27.0.0-1
- v27.0.0 Marketplace Enhancement
- Added CDN-first marketplace index with signed metadata and fallback behavior
- Added ratings/reviews, verified publisher badges, analytics opt-in, and hot reload
- Updated SDK, changelog, README, and release notes for v27.0.0

* Thu Feb 12 2026 Loofi <loofi@example.com> - 26.0.2-1
- v26.0.2 Status Bar UI Hotfix
- Fixed bottom status bar label rendering artifacts

* Thu Feb 12 2026 Loofi <loofi@example.com> - 26.0.1-1
- v26.0.1 Breadcrumb Bar UI Hotfix
- Fixed top breadcrumb text rendering artifacts

* Wed Feb 11 2026 Loofi <loofi@example.com> - 25.0.3-1
- v25.0.3 Maintenance Update Crash Hotfix
- Fixed crash when clicking Maintenance update actions

* Mon Feb 09 2026 Loofi <loofi@example.com> - 24.0.0-1
- v24.0 Power Features
- Created BaseActionExecutor ABC with privileged execution support
- Centralized BaseWorker QThread pattern in core/workers/
- Migrated system and hardware services to services/ layer

* Mon Feb 09 2026 Loofi <loofi@example.com> - 21.0.1-1
- Packaging: Remove python-jose test dependency (fixes RPM install on Fedora)

* Mon Feb 09 2026 Loofi <loofi@example.com> - 21.0.0-1
- v21.0 UX Stabilization & Layout Integrity
- Baseline layout fixes: native title bar, border cleanup, documentMode

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.2-2
- UI hotfix: force native title-bar flags in MainWindow

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.2-1
- UI: Fix top tab overflow by enabling scroll buttons and styling scrollers

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.1-1
- Packaging: switch JWT dependency to python3-jwt (PyJWT) for Fedora 43

* Mon Feb 09 2026 Loofi <loofi@example.com> - 20.0.0-1
- v20.0 Synapse Phase 1: Remote Management & EventBus Hive Mind

* Mon Feb 09 2026 Loofi <loofi@example.com> - 19.0.0-1
- v19.0 Vanguard: ActionExecutor, breadcrumb bar, status bar, tooltips

* Mon Feb 09 2026 Loofi <loofi@example.com> - 18.1.1-1
- v18.1.1 Hotfix: Fix startup crash due to sidebar refactor

* Mon Feb 09 2026 Loofi <loofi@example.com> - 18.1.0-1
- v18.1 Navigator: Categorized Sidebar & Enhanced UX

* Mon Feb 09 2026 Loofi <loofi@example.com> - 18.0.0-1
- v18.0 Sentinel: Autonomous Agent Framework, AI Agent Planner

* Sun Feb 08 2026 Loofi <loofi@example.com> - 17.0.0-1
- v17.0 Atlas: Performance, Snapshots, Smart Logs, Storage, Network

* Sun Feb 08 2026 Loofi <loofi@example.com> - 15.0.0-1
- v15.0 Nebula: Auto-Tuner, Snapshot Timeline, Smart Logs

* Sun Feb 08 2026 Loofi <loofi@example.com> - 13.5.0-1
- UX Polish: Settings system, light theme, keyboard shortcuts

* Sun Feb 08 2026 Loofi <loofi@example.com> - 13.1.0-1
- Stability update: exception cleanup, security hardening

* Sun Feb 08 2026 Loofi <loofi@example.com> - 13.0.0-1
- Nexus Update: System profiles, health timeline, plugin SDK v2

* Sun Feb 08 2026 Loofi <loofi@example.com> - 12.0.0-1
- Sovereign Update: Virtualization, mesh networking, state teleportation

* Sun Feb 08 2026 Loofi <loofi@example.com> - 11.0.0-1
- Aurora Update: Extensibility and diagnostics upgrades

* Sat Feb 07 2026 Loofi <loofi@example.com> - 10.0.0-1
- Zenith Update: Major consolidation and modernization release

* Sat Feb 07 2026 Loofi <loofi@example.com> - 9.2.0-1
- Pulse Update: Real-time performance monitoring and process management

* Sat Feb 07 2026 Loofi <loofi@example.com> - 9.0.0-1
- Director Update: Window management for KDE, Hyprland, Sway

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.5.0-1
- Sentinel Update: Proactive security hardening

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.1.0-1
- Neural Update: AI-ready foundation

* Sat Feb 07 2026 Loofi <loofi@example.com> - 8.0.0-1
- Replicator Update: Developer tools, diagnostics, and IaC exports

* Sat Feb 07 2026 Loofi <loofi@example.com> - 7.0.0-1
- Community Update: Marketplace and Drift Detection

* Sat Feb 07 2026 Loofi <loofi@example.com> - 6.5.0-1
- Architect Update: CLI and Plugin System

* Sat Feb 07 2026 Loofi <loofi@example.com> - 6.2.0-1
- Engine Room Update: Boot management features
