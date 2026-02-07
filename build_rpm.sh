#!/bin/bash
set -e

# Setup build directories in /tmp to avoid spaces in path
BUILD_DIR="/tmp/loofi-fedora-tweaks-build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Prepare source tarball
# We need the directory inside the tarball to be name-version
mkdir -p "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-1.0.0/loofi-fedora-tweaks
cp -r loofi-fedora-tweaks/* "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-1.0.0/loofi-fedora-tweaks/
# We need the desktop file at top level for the spec %install
cp loofi-fedora-tweaks.desktop "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-1.0.0/

tar -czf "$BUILD_DIR"/rpmbuild/SOURCES/loofi-fedora-tweaks-1.0.0.tar.gz -C "$BUILD_DIR"/temp_build loofi-fedora-tweaks-1.0.0

# Copy spec file
cp loofi-fedora-tweaks.spec "$BUILD_DIR"/rpmbuild/SPECS/

# Build RPM
rpmbuild --define "_topdir $BUILD_DIR/rpmbuild" -ba "$BUILD_DIR"/rpmbuild/SPECS/loofi-fedora-tweaks.spec

# Copy RPM back
mkdir -p rpmbuild/RPMS/noarch
cp "$BUILD_DIR"/rpmbuild/RPMS/noarch/*.rpm rpmbuild/RPMS/noarch/

echo "RPM built successfully at rpmbuild/RPMS/noarch/"
