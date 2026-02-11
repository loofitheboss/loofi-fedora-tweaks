#!/usr/bin/env bash
# Loofi Fedora Tweaks — Automated Proof System
# Validates all tests, linters, and build artifacts for a version
# Usage: bash scripts/autoprove.sh [version]

set -euo pipefail

VERSION="${1:-$(grep -oP '__version__ = "\K[^"]+' loofi-fedora-tweaks/version.py)}"
PHASE="${2:-all}"
FAILED=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[AUTOPROVE]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; FAILED=$((FAILED + 1)); }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

log "Auto-verification for v${VERSION} — Phase: ${PHASE}"
echo "=================================================="

# Phase 1: Environment Check
if [[ "$PHASE" == "all" || "$PHASE" == "env" ]]; then
    log "Phase 1: Environment Check"
    
    if [[ -d ".venv" ]]; then
        success "Virtual environment exists"
    else
        warn "No .venv found, using system Python"
    fi
    
    if command -v python3 &> /dev/null; then
        PY_VERSION=$(python3 --version)
        success "Python: $PY_VERSION"
    else
        error "Python3 not found"
    fi
    
    if python3 -c "import PyQt6" 2>/dev/null; then
        success "PyQt6 installed"
    else
        error "PyQt6 not installed"
    fi
    
    echo ""
fi

# Phase 2: Syntax Check
if [[ "$PHASE" == "all" || "$PHASE" == "syntax" ]]; then
    log "Phase 2: Syntax Validation"
    
    if python3 -m py_compile loofi-fedora-tweaks/main.py 2>/dev/null; then
        success "main.py syntax valid"
    else
        error "main.py has syntax errors"
    fi
    
    SYNTAX_ERRORS=0
    while IFS= read -r pyfile; do
        if ! python3 -m py_compile "$pyfile" 2>/dev/null; then
            error "Syntax error in $pyfile"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    done < <(find loofi-fedora-tweaks -name "*.py" -type f)
    
    if [[ $SYNTAX_ERRORS -eq 0 ]]; then
        success "All Python files have valid syntax"
    else
        error "$SYNTAX_ERRORS files have syntax errors"
    fi
    
    echo ""
fi

# Phase 3: Linting
if [[ "$PHASE" == "all" || "$PHASE" == "lint" ]]; then
    log "Phase 3: Code Quality (flake8)"
    
    if command -v flake8 &> /dev/null; then
        if flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722 --count --statistics 2>&1 | tee /tmp/flake8.log; then
            success "flake8: No issues"
        else
            warn "flake8: Found issues (see above)"
        fi
    else
        warn "flake8 not installed, skipping"
    fi
    
    echo ""
fi

# Phase 4: Unit Tests
if [[ "$PHASE" == "all" || "$PHASE" == "test" ]]; then
    log "Phase 4: Unit Tests"
    
    export PYTHONPATH=loofi-fedora-tweaks
    
    # Run all tests with coverage
    if python3 -m pytest tests/ -v --tb=short --maxfail=5 2>&1 | tee /tmp/pytest.log; then
        PASSED=$(grep -oP '\d+(?= passed)' /tmp/pytest.log | tail -1 || echo "0")
        success "All tests passed ($PASSED tests)"
    else
        ERROR_COUNT=$(grep -oP '\d+(?= failed)' /tmp/pytest.log | tail -1 || echo "unknown")
        error "$ERROR_COUNT tests failed"
    fi
    
    echo ""
fi

