# Loofi Fedora Tweaks — Justfile
# Unified command interface for humans and AI agents.
# Run `just --list` to see all available commands.
#
# Install just: sudo dnf install just

# Default: show available commands
default:
    @just --list --unsorted

# === Configuration ===

# Project paths
src_root := "loofi-fedora-tweaks"
test_dir := "tests"

# Thresholds (single source of truth — CI workflows read these)
coverage_min := "75"
max_line_length := "150"
flake8_ignore := "E501,W503,E402,E722"

# ============================================================
#  Development
# ============================================================

# Run the application (GUI mode)
run:
    @echo "Starting Loofi Fedora Tweaks..."
    PYTHONPATH={{src_root}} python3 {{src_root}}/main.py

# Run the application in CLI mode
cli *ARGS:
    PYTHONPATH={{src_root}} python3 {{src_root}}/main.py --cli {{ARGS}}

# ============================================================
#  Testing
# ============================================================

# Run full test suite
test *ARGS:
    PYTHONPATH={{src_root}} python -m pytest {{test_dir}}/ -v --tb=short {{ARGS}}

# Run a single test file (e.g., just test-file test_commands)
test-file FILE:
    PYTHONPATH={{src_root}} python -m pytest {{test_dir}}/{{FILE}}.py -v

# Run a single test method (e.g., just test-method test_commands::TestClass::test_method)
test-method PATH:
    PYTHONPATH={{src_root}} python -m pytest {{test_dir}}/{{PATH}} -v

# Run tests with coverage report
test-coverage:
    PYTHONPATH={{src_root}} python -m pytest {{test_dir}}/ -v \
        --cov={{src_root}} \
        --cov-report=term-missing \
        --cov-fail-under={{coverage_min}}

# Run tests and output JUnit XML (for CI)
test-ci:
    PYTHONPATH={{src_root}} python -m pytest {{test_dir}}/ -v --tb=short \
        --cov={{src_root}} \
        --cov-report=term-missing \
        --cov-fail-under={{coverage_min}} \
        --junitxml=test-results.xml

# ============================================================
#  Code Quality
# ============================================================

# Lint with flake8
lint:
    flake8 {{src_root}}/ --max-line-length={{max_line_length}} --ignore={{flake8_ignore}}

# Type check with mypy
typecheck:
    mypy {{src_root}}/ --ignore-missing-imports --no-error-summary

# Run pre-commit hooks on all files
pre-commit:
    pre-commit run --all-files

# Full verification (lint + typecheck + tests + coverage)
verify:
    @echo "=== Lint ==="
    just lint
    @echo ""
    @echo "=== Type Check ==="
    just typecheck
    @echo ""
    @echo "=== Tests + Coverage ==="
    just test-coverage
    @echo ""
    @echo "=== All checks passed ==="

# ============================================================
#  Build & Package
# ============================================================

# Build RPM package
build-rpm:
    bash scripts/build_rpm.sh

# Build Flatpak bundle
build-flatpak:
    bash scripts/build_flatpak.sh

# Build source distribution
build-sdist:
    bash scripts/build_sdist.sh

# Build AppImage
build-appimage:
    bash scripts/build_appimage.sh

# Build all packages
build-all: build-rpm build-sdist

# ============================================================
#  AI Workflow & Agents
# ============================================================

# Generate project stats (.project-stats.json)
stats:
    PYTHONPATH={{src_root}} python3 scripts/project_stats.py

# Check if stats are fresh (CI mode — fails on drift)
stats-check:
    PYTHONPATH={{src_root}} python3 scripts/project_stats.py --check

# Sync AI agent adapters (canonical → Claude/Codex)
sync-agents:
    python3 scripts/sync_ai_adapters.py --render

# Check for adapter drift (CI mode — fails if out of sync)
check-drift:
    python3 scripts/sync_ai_adapters.py --check

# Validate release documentation
validate-release:
    PYTHONPATH={{src_root}} python3 scripts/check_release_docs.py

# Generate workflow reports (test results + run manifest)
workflow-reports:
    PYTHONPATH={{src_root}} python3 scripts/generate_workflow_reports.py

# Run full autoprove verification suite
autoprove:
    bash scripts/autoprove.sh

# ============================================================
#  Version Management
# ============================================================

# Bump version (dry-run first, then confirm)
bump-dry VERSION:
    PYTHONPATH={{src_root}} python3 scripts/bump_version.py {{VERSION}} --dry-run

# Bump version (actually applies changes)
bump VERSION:
    PYTHONPATH={{src_root}} python3 scripts/bump_version.py {{VERSION}}

# Show current version
version:
    @python3 -c "import sys; sys.path.insert(0, '{{src_root}}'); from version import __version__, __version_codename__; print(f'{__version__} \"{__version_codename__}\"')"

# ============================================================
#  MCP Servers
# ============================================================

# Start workflow MCP server (JSON-RPC over stdio)
mcp-workflow:
    python3 scripts/mcp_workflow_server.py

# Start agent sync MCP server (JSON-RPC over stdio)
mcp-agent-sync:
    python3 scripts/mcp_agent_sync_server.py

# Health check for GitHub MCP integration
mcp-health:
    bash scripts/mcp_github_health_check.sh

# ============================================================
#  Release Pipeline
# ============================================================

# Full release preparation (verify + validate + stats)
release-prep:
    @echo "=== Step 1: Verify code quality ==="
    just verify
    @echo ""
    @echo "=== Step 2: Validate release docs ==="
    just validate-release
    @echo ""
    @echo "=== Step 3: Check stats freshness ==="
    just stats-check
    @echo ""
    @echo "=== Step 4: Check agent sync ==="
    just check-drift
    @echo ""
    @echo "=== Release preparation complete ==="

# ============================================================
#  Utilities
# ============================================================

# Show project statistics summary
info:
    @echo "Loofi Fedora Tweaks"
    @just version
    @echo ""
    @echo "Tabs:  $(find {{src_root}}/ui -name '*_tab.py' ! -name 'base_tab.py' | wc -l) feature tabs"
    @echo "Tests: $(find {{test_dir}} -name 'test_*.py' | wc -l) test files"
    @echo "Utils: $(find {{src_root}}/utils -name '*.py' ! -name '__init__.py' | wc -l) modules"

# Clean build artifacts and caches
clean:
    rm -rf build/ dist/ *.egg-info __pycache__
    rm -rf .pytest_cache .mypy_cache .coverage htmlcov
    rm -f test-results.xml
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @echo "Cleaned."

# Scaffold a new plugin
create-plugin NAME:
    bash scripts/create_plugin.sh {{NAME}}
