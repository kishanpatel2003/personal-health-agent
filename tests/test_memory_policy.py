"""Offline tests use fictional records and isolated storage only."""
import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from bryan.db.queries import init_db, append_weight, get_weight_trend
from bryan.mcp_server import policy, vault_tools


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    root.mkdir()
    for module in (policy, vault_tools):
        monkeypatch.setattr(module, "VAULT_PATH", root)
    monkeypatch.setattr(policy, "AUDIT_PATH", root / ".audit")
    monkeypatch.setattr(policy, "UNRESTRICTED_WRITE_PATHS", [root / p for p in ("scratch", "logs", "issues")])
    monkeypatch.setattr(policy, "GUARDED_WRITE_PATHS", [root / p for p in ("canonical", "summaries")])
    return root


def test_database_is_empty_and_synthetic_metric_roundtrips(tmp_path):
    db = tmp_path / "metrics.db"
    asyncio.run(init_db(db))
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM weight_log").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM body_comp_log").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM nutrition_log").fetchone()[0] == 0
    asyncio.run(append_weight(db, "2030-01-01", 170.0, "fictional test record"))
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT weight_lbs FROM weight_log").fetchone()[0] == 170.0


def test_canonical_write_requires_promotion_and_is_audited(vault):
    with pytest.raises(PermissionError):
        asyncio.run(vault_tools.write_scratch("canonical/profile.md", "unreviewed"))
    asyncio.run(vault_tools.promote_canonical("canonical/profile.md", "Fictional subject", "confirmed synthetic fixture"))
    record = json.loads((vault / ".audit/writes.jsonl").read_text())
    assert record["action"] == "promote_canonical"
    assert record["reason"] == "confirmed synthetic fixture"
    assert (vault / "canonical/profile.md").read_text() == "Fictional subject"


def test_escape_and_symlink_writes_are_rejected(vault, tmp_path):
    with pytest.raises(PermissionError):
        asyncio.run(vault_tools.write_scratch("../outside.md", "blocked"))
    (vault / "scratch").mkdir()
    (vault / "scratch/escape").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(PermissionError):
        asyncio.run(vault_tools.write_scratch("scratch/escape/outside.md", "blocked"))
    assert not (tmp_path / "outside.md").exists()


def test_telegram_requires_explicit_allowed_user(monkeypatch):
    from bryan.telegram.bot import create_app
    monkeypatch.delenv("BRYAN_TELEGRAM_USER_ID", raising=False)
    with pytest.raises(RuntimeError, match="single authorized user"):
        create_app()
