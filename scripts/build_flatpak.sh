#!/bin/bash
# Flatpak build script for Loofi Fedora Tweaks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST_PATH="${ROOT_DIR}/org.loofi.FedoraTweaks.yml"
OUTPUT_DIR="${ROOT_DIR}/dist/flatpak"
REPO_DIR="${OUTPUT_DIR}/repo"
BUILD_DIR="${OUTPUT_DIR}/build-dir"
VERSION_FILE="${ROOT_DIR}/loofi-fedora-tweaks/version.py"
APP_ID="org.loofi.FedoraTweaks"

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Error: Missing required tool: ${tool}" >&2
    exit 1
  fi
}

extract_version() {
  if [[ ! -f "${VERSION_FILE}" ]]; then
    echo "Error: Missing version file: ${VERSION_FILE}" >&2
    exit 1
  fi

  local version
  version="$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' "${VERSION_FILE}" | head -n 1)"
  if [[ -z "${version}" ]]; then
    echo "Error: Failed to parse version from ${VERSION_FILE}" >&2
    exit 1
  fi

  printf '%s' "${version}"
}

main() {
  require_tool flatpak-builder
  require_tool flatpak
  require_tool tar

  if [[ ! -f "${MANIFEST_PATH}" ]]; then
    echo "Error: Flatpak manifest not found: ${MANIFEST_PATH}" >&2
    exit 1
  fi

  local version
  version="$(extract_version)"

  mkdir -p "${OUTPUT_DIR}"
  rm -rf "${REPO_DIR}" "${BUILD_DIR}"

  local bundle_path="${OUTPUT_DIR}/loofi-fedora-tweaks-v${version}.flatpak"

  echo "Building Flatpak from ${MANIFEST_PATH}"
  flatpak-builder --force-clean --repo="${REPO_DIR}" "${BUILD_DIR}" "${MANIFEST_PATH}"

  echo "Creating Flatpak bundle: ${bundle_path}"
  flatpak build-bundle "${REPO_DIR}" "${bundle_path}" "${APP_ID}"

  if [[ ! -f "${bundle_path}" ]]; then
    echo "Error: Flatpak bundle was not created: ${bundle_path}" >&2
    exit 1
  fi

  echo "Flatpak build complete"
  echo "Repo: ${REPO_DIR}"
  echo "Bundle: ${bundle_path}"
}

main "$@"
