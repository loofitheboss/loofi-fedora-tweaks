#!/bin/bash
# Build an SRPM suitable for Fedora COPR submission.
# Usage: bash scripts/build_srpm.sh
#
# The SRPM is written to rpmbuild/SRPMS/ and can be uploaded to COPR
# either manually or via the copr-cli tool.
set -euo pipefail

VERSION=$(python3 -c "exec(open('loofi-fedora-tweaks/version.py').read()); print(__version__)")
REPO_URL="https://github.com/loofitheboss/loofi-fedora-tweaks"

echo "Building SRPM for loofi-fedora-tweaks v${VERSION}"

# Setup rpmbuild tree in /tmp to avoid spaces in path
BUILD_DIR="/tmp/loofi-fedora-tweaks-srpm"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Download the source tarball from the GitHub release tag.
# COPR will re-download it during the build, but rpmbuild -bs needs the
# file present to create the SRPM.
TARBALL_URL="${REPO_URL}/archive/v${VERSION}/loofi-fedora-tweaks-${VERSION}.tar.gz"
echo "Downloading source tarball: ${TARBALL_URL}"
curl -fSL -o "$BUILD_DIR/rpmbuild/SOURCES/loofi-fedora-tweaks-${VERSION}.tar.gz" "$TARBALL_URL"

# Copy spec
cp loofi-fedora-tweaks.spec "$BUILD_DIR/rpmbuild/SPECS/"

# Build SRPM only (-bs = build source)
rpmbuild --define "_topdir $BUILD_DIR/rpmbuild" \
         -bs "$BUILD_DIR/rpmbuild/SPECS/loofi-fedora-tweaks.spec"

# Copy SRPM back to repo tree
mkdir -p rpmbuild/SRPMS
cp "$BUILD_DIR"/rpmbuild/SRPMS/*.src.rpm rpmbuild/SRPMS/

SRPM_FILE=$(ls rpmbuild/SRPMS/*.src.rpm 2>/dev/null | head -1)
echo ""
echo "SRPM built successfully: ${SRPM_FILE}"
echo ""
echo "To submit to COPR manually:"
echo "  copr-cli build loofi-fedora-tweaks ${SRPM_FILE}"
