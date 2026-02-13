#!/bin/bash
# AppImage build script for Loofi Fedora Tweaks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION_FILE="${ROOT_DIR}/loofi-fedora-tweaks/version.py"
OUTPUT_DIR="${ROOT_DIR}/dist/appimage"
APPDIR_TMP="$(mktemp -d /tmp/loofi-fedora-tweaks-appdir-XXXXXX)"
APPDIR="${APPDIR_TMP}/AppDir"

cleanup() {
  rm -rf "${APPDIR_TMP}"
}
trap cleanup EXIT

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Error: Missing required tool: ${tool}" >&2
    exit 1
  fi
}

resolve_linuxdeploy() {
  if command -v linuxdeploy >/dev/null 2>&1; then
    printf '%s' "$(command -v linuxdeploy)"
    return
  fi

  if [[ -n "${LINUXDEPLOY_BIN:-}" && -x "${LINUXDEPLOY_BIN}" ]]; then
    printf '%s' "${LINUXDEPLOY_BIN}"
    return
  fi

  echo "Error: Missing required tool: linuxdeploy" >&2
  exit 1
}

extract_version() {
  local version
  version="$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' "${VERSION_FILE}" | head -n 1)"
  if [[ -z "${version}" ]]; then
    echo "Error: Failed to parse version from ${VERSION_FILE}" >&2
    exit 1
  fi
  printf '%s' "${version}"
}

main() {
  require_tool appimagetool
  local linuxdeploy_bin
  linuxdeploy_bin="$(resolve_linuxdeploy)"
  "${linuxdeploy_bin}" --version >/dev/null 2>&1 || true

  if [[ ! -f "${ROOT_DIR}/loofi-fedora-tweaks.desktop" ]]; then
    echo "Error: Missing desktop file: ${ROOT_DIR}/loofi-fedora-tweaks.desktop" >&2
    exit 1
  fi

  if [[ ! -f "${ROOT_DIR}/loofi-fedora-tweaks/assets/icon.png" ]]; then
    echo "Error: Missing icon file: ${ROOT_DIR}/loofi-fedora-tweaks/assets/icon.png" >&2
    exit 1
  fi

  local version
  version="$(extract_version)"
  mkdir -p "${OUTPUT_DIR}"
  local output_path="${OUTPUT_DIR}/loofi-fedora-tweaks-v${version}-x86_64.AppImage"

  mkdir -p "${APPDIR}/usr/bin" "${APPDIR}/usr/lib" "${APPDIR}/usr/share/applications" "${APPDIR}/usr/share/icons/hicolor/512x512/apps"
  cp -r "${ROOT_DIR}/loofi-fedora-tweaks" "${APPDIR}/usr/lib/loofi-fedora-tweaks"
  cp "${ROOT_DIR}/loofi-fedora-tweaks.desktop" "${APPDIR}/usr/share/applications/"
  cp "${ROOT_DIR}/loofi-fedora-tweaks/assets/icon.png" "${APPDIR}/usr/share/icons/hicolor/512x512/apps/org.loofi.FedoraTweaks.png"

  cat > "${APPDIR}/usr/bin/loofi-fedora-tweaks" <<'APP'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/../lib/loofi-fedora-tweaks"
exec python3 "${SCRIPT_DIR}/../lib/loofi-fedora-tweaks/main.py" "$@"
APP
  chmod +x "${APPDIR}/usr/bin/loofi-fedora-tweaks"

  cat > "${APPDIR}/AppRun" <<'APP'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/usr/bin/loofi-fedora-tweaks" "$@"
APP
  chmod +x "${APPDIR}/AppRun"

  cp "${ROOT_DIR}/loofi-fedora-tweaks.desktop" "${APPDIR}/"
  cp "${ROOT_DIR}/loofi-fedora-tweaks/assets/icon.png" "${APPDIR}/org.loofi.FedoraTweaks.png"

  ARCH=x86_64 appimagetool "${APPDIR}" "${output_path}"

  if [[ ! -f "${output_path}" ]]; then
    echo "Error: AppImage was not created: ${output_path}" >&2
    exit 1
  fi

  echo "AppImage build complete: ${output_path}"
}

main "$@"
