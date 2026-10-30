"""Vault interaction tools for the Bryan MCP server.

Every function is a plain ``async`` callable that will be registered as an MCP
tool by ``server.py``.  All paths supplied by the caller are **relative to the
vault root** (``VAULT_PATH``).
"""

from __future__ import annotations

from pathlib import Path

from bryan.config import VAULT_PATH
from bryan.mcp_server.policy import audit_write, validate_write_path


def _resolve_vault_path(relative: str) -> Path:
    """Turn a caller-supplied relative path into an absolute one and ensure
    it stays inside the vault."""
    resolved = (VAULT_PATH / relative).resolve()
    vault_resolved = VAULT_PATH.resolve()
    if vault_resolved not in resolved.parents and resolved != vault_resolved:
        raise PermissionError(
            f"Path {resolved} escapes the vault root ({vault_resolved})"
        )
    return resolved


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def read_note(path: str) -> str:
    """Read a markdown file from the vault.

    *path* is relative to the vault root (e.g. ``canonical/weekly-review.md``).
    Returns the full contents of the file as a string.
    """
    target = _resolve_vault_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Note not found: {path}")
    if not target.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")
    return target.read_text(encoding="utf-8")


async def write_scratch(path: str, content: str) -> str:
    """Write a file to scratch/ or logs/ (unrestricted write zones).

    *path* is relative to the vault root (must start with ``scratch/`` or
    ``logs/``).  Parent directories are created automatically.
    Returns a confirmation message.
    """
    target = _resolve_vault_path(path)
    validate_write_path(target, guarded=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


async def promote_canonical(path: str, content: str, reason: str) -> str:
    """Write to canonical/ or summaries/ (guarded write zones).

    This is the **only** sanctioned way to persist curated knowledge.
    *path* is relative to the vault root.  *reason* is audit-logged.
    Returns a confirmation message.
    """
    target = _resolve_vault_path(path)
    validate_write_path(target, guarded=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    audit_write(target, action="promote_canonical", reason=reason)
    return f"Promoted {path} ({len(content)} chars). Reason: {reason}"


async def search_vault(query: str) -> str:
    """Full-text case-insensitive search across all ``.md`` files in the vault.

    Returns matching file paths (relative to vault root) with the first
    matching line as a snippet, one per file, up to 50 results.
    """
    query_lower = query.lower()
    results: list[str] = []
    vault_resolved = VAULT_PATH.resolve()

    for md_file in vault_resolved.rglob("*.md"):
        # Skip hidden directories (e.g. .audit, .obsidian).
        parts = md_file.relative_to(vault_resolved).parts
        if any(p.startswith(".") for p in parts):
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            if query_lower in line.lower():
                rel = md_file.relative_to(vault_resolved)
                snippet = line.strip()[:120]
                results.append(f"{rel}: {snippet}")
                break
        if len(results) >= 50:
            break

    if not results:
        return f"No results for '{query}'"
    return "\n".join(results)


async def list_vault(path: str = "") -> str:
    """List files and directories at a vault path.

    *path* is relative to the vault root (defaults to root).  Returns a
    newline-separated listing.
    """
    target = _resolve_vault_path(path) if path else VAULT_PATH.resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {path or '/'}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is a file, not a directory: {path}")

    entries: list[str] = []
    for child in sorted(target.iterdir()):
        if child.name.startswith("."):
            continue
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{child.name}{suffix}")
    return "\n".join(entries) if entries else "(empty directory)"
