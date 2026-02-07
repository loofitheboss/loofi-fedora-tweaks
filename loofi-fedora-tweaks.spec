Name:           loofi-fedora-tweaks
Version:        6.2.0
Release:        1%{?dist}
Summary:        System tweaks and maintenance for HP Elitebook 840 G8 (Supports Atomic)

License:        MIT
URL:            https://github.com/loofitheboss/loofi-fedora-tweaks
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3
Requires:       python3-pyqt6
Requires:       polkit
Requires:       libnotify

%description
A GUI application for Fedora 43 (KDE Plasma) tailored for the HP Elitebook 840 G8.
Provides system updates, cleanup, maintenance, and specific hardware optimizations.

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
* Fri Feb 07 2026 Loofi <loofi@example.com> - 6.2.0-1
- Engine Room Update: Boot management features
- Kernel parameter editor with grubby wrapper
- ZRAM tuner for memory compression
- Secure Boot MOK helper
