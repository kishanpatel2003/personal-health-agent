from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


# --- API keys (lazy — only fail when actually used) ---
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# --- Paths ---
VAULT_PATH = Path(os.environ.get("BRYAN_VAULT_PATH", str(Path.home() / ".local/share/personal-health-agent/vault"))).expanduser()
DB_PATH = Path(os.environ.get("BRYAN_DB_PATH", str(Path.home() / ".local/share/personal-health-agent/metrics.db"))).expanduser()
AUDIT_PATH = VAULT_PATH / ".audit"
PROFILE_PATH = Path(os.environ["BRYAN_PROFILE_PATH"]).expanduser() if os.environ.get("BRYAN_PROFILE_PATH") else None

# --- Vault subdirectories ---
CANONICAL_PATH = VAULT_PATH / "canonical"
SCRATCH_PATH = VAULT_PATH / "scratch"
LOGS_PATH = VAULT_PATH / "logs"
SUMMARIES_PATH = VAULT_PATH / "summaries"
ISSUES_PATH = VAULT_PATH / "issues"
MEDIA_PATH = VAULT_PATH / "media"

# --- Write policy ---
# Bryan can write freely to these paths
UNRESTRICTED_WRITE_PATHS = [SCRATCH_PATH, LOGS_PATH, ISSUES_PATH]
# Bryan can write to these only via promote_canonical()
GUARDED_WRITE_PATHS = [CANONICAL_PATH, SUMMARIES_PATH]

# --- Models ---
DEFAULT_MODEL = os.environ.get("BRYAN_MODEL", "claude-sonnet-4-6")
WEEKLY_REVIEW_MODEL = os.environ.get("BRYAN_WEEKLY_REVIEW_MODEL", "claude-opus-4-6")
