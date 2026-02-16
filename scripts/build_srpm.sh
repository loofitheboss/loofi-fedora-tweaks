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

SOURCE_TARBALL="$BUILD_DIR/rpmbuild/SOURCES/loofi-fedora-tweaks-${VERSION}.tar.gz"
TARBALL_URL="${REPO_URL}/archive/v${VERSION}/loofi-fedora-tweaks-${VERSION}.tar.gz"

# Prefer canonical release source tarball; fall back to local archive when
# the release tag is not yet available.
echo "Downloading source tarball: ${TARBALL_URL}"
if ! curl -fSL -o "$SOURCE_TARBALL" "$TARBALL_URL"; then
  echo "Release tarball unavailable; creating source tarball from local checkout"
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git archive \
      --format=tar.gz \
      --prefix="loofi-fedora-tweaks-${VERSION}/" \
      -o "$SOURCE_TARBALL" \
      HEAD
  else
    tar \
      --exclude-vcs \
      --transform "s#^#loofi-fedora-tweaks-${VERSION}/#" \
      -czf "$SOURCE_TARBALL" \
      .
  fi
fi

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
