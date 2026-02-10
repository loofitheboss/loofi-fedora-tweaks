#!/usr/bin/env bash
# Loofi Fedora Tweaks — Workflow Runner
# Automates the 7-phase pipeline for version releases.
#
# Usage:
#   ./scripts/workflow-runner.sh <version> [phase]
#
# Examples:
#   ./scripts/workflow-runner.sh 23.0.0          # Run all phases
#   ./scripts/workflow-runner.sh 23.0.0 test     # Run only test phase
#   ./scripts/workflow-runner.sh 23.0.0 validate # Validate release readiness
#
# Phases: plan, design, implement, test, document, package, release, validate

set -euo pipefail

VERSION="${1:?Usage: $0 <version> [phase]}"
PHASE="${2:-all}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASKS_FILE="$ROOT/.claude/workflow/tasks-v${VERSION}.md"
VERSION_PY="$ROOT/loofi-fedora-tweaks/version.py"
SPEC_FILE="$ROOT/loofi-fedora-tweaks.spec"

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

#--- Phase Functions ---

phase_validate() {
    log "Validating release readiness for v${VERSION}..."
    local errors=0

    # Version alignment
    local py_ver spec_ver
    py_ver=$(python3 -c "
import sys; sys.path.insert(0,'$ROOT/loofi-fedora-tweaks')
from version import __version__; print(__version__)
" 2>/dev/null || echo "UNKNOWN")
    spec_ver=$(grep '^Version:' "$SPEC_FILE" 2>/dev/null | awk '{print $2}' || echo "UNKNOWN")

    if [ "$py_ver" = "$VERSION" ]; then ok "version.py: $py_ver"; else fail "version.py: $py_ver (expected $VERSION)"; ((errors++)); fi
    if [ "$spec_ver" = "$VERSION" ]; then ok ".spec: $spec_ver"; else fail ".spec: $spec_ver (expected $VERSION)"; ((errors++)); fi

    # Documentation
    if grep -q "\[$VERSION\]" "$ROOT/CHANGELOG.md" 2>/dev/null; then ok "CHANGELOG.md has v$VERSION"; else warn "CHANGELOG.md missing v$VERSION entry"; fi
    if [ -f "$ROOT/RELEASE-NOTES-v${VERSION}.md" ]; then ok "Release notes exist"; else warn "RELEASE-NOTES-v${VERSION}.md missing"; fi

    # Task file
    if [ -f "$TASKS_FILE" ]; then ok "Task file exists"; else warn "Task file missing: $TASKS_FILE"; fi

    # Build scripts
    for script in build_rpm.sh build_flatpak.sh build_appimage.sh build_sdist.sh; do
        local path="$ROOT/scripts/$script"
        if [ -f "$path" ] && [ -x "$path" ]; then
            ok "$script: executable"
        elif [ -f "$path" ]; then
            warn "$script: exists but not executable"
        else
            fail "$script: missing"
            ((errors++))
        fi
    done

    # Tests
    log "Running tests..."
    if PYTHONPATH="$ROOT/loofi-fedora-tweaks" python3 -m pytest "$ROOT/tests/" -q --tb=line; then
        ok "All tests pass"
    else
        fail "Tests failing"
        ((errors++))
    fi

    # Lint
    log "Running lint..."
    if flake8 "$ROOT/loofi-fedora-tweaks/" --max-line-length=150 --ignore=E501,W503,E402,E722; then
        ok "Lint clean"
    else
        warn "Lint issues found (see output above)"
    fi

    # Exit with error if any hard checks failed
    if [ "$errors" -gt 0 ]; then
        fail "$errors validation error(s) found"
        exit 1
    fi
}

phase_plan() {
    log "P1: PLAN — Decomposing v${VERSION} into tasks"
    echo "Run with Claude Code:"
    echo ""
    echo "  claude --model haiku \"Read ROADMAP.md and .claude/workflow/prompts/plan.md."
    echo "  Execute P1 PLAN for v${VERSION}."
    echo "  Save task list to .claude/workflow/tasks-v${VERSION}.md\""
    echo ""
}

phase_design() {
    log "P2: DESIGN — Architecture review"
    if [ ! -f "$TASKS_FILE" ]; then fail "Run 'plan' phase first"; exit 1; fi
    echo "Run with Claude Code:"
    echo ""
    echo "  claude --model sonnet \"Read .claude/workflow/prompts/design.md."
    echo "  Execute P2 DESIGN for v${VERSION}."
    echo "  Review tasks in .claude/workflow/tasks-v${VERSION}.md\""
    echo ""
}

phase_implement() {
    log "P3: IMPLEMENT — Building v${VERSION}"
    if [ ! -f "$TASKS_FILE" ]; then fail "Run 'plan' phase first"; exit 1; fi
    echo "Run with Claude Code:"
    echo ""
    echo "  claude --model sonnet \"Read .claude/workflow/prompts/implement.md."
    echo "  Execute P3 IMPLEMENT for v${VERSION}."
    echo "  Work through tasks in .claude/workflow/tasks-v${VERSION}.md\""
    echo ""
}

phase_test() {
    log "P4: TEST — Running tests for v${VERSION}"
    echo "Run with Claude Code:"
    echo ""
    echo "  claude --model sonnet \"Read .claude/workflow/prompts/test.md."
    echo "  Execute P4 TEST for v${VERSION}.\""
    echo ""
    log "Or run directly:"
    echo "  PYTHONPATH=$ROOT/loofi-fedora-tweaks python3 -m pytest $ROOT/tests/ -v --cov=loofi-fedora-tweaks --cov-fail-under=80"
}

phase_document() {
    log "P5: DOCUMENT — Updating docs for v${VERSION}"
    echo "Run with Claude Code:"
    echo ""
    echo "  claude --model haiku \"Read .claude/workflow/prompts/document.md."
    echo "  Execute P5 DOCUMENT for v${VERSION}.\""
    echo ""
}

phase_package() {
    log "P6: PACKAGE — Validating packaging for v${VERSION}"
    echo "Run with Claude Code:"
    echo ""
    echo "  claude --model haiku \"Read .claude/workflow/prompts/package.md."
    echo "  Execute P6 PACKAGE for v${VERSION}.\""
    echo ""
    log "Or run directly:"
    echo "  bash $ROOT/scripts/build_rpm.sh"
}

phase_release() {
    log "P7: RELEASE — Releasing v${VERSION}"
    echo ""
    echo "Manual steps:"
    echo "  1. git checkout -b release/v${VERSION%.*}"
    echo "  2. git tag v${VERSION}"
    echo "  3. git push origin release/v${VERSION%.*} --tags"
    echo "  4. GitHub Actions will create the release automatically"
    echo ""
    echo "Or use Claude Code:"
    echo "  claude --model haiku \"Read .claude/workflow/prompts/release.md."
    echo "  Execute P7 RELEASE for v${VERSION}.\""
}

#--- Main ---

case "$PHASE" in
    all)
        phase_validate
        echo ""
        log "To run the full pipeline, execute each phase:"
        echo "  $0 $VERSION plan"
        echo "  $0 $VERSION design"
        echo "  $0 $VERSION implement"
        echo "  $0 $VERSION test"
        echo "  $0 $VERSION document"
        echo "  $0 $VERSION package"
        echo "  $0 $VERSION release"
        ;;
    plan)      phase_plan ;;
    design)    phase_design ;;
    implement) phase_implement ;;
    test)      phase_test ;;
    document)  phase_document ;;
    package)   phase_package ;;
    release)   phase_release ;;
    validate)  phase_validate ;;
    *)
        echo "Unknown phase: $PHASE"
        echo "Available: plan, design, implement, test, document, package, release, validate, all"
        exit 1
        ;;
esac