# Phase 5: Plugin Tests (P4 specific)
if [[ "$PHASE" == "all" || "$PHASE" == "p4" || "$PHASE" == "plugin" ]]; then
    log "Phase 5: Plugin Architecture Tests (P4)"
    
    export PYTHONPATH=loofi-fedora-tweaks
    
    P4_FILES=(
        "tests/test_plugin_registry.py"
        "tests/test_plugin_loader.py"
        "tests/test_plugin_compat.py"
        "tests/test_plugin_integration.py"
    )
    
    PLUGIN_PASSED=0
    PLUGIN_TOTAL=0
    
    for testfile in "${P4_FILES[@]}"; do
        if [[ -f "$testfile" ]]; then
            if python3 -m pytest "$testfile" -v --tb=short 2>&1 | tee /tmp/p4_test.log; then
                COUNT=$(grep -oP '\d+(?= passed)' /tmp/p4_test.log | tail -1 || echo "0")
                success "$testfile: $COUNT tests passed"
                PLUGIN_PASSED=$((PLUGIN_PASSED + COUNT))
            else
                FAIL_COUNT=$(grep -oP '\d+(?= failed)' /tmp/p4_test.log | tail -1 || echo "0")
                error "$testfile: $FAIL_COUNT tests failed"
            fi
            
            TOTAL=$(grep -oP '\d+(?= (passed|failed))' /tmp/p4_test.log | tail -1 || echo "0")
            PLUGIN_TOTAL=$((PLUGIN_TOTAL + TOTAL))
        else
            error "$testfile not found"
        fi
    done
    
    if [[ $PLUGIN_PASSED -eq $PLUGIN_TOTAL ]]; then
        success "P4: All $PLUGIN_TOTAL plugin tests passed"
    else
        error "P4: Only $PLUGIN_PASSED/$PLUGIN_TOTAL tests passed"
    fi
    
    echo ""
fi

# Phase 6: Import Validation
if [[ "$PHASE" == "all" || "$PHASE" == "import" ]]; then
    log "Phase 6: Import Validation"
    
    export PYTHONPATH=loofi-fedora-tweaks
    
    if python3 -c "from utils.plugin_registry import PluginRegistry" 2>/dev/null; then
        success "PluginRegistry imports"
    else
        error "PluginRegistry import failed"
    fi
    
    if python3 -c "from utils.plugin_loader import PluginLoader" 2>/dev/null; then
        success "PluginLoader imports"
    else
        error "PluginLoader import failed"
    fi
    
    if python3 -c "from utils.plugin_compat import CompatibilityDetector" 2>/dev/null; then
        success "CompatibilityDetector imports"
    else
        error "CompatibilityDetector import failed"
    fi
    
    echo ""
fi

# Phase 7: Build Validation
if [[ "$PHASE" == "all" || "$PHASE" == "build" ]]; then
    log "Phase 7: Build System Check"
    
    if [[ -f "loofi-fedora-tweaks.spec" ]]; then
        success "RPM spec file exists"
        
        SPEC_VERSION=$(grep -oP '^Version:\s+\K.*' loofi-fedora-tweaks.spec)
        if [[ "$SPEC_VERSION" == "$VERSION" ]]; then
            success "Spec version matches: $VERSION"
        else
            error "Version mismatch: spec=$SPEC_VERSION, version.py=$VERSION"
        fi
    else
        error "loofi-fedora-tweaks.spec not found"
    fi
    
    if [[ -f "scripts/build_rpm.sh" ]]; then
        success "build_rpm.sh exists"
    else
        error "build_rpm.sh not found"
    fi
    
    echo ""
fi

# Phase 8: Documentation Check
if [[ "$PHASE" == "all" || "$PHASE" == "docs" ]]; then
    log "Phase 8: Documentation"
    
    DOCS=(
        "README.md"
        "ROADMAP.md"
        "CHANGELOG.md"
        "AGENTS.md"
    )
    
    for doc in "${DOCS[@]}"; do
        if [[ -f "$doc" ]]; then
            success "$doc exists"
        else
            warn "$doc missing"
        fi
    done
    
    echo ""
fi

# Final Report
echo "=================================================="
if [[ $FAILED -eq 0 ]]; then
    success "AUTO-PROOF COMPLETE: All checks passed! ✓"
    exit 0
else
    error "AUTO-PROOF FAILED: $FAILED check(s) failed"
    exit 1
fi
