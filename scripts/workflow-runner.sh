#!/usr/bin/env bash
# Workflow runner shell wrapper for Loofi Fedora Tweaks
# Validates environment and forwards arguments to workflow_runner.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNNER_SCRIPT="$SCRIPT_DIR/workflow_runner.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Workflow Runner — Loofi Fedora Tweaks

Usage: $0 [OPTIONS]

Options:
  --phase PHASE              Workflow phase to execute
                            (plan|design|build|test|doc|package|release|all)
  --target-version VERSION   Version tag (e.g., v42.0.0 or 42.0.0)
  --assistant ASSISTANT      AI assistant to use (codex|claude|copilot)
  --mode MODE               Execution mode (write|review)
  --issue NUMBER            Optional issue ID for traceability
  --owner NAME              Writer lock owner (default: current user)
  --dry-run                 Print commands without executing
  --lock-ttl-minutes N      Writer lock expiry in minutes (default: 120)
  --release-writer-lock     Release writer lock and exit
  --force-release-lock      Force-release writer lock
  --force-phase             Bypass strict phase ordering enforcement
  --help                    Show this help message

Examples:
  # Plan phase (dry-run)
  $0 --phase plan --target-version v42.0.0 --assistant copilot --dry-run

  # Build phase (live)
  $0 --phase build --target-version v42.0.0 --assistant claude

  # Full pipeline (dry-run)
  $0 --phase all --target-version v42.0.0 --assistant codex --dry-run

  # Release writer lock
  $0 --release-writer-lock --assistant copilot

Environment:
  PYTHON_VERSION: Python 3.12+ required
  PYTHONPATH: Set to loofi-fedora-tweaks directory

Legacy Usage (still supported):
  $0 <version> [phase] [runner args...]

See also: scripts/workflow_runner.py --help
EOF
    exit 0
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: python3 not found in PATH${NC}" >&2
        exit 1
    fi

    local python_version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major minor
    IFS='.' read -r major minor <<< "$python_version"

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 12 ]; }; then
        echo -e "${RED}ERROR: Python 3.12+ required, found $python_version${NC}" >&2
        exit 1
    fi

    echo -e "${GREEN}✓ Python $python_version${NC}"
}

check_runner_script() {
    if [ ! -f "$RUNNER_SCRIPT" ]; then
        echo -e "${RED}ERROR: workflow_runner.py not found at $RUNNER_SCRIPT${NC}" >&2
        exit 1
    fi

    if [ ! -r "$RUNNER_SCRIPT" ]; then
        echo -e "${RED}ERROR: workflow_runner.py not readable${NC}" >&2
        exit 1
    fi

    echo -e "${GREEN}✓ Workflow runner script found${NC}"
}

