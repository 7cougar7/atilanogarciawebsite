#!/bin/bash

# Aurora DSQL Django Fork Refresh Script
# This script fetches the latest commit from your fork and reinstalls it

set -e  # Exit on any error

# Configuration
REPO_URL="https://github.com/7cougar7/aurora-dsql-django.git"
BRANCH="version-0"
PACKAGE_NAME="aurora-dsql-django"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Aurora DSQL Django Fork Refresh Script${NC}"
echo "=================================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not detected. Activating...${NC}"
    source venv/bin/activate
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        echo -e "${RED}❌ Failed to activate virtual environment. Please run: source venv/bin/activate${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Virtual environment active: $VIRTUAL_ENV${NC}"

# Get the latest commit hash from the remote repository
echo -e "${BLUE}🔍 Fetching latest commit hash from $REPO_URL...${NC}"
LATEST_COMMIT=$(git ls-remote $REPO_URL $BRANCH | cut -f1)

if [[ -z "$LATEST_COMMIT" ]]; then
    echo -e "${RED}❌ Failed to fetch latest commit hash from $REPO_URL${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Latest commit: $LATEST_COMMIT${NC}"

# Check if the package is currently installed and get its info
echo -e "${BLUE}🔍 Checking current installation...${NC}"
CURRENT_INFO=$(pip show $PACKAGE_NAME 2>/dev/null || echo "Not installed")

if [[ "$CURRENT_INFO" != "Not installed" ]]; then
    echo -e "${YELLOW}📦 Current installation found:${NC}"
    echo "$CURRENT_INFO" | grep -E "(Name|Version|Location)"

    # Uninstall current version
    echo -e "${YELLOW}🗑️  Uninstalling current version...${NC}"
    pip uninstall $PACKAGE_NAME -y
else
    echo -e "${YELLOW}📦 Package not currently installed${NC}"
fi

# Install the latest version with force reinstall and no cache
echo -e "${BLUE}📥 Installing latest version from fork...${NC}"
INSTALL_URL="git+${REPO_URL}@${LATEST_COMMIT}"
echo -e "${BLUE}Installing: $INSTALL_URL${NC}"

pip install --force-reinstall --no-cache-dir "$INSTALL_URL"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Successfully installed latest version!${NC}"

    # Show installation info
    echo -e "${BLUE}📋 Installation details:${NC}"
    pip show $PACKAGE_NAME | grep -E "(Name|Version|Location)"

    # Update requirements.in with the new commit hash
    echo -e "${BLUE}📝 Updating requirements.in with latest commit...${NC}"
    if [[ -f "requirements.in" ]]; then
        # Create backup
        cp requirements.in requirements.in.backup

        # Update the line with the new commit hash
        sed -i.tmp "s|git+https://github.com/7cougar7/aurora-dsql-django.git@[a-f0-9]*|git+https://github.com/7cougar7/aurora-dsql-django.git@${LATEST_COMMIT}|g" requirements.in
        rm requirements.in.tmp

        echo -e "${GREEN}✅ Updated requirements.in with commit: $LATEST_COMMIT${NC}"

        # Ask if user wants to recompile requirements.txt
        echo -e "${YELLOW}🤔 Do you want to recompile requirements.txt? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}🔄 Recompiling requirements.txt...${NC}"
            pip-compile
            echo -e "${GREEN}✅ Requirements.txt updated${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  requirements.in not found, skipping update${NC}"
    fi

    # Test the installation
    echo -e "${BLUE}🧪 Testing installation...${NC}"
    python -c "
import aurora_dsql_django
from aurora_dsql_django.base import DatabaseWrapper
from aurora_dsql_django.schema import DatabaseSchemaEditor
print('✅ All imports successful')
print(f'Package location: {aurora_dsql_django.__file__}')
print(f'Version: {getattr(aurora_dsql_django, \"__version__\", \"Unknown\")}')
    "

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Installation test passed!${NC}"
        echo ""
        echo -e "${GREEN}🎉 Fork refresh completed successfully!${NC}"
        echo -e "${BLUE}Latest commit: $LATEST_COMMIT${NC}"
        echo -e "${BLUE}Package is ready to use with your latest changes.${NC}"
    else
        echo -e "${RED}❌ Installation test failed${NC}"
        exit 1
    fi

else
    echo -e "${RED}❌ Failed to install latest version${NC}"
    exit 1
fi
