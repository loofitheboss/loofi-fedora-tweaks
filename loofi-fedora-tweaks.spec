Name:           loofi-fedora-tweaks
Version:        4.6.0
Release:        1%{?dist}
Summary:        System tweaks and maintenance for HP Elitebook 840 G8

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

# Copy source code
cp -r loofi-fedora-tweaks/* "%{buildroot}/usr/lib/%{name}/"

# Create wrapper script
echo '#!/bin/bash' > "%{buildroot}/usr/bin/%{name}"
echo 'export PYTHONPATH=$PYTHONPATH:/usr/lib/loofi-fedora-tweaks' >> "%{buildroot}/usr/bin/%{name}"
echo 'python3 /usr/lib/loofi-fedora-tweaks/main.py "$@"' >> "%{buildroot}/usr/bin/%{name}"
chmod +x "%{buildroot}/usr/bin/%{name}"

# Install desktop file
cp loofi-fedora-tweaks.desktop "%{buildroot}/usr/share/applications/"

%files
/usr/lib/%{name}
/usr/bin/%{name}
/usr/share/applications/loofi-fedora-tweaks.desktop

%changelog
* Sat Feb 07 2026 Loofi <loofi@loofi.com> - 1.0.0-1
- Initial release
