#!/bin/bash

# STRATOS | GIT HISTORY PURGE
# Destructive utility to reset git history to a single clean commit.

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

# Work from project root
cd "$(dirname "$0")/../.."

echo -e "${RED}${BOLD}!!! WARNING: DESTRUCTIVE OPERATION !!!${NC}"
echo -e "This script will ${BOLD}DELETE ALL GIT HISTORY${NC} and force push a single commit to origin main."
echo -e "Only use this when your codebase is stable and you want a clean public launch."
echo ""

read -p "Are you absolutely sure you want to proceed? (type 'PURGE' to confirm): " CONFIRM

if [ "$CONFIRM" != "PURGE" ]; then
    echo "Aborted."
    exit 0
fi

# 1. Verification
if [ ! -d .git ]; then
    echo -e "${RED}Error: Not a git repository.${NC}"
    exit 1
fi

# 2. Preparation
echo -e "\n${YELLOW}› Cleaning up local workspace...${NC}"
if [ -f "./Scripts/Bash/clean.sh" ]; then
    ./Scripts/Bash/clean.sh
fi

# 3. Purging History
echo -e "${YELLOW}› Creating clean branch...${NC}"
git checkout --orphan latest_branch

echo -e "${YELLOW}› Staging all files...${NC}"
git add -A

echo -e "${YELLOW}› Committing initial release...${NC}"
git commit -m "Initial Release: Stratos v0.1"

echo -e "${YELLOW}› Replacing main branch...${NC}"
git branch -D main
git branch -m main

# 4. Final Push
echo -e "\n${RED}${BOLD}FINAL STEP: FORCING UPDATE TO GITHUB${NC}"
echo -e "Command: git push -f origin main"
read -p "Press Enter to execute the final push or Ctrl+C to stop here..."

git push -f origin main

echo -e "\n${GREEN}${BOLD}SUCCESS: GitHub history has been purged.${NC}"
echo "Your repository is now clean with a single 'Initial Release' commit."
