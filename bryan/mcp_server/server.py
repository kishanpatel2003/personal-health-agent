"""Bryan MCP server entry point.

Registers all vault, metrics, and issue-tracker tools and runs the server
over stdio transport using FastMCP.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bryan.mcp_server.vault_tools import (
    list_vault,
    promote_canonical,
    read_note,
    search_vault,
    write_scratch,
)
from bryan.mcp_server.metrics_tools import (
    append_metric,
    get_adherence,
    query_trend,
)
from bryan.mcp_server.issues_tools import (
    create_issue,
    get_open_issues,
    update_issue,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "bryan-health",
    instructions=(
        "Bryan's health-performance data layer. "
        "Use these tools to read/write the Obsidian vault, record metrics, "
        "query trends, and manage health issues."
    ),
)

# ---------------------------------------------------------------------------
# Vault tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="read_note",
    description=(
        "Read a markdown note from the vault. "
        "Use this to review canonical docs, scratch notes, summaries, or any .md file."
    ),
)
async def _read_note(path: str) -> str:
    """path: vault-relative path to the markdown file (e.g. 'canonical/protocol.md')."""
    return await read_note(path)


@mcp.tool(
    name="write_scratch",
    description=(
        "Write a file to scratch/ or logs/ (unrestricted write zones). "
        "Use for drafts, intermediate analysis, daily logs, and working notes."
    ),
)
async def _write_scratch(path: str, content: str) -> str:
    """path: vault-relative path starting with scratch/ or logs/.
    content: the full text content to write."""
    return await write_scratch(path, content)


@mcp.tool(
    name="promote_canonical",
    description=(
        "Write curated content to canonical/ or summaries/ (guarded write zones). "
        "This is the ONLY way to persist finalized knowledge. Requires a reason. "
        "Use when analysis is complete and a document should become part of the permanent record."
    ),
)
async def _promote_canonical(path: str, content: str, reason: str) -> str:
    """path: vault-relative path starting with canonical/ or summaries/.
    content: the finalized markdown content.
    reason: why this content is being promoted (audit-logged)."""
    return await promote_canonical(path, content, reason)


@mcp.tool(
    name="search_vault",
    description=(
        "Full-text case-insensitive search across all .md files in the vault. "
        "Returns matching file paths with a snippet of the first matching line. "
        "Use to find relevant notes, protocols, or past analyses."
    ),
)
async def _search_vault(query: str) -> str:
    """query: the search string to look for (case-insensitive)."""
    return await search_vault(query)


@mcp.tool(
    name="list_vault",
    description=(
        "List files and directories at a vault path. "
        "Use to explore vault structure or check what exists in a directory."
    ),
)
async def _list_vault(path: str = "") -> str:
    """path: vault-relative directory path (default: vault root)."""
    return await list_vault(path)


# ---------------------------------------------------------------------------
# Metrics tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="append_metric",
    description=(
        "Record a health metric data point. Inserts into the SQLite database. "
        "Use whenever Bryan receives new health data (weight, nutrition, workout, etc.)."
    ),
)
async def _append_metric(kind: str, date: str, data: str) -> str:
    """kind: metric type — one of weight, nutrition, workout, symptom, supplement, sleep, body_comp.
    date: ISO date (YYYY-MM-DD).
    data: JSON string with metric-specific fields."""
    return await append_metric(kind, date, data)


@mcp.tool(
    name="query_trend",
    description=(
        "Query recent trend data for a health metric. "
        "Returns formatted rows from the last N days. "
        "Use for trend analysis, weekly reviews, or answering questions about progress."
    ),
)
async def _query_trend(metric: str, days: int = 14) -> str:
    """metric: one of weight, nutrition, workout, symptom, supplement, sleep, body_comp.
    days: number of days to look back (default 14)."""
    return await query_trend(metric, days)


@mcp.tool(
    name="get_adherence",
    description=(
        "Return adherence rate for a date range. "
        "Shows what fraction of days have logged data. "
        "Use for accountability checks and weekly reviews."
    ),
)
async def _get_adherence(start_date: str, end_date: str) -> str:
    """start_date: range start (YYYY-MM-DD, inclusive).
    end_date: range end (YYYY-MM-DD, inclusive)."""
    return await get_adherence(start_date, end_date)


# ---------------------------------------------------------------------------
# Issue tracker tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="get_open_issues",
    description=(
        "List all open health issues. Scans issues/ directory for .md files "
        "whose status is not 'resolved'. Returns severity, status, and first-seen date."
    ),
)
async def _get_open_issues() -> str:
    return await get_open_issues()


@mcp.tool(
    name="create_issue",
    description=(
        "Create a new health issue tracker entry. "
        "Use when Bryan identifies a new symptom pattern, concern, or item to track. "
        "Creates a .md file in issues/ with structured frontmatter."
    ),
)
async def _create_issue(
    name: str,
    severity: str,
    description: str,
    trigger: str = "",
) -> str:
    """name: short descriptive name (becomes the filename slug).
    severity: one of low, medium, high, critical.
    description: markdown body describing the issue.
    trigger: what triggered this issue (optional)."""
    return await create_issue(name, severity, description, trigger)


@mcp.tool(
    name="update_issue",
    description=(
        "Update frontmatter fields on an existing issue. "
        "Use to change status (e.g. to 'resolved'), update severity, "
        "add confidence, or modify recommended_next_step."
    ),
)
async def _update_issue(path: str, updates: str) -> str:
    """path: vault-relative path to the issue file (e.g. 'issues/2026-04-10-headache.md').
    updates: JSON string of frontmatter fields to update."""
    return await update_issue(path, updates)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Bryan MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
