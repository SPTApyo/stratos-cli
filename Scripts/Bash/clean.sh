#!/bin/bash

# STRATOS | CLEANUP UTILITY
# Removes Python cache files, build artifacts, and temporary logs

BLUE='\033[0;34m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

# Work from project root
cd "$(dirname "$0")/../.."

echo -e "${BLUE}${BOLD}› STARTING CLEANUP...${NC}"

# 1. Remove Python cache
echo -e "  - Removing __pycache__ folders..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo -e "  - Removing .pyc and .pyo files..."
find . -type f -name "*.py[co]" -delete

# 2. Remove Build artifacts
echo -e "  - Removing build/ and dist/ folders..."
rm -rf build/
rm -rf dist/

echo -e "  - Removing .egg-info folders..."
rm -rf *.egg-info/

# 3. Remove Test & Tool caches
echo -e "  - Removing tool caches (.pytest, .ruff, .mypy)..."
rm -rf .pytest_cache/
rm -rf .ruff_cache/
rm -rf .mypy_cache/

# 4. Remove packaging temporary files
echo -e "  - Removing generated packaging files (PKGBUILD, spec)..."
rm -f PKGBUILD
rm -f stratos.spec

echo -e "\n${GREEN}${BOLD}SUCCESS: Project directory cleaned.${NC}"
