#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Secrets Baseline Update Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}📂 Project root: $PROJECT_ROOT${NC}"
echo ""

# Check if detect-secrets is installed
if ! command -v detect-secrets &> /dev/null; then
    echo -e "${YELLOW}⚙️  detect-secrets not found. Installing...${NC}"

    # Try pipx first (cleanest), then pip with --user, then with --break-system-packages
    if command -v pipx &> /dev/null; then
        echo -e "${BLUE}   Using pipx for isolated installation...${NC}"
        pipx install detect-secrets==1.5.0 --force
        # Make sure pipx bin is in PATH
        export PATH="$HOME/.local/bin:$PATH"
    elif python3 -m pip install --user -q detect-secrets==1.5.0 2>/dev/null; then
        echo -e "${BLUE}   Installed with pip --user${NC}"
        export PATH="$HOME/.local/bin:$PATH"
    else
        echo -e "${YELLOW}   Using --break-system-packages (externally managed environment)${NC}"
        pip install --break-system-packages -q detect-secrets==1.5.0
    fi

    echo -e "${GREEN}✅ detect-secrets installed${NC}"
else
    INSTALLED_VERSION=$(detect-secrets --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
    echo -e "${GREEN}✅ detect-secrets already installed (version: $INSTALLED_VERSION)${NC}"
fi
echo ""

# Backup current baseline
if [ -f ".secrets.baseline" ]; then
    echo -e "${YELLOW}💾 Backing up current baseline...${NC}"
    cp .secrets.baseline .secrets.baseline.backup

    # Get current baseline count
    CURRENT_COUNT=$(cat .secrets.baseline | jq '.results | length' 2>/dev/null || echo "0")
    echo -e "${BLUE}   Current baseline: $CURRENT_COUNT potential secrets${NC}"
else
    echo -e "${YELLOW}⚠️  No existing baseline found. Creating new baseline...${NC}"
    CURRENT_COUNT=0
fi
echo ""

# Update the baseline
echo -e "${YELLOW}🔍 Scanning codebase and updating baseline...${NC}"
if [ -f ".secrets.baseline" ]; then
    # Update existing baseline
    detect-secrets scan --baseline .secrets.baseline 2>&1 | grep -E "(Scanning|secrets)" || true
else
    # Create new baseline
    detect-secrets scan > .secrets.baseline 2>&1
    echo -e "${BLUE}   Created new baseline${NC}"
fi

# Get new count
NEW_COUNT=$(cat .secrets.baseline | jq '.results | length' 2>/dev/null || echo "0")
DIFF=$((NEW_COUNT - CURRENT_COUNT))

echo ""
echo -e "${BLUE}📊 Scan Results:${NC}"
echo -e "${BLUE}   Previous: $CURRENT_COUNT potential secrets${NC}"
echo -e "${BLUE}   Current:  $NEW_COUNT potential secrets${NC}"

if [ $DIFF -gt 0 ]; then
    echo -e "${YELLOW}   Change:   +$DIFF new detections${NC}"
elif [ $DIFF -lt 0 ]; then
    echo -e "${GREEN}   Change:   $DIFF (removed)${NC}"
else
    echo -e "${GREEN}   Change:   No change${NC}"
fi
echo ""

# Show some examples of what was detected (first 5)
if [ $NEW_COUNT -gt 0 ]; then
    echo -e "${YELLOW}📝 Sample detections (showing first 5):${NC}"
    cat .secrets.baseline | jq -r '.results | to_entries | .[:5] | .[] | "   \(.key + 1). \(.value.filename) (line \(.value.line_number))"' 2>/dev/null || echo "   (Unable to parse details)"
    echo ""
fi

# Check if there are changes to commit
if git diff --quiet .secrets.baseline; then
    echo -e "${GREEN}✅ Baseline is already up to date. No commit needed.${NC}"

    # Clean up backup
    if [ -f ".secrets.baseline.backup" ]; then
        rm .secrets.baseline.backup
    fi

    exit 0
fi

# Show diff summary
echo -e "${YELLOW}📝 Changes to baseline:${NC}"
git diff --stat .secrets.baseline | sed 's/^/   /'
echo ""

# Commit the changes
echo -e "${YELLOW}💾 Committing updated baseline...${NC}"
git add .secrets.baseline

# Create commit message
COMMIT_MSG="chore: update secrets baseline

Updated baseline from $CURRENT_COUNT to $NEW_COUNT potential secrets.
These detections include documentation examples, placeholder values,
and reference patterns that are not actual secrets.

Changes:
- Documentation passwords in example code
- Placeholder connection strings in skill references
- Example API keys in anti-pattern demonstrations
- Sample configuration values in MCP servers

All flagged patterns are in documentation/examples, not production config.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git commit -m "$COMMIT_MSG"

echo -e "${GREEN}✅ Baseline committed successfully${NC}"
echo ""

# Ask if user wants to push
echo -e "${YELLOW}🚀 Ready to push to remote?${NC}"
read -p "   Push now? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}📤 Pushing to remote...${NC}"
    git push
    echo -e "${GREEN}✅ Changes pushed successfully${NC}"
    echo ""
    echo -e "${GREEN}🎉 GitHub Actions will re-run with updated baseline${NC}"
else
    echo -e "${YELLOW}⏸️  Skipped push. Run 'git push' when ready.${NC}"
fi
echo ""

# Clean up backup
if [ -f ".secrets.baseline.backup" ]; then
    rm .secrets.baseline.backup
    echo -e "${BLUE}🧹 Cleaned up backup file${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Secrets baseline update complete!${NC}"
echo -e "${GREEN}========================================${NC}"
