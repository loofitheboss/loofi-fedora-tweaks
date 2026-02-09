#!/bin/bash
set -e

VERSION=$(python3 -c "exec(open('loofi-fedora-tweaks/version.py').read()); print(__version__)")

# Setup build directories in /tmp to avoid spaces in path
BUILD_DIR="/tmp/loofi-fedora-tweaks-build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Prepare source tarball
mkdir -p "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-$VERSION/loofi-fedora-tweaks
cp -r loofi-fedora-tweaks/* "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-$VERSION/loofi-fedora-tweaks/
cp loofi-fedora-tweaks.desktop "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-$VERSION/

# Ensure Python cache artifacts are never packaged
find "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-$VERSION -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$BUILD_DIR"/temp_build/loofi-fedora-tweaks-$VERSION -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

tar -czf "$BUILD_DIR"/rpmbuild/SOURCES/loofi-fedora-tweaks-$VERSION.tar.gz -C "$BUILD_DIR"/temp_build loofi-fedora-tweaks-$VERSION

# Copy spec file
cp loofi-fedora-tweaks.spec "$BUILD_DIR"/rpmbuild/SPECS/

# Build RPM
rpmbuild --define "_topdir $BUILD_DIR/rpmbuild" -ba "$BUILD_DIR"/rpmbuild/SPECS/loofi-fedora-tweaks.spec

# Copy RPM back
mkdir -p rpmbuild/RPMS/noarch
cp "$BUILD_DIR"/rpmbuild/RPMS/noarch/*.rpm rpmbuild/RPMS/noarch/

echo "RPM built successfully at rpmbuild/RPMS/noarch/"
