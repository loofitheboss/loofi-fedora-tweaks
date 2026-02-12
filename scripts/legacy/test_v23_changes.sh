#!/usr/bin/env bash
# Test runner for v23.0 Architecture Hardening tests
# Run with: bash scripts/legacy/test_v23_changes.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORT_DIR="$PROJECT_DIR/docs/reports/v23"
mkdir -p "$REPORT_DIR"

cd "$PROJECT_DIR"

echo "=================================="
echo "v23.0 Architecture Hardening Tests"
echo "=================================="
echo

# Set Python path
export PYTHONPATH="$PROJECT_DIR/loofi-fedora-tweaks"

echo "✓ Python path set: $PYTHONPATH"
echo

# Test 1: Validate syntax
echo "[1/4] Validating Python syntax..."
python3 -m py_compile tests/test_command_worker.py && echo "  ✓ test_command_worker.py"
python3 -m py_compile tests/test_package_service.py && echo "  ✓ test_package_service.py"
python3 -m py_compile tests/test_system_service.py && echo "  ✓ test_system_service.py"
echo

# Test 2: Run new tests only
echo "[2/4] Running new v23.0 tests..."
python3 -m pytest \
    tests/test_command_worker.py \
    tests/test_package_service.py \
    tests/test_system_service.py \
    -v \
    --tb=short \
    2>&1 | tee "$REPORT_DIR/test_v23_output.log"
echo

# Test 3: Run full test suite
echo "[3/4] Running full test suite..."
python3 -m pytest tests/ -v --cov-fail-under=80 2>&1 | tee "$REPORT_DIR/test_full_output.log"
echo

# Test 4: Generate coverage report
echo "[4/4] Generating coverage report for v23.0 modules..."
python3 -m pytest \
    tests/test_command_worker.py \
    tests/test_package_service.py \
    tests/test_system_service.py \
    --cov=loofi-fedora-tweaks/core/workers/command_worker \
    --cov=loofi-fedora-tweaks/services/package/service \
    --cov=loofi-fedora-tweaks/services/system/service \
    --cov-report=term-missing \
    --cov-report=html:"$REPORT_DIR/htmlcov" \
    2>&1 | tee "$REPORT_DIR/test_coverage_output.log"
echo

echo "=================================="
echo "Test run complete!"
echo "Results saved to:"
echo "  - docs/reports/v23/test_v23_output.log"
echo "  - docs/reports/v23/test_full_output.log"
echo "  - docs/reports/v23/test_coverage_output.log"
echo "  - docs/reports/v23/htmlcov/ (coverage HTML report)"
echo "=================================="
