#!/usr/bin/env bash
# Loofi Fedora Tweaks — Legacy Workflow Runner (State-File compatible)
#
# Usage:
#   ./scripts/workflow-runner.sh <version> [phase] [runner args...]
#
# Examples:
#   ./scripts/workflow-runner.sh 23.0.0 all
#   ./scripts/workflow-runner.sh 23.0.0 plan --dry-run
#   ./scripts/workflow-runner.sh 26.0 design --assistant codex --mode write --issue 42
#   ./scripts/workflow-runner.sh 23.0.0 validate
#
# Phases: plan, design, implement, test, document, package, release, validate, all

set -euo pipefail

VERSION_INPUT="${1:?Usage: $0 <version> [phase] [runner args...]}"
PHASE="${2:-all}"
shift 2 || true
EXTRA_ARGS=("$@")
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$ROOT/scripts/workflow_runner.py"
VERSION_NO_V="${VERSION_INPUT#v}"
VERSION_TAG="v${VERSION_NO_V}"
TASKS_FILE="$ROOT/.workflow/specs/tasks-${VERSION_TAG}.md"
TEST_REPORT_FILE="$ROOT/.workflow/reports/test-results-${VERSION_TAG}.json"
VERSION_PY="$ROOT/loofi-fedora-tweaks/version.py"
SPEC_FILE="$ROOT/loofi-fedora-tweaks.spec"
NOTES_FILE="$ROOT/docs/releases/RELEASE-NOTES-${VERSION_TAG}.md"
LEGACY_NOTES_FILE="$ROOT/RELEASE-NOTES-${VERSION_TAG}.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[workflow]${NC} $*"; }
ok()  { echo -e "${GREEN}  ✓${NC} $*"; }
warn(){ echo -e "${YELLOW}  ⚠${NC} $*"; }
fail(){ echo -e "${RED}  ✗${NC} $*"; }

phase_validate() {
    log "Validating release readiness for ${VERSION_TAG}..."

    local py_ver spec_ver
    py_ver=$(python3 -c "
import sys; sys.path.insert(0,'$ROOT/loofi-fedora-tweaks')
from version import __version__; print(__version__)
" 2>/dev/null || echo "UNKNOWN")
    spec_ver=$(grep '^Version:' "$SPEC_FILE" 2>/dev/null | awk '{print $2}' || echo "UNKNOWN")

    if [ "$py_ver" = "$VERSION_NO_V" ]; then ok "version.py: $py_ver"; else fail "version.py: $py_ver (expected $VERSION_NO_V)"; fi
    if [ "$spec_ver" = "$VERSION_NO_V" ]; then ok ".spec: $spec_ver"; else fail ".spec: $spec_ver (expected $VERSION_NO_V)"; fi

    if grep -q "\[$VERSION_NO_V\]" "$ROOT/CHANGELOG.md" 2>/dev/null || grep -q "\[$VERSION_TAG\]" "$ROOT/CHANGELOG.md" 2>/dev/null; then
        ok "CHANGELOG.md has $VERSION_TAG entry"
    else
        warn "CHANGELOG.md missing $VERSION_TAG entry"
    fi

    if [ -f "$NOTES_FILE" ]; then
        ok "Release notes exist: docs/releases/RELEASE-NOTES-${VERSION_TAG}.md"
    elif [ -f "$LEGACY_NOTES_FILE" ]; then
        ok "Release notes exist: RELEASE-NOTES-${VERSION_TAG}.md (legacy path)"
    else
        warn "Release notes missing: docs/releases/RELEASE-NOTES-${VERSION_TAG}.md"
    fi

    if [ -f "$TASKS_FILE" ]; then ok "Task artifact exists"; else warn "Task artifact missing: $TASKS_FILE"; fi
    if [ -f "$TEST_REPORT_FILE" ]; then ok "Test report artifact exists"; else warn "Test report artifact missing: $TEST_REPORT_FILE"; fi

    for script in build_rpm.sh build_flatpak.sh build_appimage.sh build_sdist.sh; do
        local path="$ROOT/scripts/$script"
        if [ -f "$path" ] && [ -x "$path" ]; then
            ok "$script: executable"
        elif [ -f "$path" ]; then
            warn "$script: exists but not executable"
        else
            fail "$script: missing"
        fi
    done

    log "Running tests..."
    if PYTHONPATH="$ROOT/loofi-fedora-tweaks" python3 -m pytest "$ROOT/tests/" -q --tb=line 2>/dev/null; then
        ok "All tests pass"
    else
        fail "Tests failing"
    fi

    log "Running lint..."
    if flake8 "$ROOT/loofi-fedora-tweaks/" --max-line-length=150 --ignore=E501,W503,E402,E722 --quiet 2>/dev/null; then
        ok "Lint clean"
    else
        warn "Lint issues found"
    fi
}

run_phase() {
    local requested="$1"
    local mapped="$requested"

    case "$requested" in
        implement) mapped="build" ;;
        document) mapped="doc" ;;
        build|doc|plan|design|test|package|release|all) ;;
        *)
            fail "Unknown phase: $requested"
            echo "Available: plan, design, implement, test, document, package, release, validate, all"
            exit 1
            ;;
    esac

    if [ ! -f "$RUNNER" ]; then
        fail "Missing Python runner: $RUNNER"
        exit 1
    fi

    log "Delegating phase '$requested' -> '$mapped' via scripts/workflow_runner.py"
    python3 "$RUNNER" --phase "$mapped" --target-version "$VERSION_TAG" "${EXTRA_ARGS[@]}"
}

case "$PHASE" in
    validate)
        phase_validate
        ;;
    all)
        phase_validate
        run_phase all
        ;;
    plan|design|implement|test|document|package|release|build|doc)
        run_phase "$PHASE"
        ;;
    *)
        fail "Unknown phase: $PHASE"
        echo "Available: plan, design, implement, test, document, package, release, validate, all"
        exit 1
        ;;
esac
