#!/bin/bash

# STRATOS | DEVELOPMENT RUNNER
# Runs Stratos locally without system installation

# Work from project root
cd "$(dirname "$0")/../.."

# 1. Environment Setup
if [ ! -d "stratos/venv" ]; then
    echo "› Initializing development environment..."
    python3 -m venv stratos/venv
    source stratos/venv/bin/activate
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    pip install -e . --quiet
else
    source stratos/venv/bin/activate
fi

# 2. Execution
# We use 'python3 -m stratos' to ensure local package resolution
python3 -m stratos "$@"
