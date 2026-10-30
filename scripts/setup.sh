#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Bryan v0.5 Setup ==="

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'" || {
    echo "ERROR: Python 3.11+ is required"
    exit 1
}

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Check .env exists
if [ ! -f .env ]; then
    echo ""
    echo "WARNING: .env file not found. Copying from template..."
    cp .env.template .env
    echo "Edit .env with your API keys before running Bryan."
fi

# Init SQLite database
echo "Initializing SQLite database..."
python3 -c "
import asyncio
from bryan.config import DB_PATH
from bryan.db.queries import init_db
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
asyncio.run(init_db(DB_PATH))
print(f'Database initialized at {DB_PATH}')
"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit .env with your ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN"
echo "  2. Run: python -m bryan.main"
