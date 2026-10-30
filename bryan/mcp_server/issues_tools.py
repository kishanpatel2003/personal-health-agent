"""Issue tracker tools for the Bryan MCP server.

Issues live as ``.md`` files in ``vault/issues/`` with YAML frontmatter.
Each function is a plain ``async`` callable registered as an MCP tool.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from bryan.config import ISSUES_PATH, VAULT_PATH
from bryan.mcp_server.policy import audit_write, validate_write_path

# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML-frontmatter parser (flat key: value only)."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _rebuild_frontmatter(fm: dict[str, str]) -> str:
    """Serialize a flat dict back to YAML frontmatter."""
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _resolve_issue_path(relative: str) -> Path:
    """Return an absolute path inside issues/, ensuring it stays in vault."""
    resolved = (VAULT_PATH / relative).resolve()
    vault_resolved = VAULT_PATH.resolve()
    if vault_resolved not in resolved.parents and resolved != vault_resolved:
        raise PermissionError(f"Path {resolved} escapes vault root ({vault_resolved})")
    return resolved


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def get_open_issues() -> str:
    """Scan ``issues/`` and return all issues whose status is not "resolved".

    Returns a newline-separated list of issue summaries including file name,
    severity, status, and first_seen date.
    """
    issues_dir = ISSUES_PATH.resolve()
    if not issues_dir.exists():
        return "No issues directory found."

    results: list[str] = []
    for md in sorted(issues_dir.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _parse_frontmatter(text)
        if fm.get("status", "").lower() == "resolved":
            continue
        rel = md.relative_to(VAULT_PATH.resolve())
        severity = fm.get("severity", "unknown")
        status = fm.get("status", "unknown")
        first_seen = fm.get("first_seen", "?")
        results.append(f"{rel} | severity={severity} status={status} first_seen={first_seen}")

    return "\n".join(results) if results else "No open issues."


async def create_issue(
    name: str,
    severity: str,
    description: str,
    trigger: str = "",
) -> str:
    """Create a new issue file in ``issues/``.

    Parameters
    ----------
    name:
        Short descriptive name (used as filename slug).
    severity:
        One of: low, medium, high, critical.
    description:
        Markdown body describing the issue.
    trigger:
        Optional note on what triggered this issue.

    Returns confirmation with file path.
    """
    today = date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    filename = f"{today}-{slug}.md"
    target = ISSUES_PATH / filename

    validate_write_path(target, guarded=False)

    fm = {
        "first_seen": today,
        "last_seen": today,
        "severity": severity,
        "confidence": "low",
        "status": "open",
        "trigger": trigger or "manual",
        "recommended_next_step": "investigate",
    }

    content = _rebuild_frontmatter(fm) + "\n\n" + description.strip() + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    rel = target.relative_to(VAULT_PATH.resolve())
    audit_write(target, action="create_issue", reason=f"New issue: {name}")
    return f"Created issue {rel}"


async def update_issue(path: str, updates: str) -> str:
    """Update frontmatter fields on an existing issue.

    Parameters
    ----------
    path:
        Vault-relative path to the issue file (e.g. ``issues/2026-04-10-headache.md``).
    updates:
        JSON string of frontmatter fields to update (e.g.
        ``{"status": "resolved", "confidence": "high"}``).

    Returns confirmation with updated fields.
    """
    target = _resolve_issue_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Issue not found: {path}")

    try:
        changes: dict[str, str] = json.loads(updates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"updates is not valid JSON: {exc}") from exc

    text = target.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)

    # Strip existing frontmatter from body.
    m = _FM_RE.match(text)
    body = text[m.end():] if m else text

    fm.update({k: str(v) for k, v in changes.items()})
    fm["last_seen"] = date.today().isoformat()

    new_content = _rebuild_frontmatter(fm) + "\n" + body
    validate_write_path(target, guarded=False)
    target.write_text(new_content, encoding="utf-8")

    rel = target.relative_to(VAULT_PATH.resolve())
    audit_write(target, action="update_issue", reason=f"Updated fields: {list(changes.keys())}")
    return f"Updated {rel}: {list(changes.keys())}"
