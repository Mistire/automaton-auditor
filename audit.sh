#!/bin/bash

# Simple wrapper for the Automaton Auditor
# Usage: ./audit <repo_url> or ./audit .

REPO_URL=$1

if [ -z "$REPO_URL" ]; then
    echo "Usage: ./audit <repo_url> or ./audit ."
    exit 1
fi

# Detect local audit
if [ "$REPO_URL" == "." ]; then
    LOCAL_PATH="."
    # Use current folder name as dummy URL
    REPO_URL="LOCAL_AUDIT_WORKSPACE"
fi

echo "⚖️ Launching Adaptive Auditor Swarm..."
.venv/bin/python3 main.py --repo_url "$REPO_URL" --local_repo_path "$LOCAL_PATH"
