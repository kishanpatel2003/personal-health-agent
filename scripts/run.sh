#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Load .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "Starting Bryan v0.5..."
python3 -m bryan.main
