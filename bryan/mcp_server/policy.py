"""Write-scope enforcement and audit logging for Bryan MCP server."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from bryan.config import AUDIT_PATH, GUARDED_WRITE_PATHS, UNRESTRICTED_WRITE_PATHS, VAULT_PATH


def _is_under(path: Path, roots: list[Path]) -> bool:
    """Return True if *path* is equal to or a child of any root."""
    resolved = path.resolve()
    return any(resolved == r.resolve() or r.resolve() in resolved.resolve().parents for r in roots)


def validate_write_path(path: Path, *, guarded: bool = False) -> None:
    """Enforce write-scope policy.

    Raises ``PermissionError`` if *path* is not under the vault root.
    When *guarded* is ``False``, also raises if *path* falls under any
    GUARDED_WRITE_PATHS (canonical/, summaries/).  When *guarded* is
    ``True``, both UNRESTRICTED and GUARDED paths are allowed.
    """
    resolved = path.resolve()
    vault_resolved = VAULT_PATH.resolve()

    # Must be under vault root.
    if vault_resolved not in resolved.parents and resolved != vault_resolved:
        raise PermissionError(
            f"Path {resolved} is not under the vault root ({vault_resolved})"
        )

    allowed_roots = list(UNRESTRICTED_WRITE_PATHS)
    if guarded:
        allowed_roots.extend(GUARDED_WRITE_PATHS)

    if not _is_under(resolved, allowed_roots):
        raise PermissionError(
            f"Write to {resolved} is not permitted. "
            f"Allowed roots: {[str(r) for r in allowed_roots]}"
        )


def audit_write(
    path: Path,
    action: str,
    reason: str | None = None,
    session_id: str | None = None,
) -> None:
    """Append a JSON-lines record to the audit log.

    Creates the audit directory on first call if it does not exist.
    """
    audit_dir = AUDIT_PATH
    audit_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": str(path),
        "action": action,
        "reason": reason,
        "session_id": session_id,
    }

    log_file = audit_dir / "writes.jsonl"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
