#!/bin/bash

# STRATOS | GLOBAL INSTALLER & UNINSTALLER
# Industrial-grade tool for Linux systems

BLUE='\033[0;34m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# Dynamic Metadata Extraction
VERSION=$(grep "__version__" stratos/__init__.py | cut -d '"' -f 2)
APP_NAME=$(grep "__app_name__" stratos/__init__.py | cut -d '"' -f 2)
DESCRIPTION=$(grep "__description__" stratos/__init__.py | cut -d '"' -f 2)

echo -e "${CYAN}${BOLD}"
echo " ███           █████████  ██████████ █████████    ████████   ██████████  █████████   █████████ "
echo "░░░███        ███░░░░░███░░░░░███░░░░███░░░░███  ███░░░░░███░░░░░███░░░ ███░░░░░███ ███░░░░░███"
echo "  ░░░███     ░███    ░░░     ░███   ░███   ░███ ░███    ░███    ░███   ░███    ░███░███    ░░░ "
echo "    ░░░███   ░░█████████     ░███   ░█████████  ░███████████    ░███   ░███    ░███░░█████████ "
echo "     ███░     ░░░░░░░░███    ░███   ░███░░░░███ ░███░░░░░███    ░███   ░███    ░███ ░░░░░░░░███"
echo "   ███░       ███    ░███    ░███   ░███   ░███ ░███    ░███    ░███   ░███    ░███ ███    ░███"
echo " ███░        ░░█████████     █████  █████  ████ █████   █████   █████  ░░█████████ ░░█████████ "
echo "░░░           ░░░░░░░░░     ░░░░░  ░░░░░  ░░░░ ░░░░░   ░░░░░   ░░░░░    ░░░░░░░░░   ░░░░░░░░░  "
echo -e "${NC}"
echo -e "  ${BOLD}${APP_NAME} | SYSTEM TOOL v${VERSION}${NC}"
echo -e "  ${DESCRIPTION}"
echo "  ------------------------------------------------"

# 1. System Checks
echo -e "\n${BLUE}› Checking system requirements...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found. Please install Python 3.10 or higher.${NC}"
    exit 1
fi

PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}ERROR: Python requires 3.10+.${NC}"
    exit 1
fi
echo -e "${GREEN}  OK: Python detected.${NC}"

# 2. Main Menu
echo -e "\n${BOLD}SELECT ACTION:${NC}"
echo "  1) Global Install (Command 'stratos' everywhere)"
echo "  2) Local Install  (Developer mode - Current folder)"
echo "  3) Uninstall      (Remove all Stratos components)"
echo "  4) Cancel"
read -p "  Selection [1-4]: " MODE

case $MODE in
    1)
        echo -e "\n${BLUE}› Ensuring build tools are present...${NC}"
        python3 -m pip install --user setuptools wheel build --quiet --break-system-packages 2>/dev/null || python3 -m pip install --user setuptools wheel build --quiet

        echo -e "\n${BLUE}› Installing ${APP_NAME} globally...${NC}"
        if command -v pipx &> /dev/null; then
            pipx install . --force
        else
            python3 -m pip install . --user --break-system-packages 2>/dev/null || python3 -m pip install . --user
        fi
        
        USER_BIN="$HOME/.local/bin"
        if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
            echo -e "\n${RED}${BOLD}ACTION REQUIRED: PATH CONFIGURATION${NC}"
            echo -e "The directory ${BOLD}$USER_BIN${NC} is not in your PATH."
            echo -e "Add this to your ${BOLD}.bashrc${NC} or ${BOLD}.zshrc${NC}:"
            echo -e "\n  ${CYAN}export PATH=\$PATH:$USER_BIN${NC}\n"
        fi
        
        echo -e "\n${GREEN}${BOLD}SUCCESS: ${APP_NAME} installed!${NC}"
        ;;
    2)
        echo -e "\n${BLUE}› Initializing local environment...${NC}"
        python3 -m venv stratos/venv
        source stratos/venv/bin/activate
        pip install --upgrade pip setuptools wheel build --quiet
        pip install -e . --quiet
        echo -e "\n${GREEN}${BOLD}SUCCESS: Local environment ready.${NC}"
        ;;
    3)
        echo -e "\n${RED}› STARTING DEEP UNINSTALLATION...${NC}"
        
        # 1. Try pip/pipx removal for both possible names
        echo -e "  - Removing packages via pip/pipx..."
        for pkg in "stratos-core" "stratos-cli"; do
            if command -v pipx &> /dev/null; then
                pipx uninstall $pkg &> /dev/null
            fi
            python3 -m pip uninstall $pkg --yes --break-system-packages &> /dev/null || python3 -m pip uninstall $pkg --yes &> /dev/null
        done
        
        # 2. Manual cleanup of bin files (Force cleanup of leftovers)
        echo -e "  - Cleaning up binary files..."
        rm -f "$HOME/.local/bin/stratos"
        sudo rm -f "/usr/local/bin/stratos" "/usr/bin/stratos" &> /dev/null
        
        # 3. Local Cleanup
        echo -e "  - Removing local venv and scripts..."
        rm -rf stratos/venv/
        rm -f stratos_run.sh
        
        # 4. Data Cleanup
        read -p "  Delete configuration (~/.config/stratos)? [y/N]: " CLEAN_CONF
        if [[ $CLEAN_CONF == "y" || $CLEAN_CONF == "Y" ]]; then
            rm -rf "$HOME/.config/stratos"
            echo -e "  - Config deleted."
        fi
        
        echo -e "\n${GREEN}${BOLD}SUCCESS: Stratos completely removed.${NC}"
        ;;
    *)
        exit 0
        ;;
esac

echo -e "\n${CYAN}------------------------------------------------"
echo -e "Thank you for using ${APP_NAME}.${NC}"
