#!/bin/bash
set -euo pipefail

VERSION=$(python3 -c "exec(open('loofi-fedora-tweaks/version.py').read()); print(__version__)")

echo "Building RPM for loofi-fedora-tweaks v${VERSION}"

# Setup build directories in /tmp to avoid spaces in path
BUILD_DIR="/tmp/loofi-fedora-tweaks-build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Prepare source tarball (mirrors the GitHub archive layout)
STAGE="$BUILD_DIR/temp_build/loofi-fedora-tweaks-$VERSION"
mkdir -p "$STAGE/loofi-fedora-tweaks"
cp -r loofi-fedora-tweaks/* "$STAGE/loofi-fedora-tweaks/"
cp loofi-fedora-tweaks.desktop "$STAGE/"
cp LICENSE "$STAGE/"

# Ensure Python cache artifacts are never packaged
find "$STAGE" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$STAGE" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

tar -czf "$BUILD_DIR"/rpmbuild/SOURCES/loofi-fedora-tweaks-$VERSION.tar.gz -C "$BUILD_DIR"/temp_build loofi-fedora-tweaks-$VERSION

# Copy spec file
cp loofi-fedora-tweaks.spec "$BUILD_DIR"/rpmbuild/SPECS/

# Build RPM
rpmbuild --define "_topdir $BUILD_DIR/rpmbuild" -ba "$BUILD_DIR"/rpmbuild/SPECS/loofi-fedora-tweaks.spec

# Copy RPM back
mkdir -p rpmbuild/RPMS/noarch
cp "$BUILD_DIR"/rpmbuild/RPMS/noarch/*.rpm rpmbuild/RPMS/noarch/

echo "RPM built successfully at rpmbuild/RPMS/noarch/"