# Legacy function for backward compatibility
phase_validate() {
    local VERSION_TAG="$1"
    local VERSION_NO_V="${VERSION_TAG#v}"
    local VERSION_PY="$ROOT_DIR/loofi-fedora-tweaks/version.py"
    local SPEC_FILE="$ROOT_DIR/loofi-fedora-tweaks.spec"
    local TASKS_FILE="$ROOT_DIR/.workflow/specs/tasks-${VERSION_TAG}.md"
    local TEST_REPORT_FILE="$ROOT_DIR/.workflow/reports/test-results-${VERSION_TAG}.json"
    local NOTES_FILE="$ROOT_DIR/docs/releases/RELEASE-NOTES-${VERSION_TAG}.md"

    echo -e "${BLUE}[workflow]${NC} Validating release readiness for ${VERSION_TAG}..."

    local py_ver spec_ver
    py_ver=$(python3 -c "
import sys; sys.path.insert(0,'$ROOT_DIR/loofi-fedora-tweaks')
from version import __version__; print(__version__)
" 2>/dev/null || echo "UNKNOWN")
    spec_ver=$(grep '^Version:' "$SPEC_FILE" 2>/dev/null | awk '{print $2}' || echo "UNKNOWN")

    if [ "$py_ver" = "$VERSION_NO_V" ]; then echo -e "${GREEN}  ✓${NC} version.py: $py_ver"; else echo -e "${RED}  ✗${NC} version.py: $py_ver (expected $VERSION_NO_V)"; fi
    if [ "$spec_ver" = "$VERSION_NO_V" ]; then echo -e "${GREEN}  ✓${NC} .spec: $spec_ver"; else echo -e "${RED}  ✗${NC} .spec: $spec_ver (expected $VERSION_NO_V)"; fi

    if grep -q "\[$VERSION_NO_V\]" "$ROOT_DIR/CHANGELOG.md" 2>/dev/null || grep -q "\[$VERSION_TAG\]" "$ROOT_DIR/CHANGELOG.md" 2>/dev/null; then
        echo -e "${GREEN}  ✓${NC} CHANGELOG.md has $VERSION_TAG entry"
    else
        echo -e "${YELLOW}  ⚠${NC} CHANGELOG.md missing $VERSION_TAG entry"
    fi

    if [ -f "$NOTES_FILE" ]; then
        echo -e "${GREEN}  ✓${NC} Release notes exist"
    else
        echo -e "${YELLOW}  ⚠${NC} Release notes missing: $NOTES_FILE"
    fi

    if [ -f "$TASKS_FILE" ]; then echo -e "${GREEN}  ✓${NC} Task artifact exists"; else echo -e "${YELLOW}  ⚠${NC} Task artifact missing: $TASKS_FILE"; fi
    if [ -f "$TEST_REPORT_FILE" ]; then echo -e "${GREEN}  ✓${NC} Test report artifact exists"; else echo -e "${YELLOW}  ⚠${NC} Test report artifact missing: $TEST_REPORT_FILE"; fi
}

main() {
    # Show help if --help or -h
    if [ $# -gt 0 ] && { [ "$1" = "--help" ] || [ "$1" = "-h" ]; }; then
        usage
    fi

    # Detect legacy usage: first arg without -- prefix is version
    if [ $# -gt 0 ] && [[ ! "$1" =~ ^-- ]]; then
        # Legacy mode: workflow-runner.sh <version> [phase] [args...]
        VERSION_INPUT="${1:?Usage: $0 <version> [phase] [runner args...]}"
        PHASE="${2:-all}"
        shift 2 || true
        EXTRA_ARGS=("$@")
        VERSION_NO_V="${VERSION_INPUT#v}"
        VERSION_TAG="v${VERSION_NO_V}"

        echo "=== Workflow Runner (Legacy Mode) ==="
        echo "Root: $ROOT_DIR"
        echo

        check_python
        check_runner_script
        export PYTHONPATH="$ROOT_DIR/loofi-fedora-tweaks:${PYTHONPATH:-}"

        case "$PHASE" in
            validate)
                phase_validate "$VERSION_TAG"
                ;;
            all)
                phase_validate "$VERSION_TAG"
                python3 "$RUNNER_SCRIPT" --phase all --target-version "$VERSION_TAG" "${EXTRA_ARGS[@]}"
                ;;
            implement)
                # Legacy: map implement -> build
                python3 "$RUNNER_SCRIPT" --phase build --target-version "$VERSION_TAG" "${EXTRA_ARGS[@]}"
                ;;
            document)
                # Legacy: map document -> doc
                python3 "$RUNNER_SCRIPT" --phase doc --target-version "$VERSION_TAG" "${EXTRA_ARGS[@]}"
                ;;
            plan|design|build|test|doc|package|release)
                python3 "$RUNNER_SCRIPT" --phase "$PHASE" --target-version "$VERSION_TAG" "${EXTRA_ARGS[@]}"
                ;;
            *)
                echo -e "${RED}ERROR: Unknown phase: $PHASE${NC}" >&2
                echo "Available: plan, design, build, test, doc, package, release, validate, all"
                exit 1
                ;;
        esac
    else
        # Modern mode: forward all arguments directly
        if [ $# -eq 0 ]; then
            usage
        fi

        echo "=== Workflow Runner (Loofi Fedora Tweaks) ==="
        echo "Root: $ROOT_DIR"
        echo

        check_python
        check_runner_script

        export PYTHONPATH="$ROOT_DIR/loofi-fedora-tweaks:${PYTHONPATH:-}"
        echo -e "${GREEN}✓ PYTHONPATH set${NC}"
        echo

        echo "Executing: python3 $RUNNER_SCRIPT $*"
        echo
        cd "$ROOT_DIR"
        exec python3 "$RUNNER_SCRIPT" "$@"
    fi
}

main "$@"
