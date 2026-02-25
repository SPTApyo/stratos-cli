#!/bin/bash

# STRATOS | FEDORA COPR AUTOMATOR
# Simplifies the creation and configuration of the DNF repository

BLUE='\033[0;34m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# Work from project root
cd "$(dirname "$0")/../.."

# Dynamic Metadata Extraction
APP_NAME=$(grep "__app_name__" stratos/__init__.py | cut -d '"' -f 2)
DESC=$(grep "__description__" stratos/__init__.py | cut -d '"' -f 2)
URL=$(grep "__url__" stratos/__init__.py | cut -d '"' -f 2)

echo -e "${CYAN}${BOLD}› STRATOS | FEDORA SETUP AUTOMATOR${NC}"
echo "------------------------------------------------"

# 1. Check for copr-cli
if ! command -v copr-cli &> /dev/null; then
    echo -e "${YELLOW}Warning: 'copr-cli' is not installed.${NC}"
    echo -e "On Arch, install it with: ${BOLD}yay -S copr-cli${NC}"
    exit 1
fi

# 2. Check for API Configuration
if [ ! -f ~/.config/copr ]; then
    echo -e "${RED}Error: COPR API not configured.${NC}"
    exit 1
fi

# Get username
USERNAME=$(copr-cli whoami | grep 'User' | awk '{print $NF}')
echo -e "${BLUE}› Detected Copr User: ${BOLD}${USERNAME}${NC}"

# 3. Create the COPR Project
echo -e "\n${BLUE}› Creating COPR project '${APP_NAME}'...${NC}"
copr-cli create "${APP_NAME}" --chroot fedora-rawhide-x86_64 --description "${DESC}" 2>/dev/null || echo "  Project already exists or basic creation done."

# 4. Add the GitHub SCM Package
echo -e "${BLUE}› Connecting GitHub repository to COPR...${NC}"
if ! copr-cli add-package-scm "${USERNAME}/${APP_NAME}" --name "${APP_NAME}" --clone-url "${URL}" --method "tito" --type "git" 2>/dev/null; then
    echo -e "${YELLOW}  Package already connected, updating configuration...${NC}"
    copr-cli edit-package-scm "${USERNAME}/${APP_NAME}" --name "${APP_NAME}" --clone-url "${URL}" --method "tito" --type "git"
fi

echo -e "\n${GREEN}${BOLD}SUCCESS: Fedora COPR is now configured!${NC}"
echo -e "Project URL: https://copr.fedorainfracloud.org/coprs/${USERNAME}/${APP_NAME}/"
