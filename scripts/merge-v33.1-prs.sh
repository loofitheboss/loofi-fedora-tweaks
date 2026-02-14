#!/bin/bash
# v33.1 PR Merge Campaign — Automated Execution Script
# This script automates the PR merge sequence where possible
# Manual steps still required for review and approval

set -e  # Exit on error

REPO="loofitheboss/loofi-fedora-tweaks"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "v33.1 PR Merge Campaign"
echo "Repository: $REPO"
echo "=========================================="

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}ERROR: GitHub CLI (gh) is not installed${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}ERROR: Not authenticated with GitHub CLI${NC}"
    echo "Run: gh auth login"
    exit 1
fi

wait_for_checks() {
    local pr_number=$1
    echo -e "${YELLOW}Waiting for CI checks on PR #$pr_number...${NC}"
    
    # Wait up to 10 minutes for checks
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        status=$(gh pr view "$pr_number" --json statusCheckRollup --jq '.statusCheckRollup[] | select(.conclusion != null) | .conclusion' | sort -u)
        
        if echo "$status" | grep -q "FAILURE\|CANCELLED\|TIMED_OUT"; then
            echo -e "${RED}CI checks failed for PR #$pr_number${NC}"
            return 1
        fi
        
        if echo "$status" | grep -q "SUCCESS" && ! echo "$status" | grep -q "PENDING\|IN_PROGRESS"; then
            echo -e "${GREEN}CI checks passed for PR #$pr_number${NC}"
            return 0
        fi
        
        echo "  Checks still running... (attempt $((attempt+1))/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    echo -e "${RED}Timeout waiting for CI checks on PR #$pr_number${NC}"
    return 1
}

merge_pr() {
    local pr_number=$1
    local description=$2
    
    echo ""
    echo "=========================================="
    echo "Merging PR #$pr_number: $description"
    echo "=========================================="
    
    # Check if PR is mergeable
    mergeable=$(gh pr view "$pr_number" --json mergeable --jq '.mergeable')
    if [ "$mergeable" != "MERGEABLE" ]; then
        echo -e "${RED}PR #$pr_number is not mergeable (conflicts or checks pending)${NC}"
        echo "Skipping... please resolve manually"
        return 1
    fi
    
    # Merge the PR
    if gh pr merge "$pr_number" --squash --auto; then
        echo -e "${GREEN}PR #$pr_number merged successfully${NC}"
        return 0
    else
        echo -e "${RED}Failed to merge PR #$pr_number${NC}"
        return 1
    fi
}

undraft_pr() {
    local pr_number=$1
    echo -e "${YELLOW}Marking PR #$pr_number as ready for review...${NC}"
    gh pr ready "$pr_number"
}

close_pr() {
    local pr_number=$1
    local reason=$2
    echo -e "${YELLOW}Closing PR #$pr_number...${NC}"
    gh pr close "$pr_number" --comment "$reason"
}

trigger_dependabot_rebase() {
    local pr_number=$1
    echo -e "${YELLOW}Requesting Dependabot rebase for PR #$pr_number...${NC}"
    gh pr comment "$pr_number" --body "@dependabot rebase"
    echo "  Waiting 30 seconds for Dependabot to respond..."
    sleep 30
}

# ========================================
# PHASE 1: Security Fix
# ========================================
echo ""
echo "=========================================="
echo "PHASE 1: Security Fix (PR #24)"
echo "=========================================="

echo "Step 1: Undraft PR #24"
if undraft_pr 24; then
    echo "Step 2: Merge PR #24"
    merge_pr 24 "Fix command injection vulnerabilities"
else
    echo -e "${RED}Failed to undraft PR #24. Check if it's already undrafted.${NC}"
fi

# ========================================
# PHASE 2: Close Obsolete PR
# ========================================
echo ""
echo "=========================================="
echo "PHASE 2: Close Obsolete PR (PR #14)"
echo "=========================================="

close_pr 14 "Closing in favor of comprehensive fix in PR #24"

# ========================================
# PHASE 3: CI/CD Action Upgrades
# ========================================
echo ""
echo "=========================================="
echo "PHASE 3: CI/CD Action Upgrades"
echo "=========================================="

# PR #23: actions/checkout
echo ""
echo "Step 3: PR #23 - actions/checkout 4→6"
trigger_dependabot_rebase 23
merge_pr 23 "ci: bump actions/checkout from 4 to 6"

# PR #19: actions/upload-artifact
echo ""
echo "Step 4: PR #19 - actions/upload-artifact 4→6"
trigger_dependabot_rebase 19
merge_pr 19 "ci: bump actions/upload-artifact from 4 to 6"

# PR #22: peter-evans/create-pull-request
echo ""
echo "Step 5: PR #22 - peter-evans/create-pull-request 7→8"
merge_pr 22 "ci: bump peter-evans/create-pull-request from 7 to 8"

# PR #21: actions/ai-inference
echo ""
echo "Step 6: PR #21 - actions/ai-inference 1→2"
merge_pr 21 "ci: bump actions/ai-inference from 1 to 2"

# PR #18: actions/stale
echo ""
echo "Step 7: PR #18 - actions/stale 9→10"
merge_pr 18 "ci: bump actions/stale from 9 to 10"

# ========================================
# PHASE 4: Dependency Updates
# ========================================
echo ""
echo "=========================================="
echo "PHASE 4: Dependency Updates (PR #20)"
echo "=========================================="

echo ""
echo "Step 8: PR #20 - fastapi 0.128.5→0.129.0"
merge_pr 20 "deps: bump fastapi from 0.128.5 to 0.129.0"

# ========================================
# PHASE 5: Test & Type Fixes
# ========================================
echo ""
echo "=========================================="
echo "PHASE 5: Test & Type Fixes (PR #26)"
echo "=========================================="

echo ""
echo -e "${YELLOW}PR #26 requires manual rebase first${NC}"
echo "Run these commands:"
echo "  gh pr checkout 26"
echo "  git fetch origin master"
echo "  git rebase origin/master"
echo "  # Resolve conflicts if any"
echo "  git push origin copilot/fix-all-pull-requests --force-with-lease"
echo ""
echo "After rebase, run:"
echo "  gh pr ready 26"
echo "  gh pr merge 26 --squash --auto"

# ========================================
# Summary
# ========================================
echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo "Automated steps completed."
echo ""
echo "Next manual steps:"
echo "1. Verify all PRs merged successfully"
echo "2. Rebase and merge PR #26 (test fixes)"
echo "3. Update CHANGELOG.md"
echo "4. Check master CI status"
echo ""
echo "View recent workflow runs:"
echo "  gh run list --limit 10"
echo ""
echo -e "${GREEN}Done!${NC}"
