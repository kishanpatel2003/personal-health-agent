"""Bridge between Telegram messages and Claude via Messages API with local tool execution.

Uses the Messages API with tool_use instead of Managed Agents sessions,
because Bryan's tools (vault read/write, SQLite) run locally on the local host.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import anthropic

from bryan.config import ANTHROPIC_API_KEY, DEFAULT_MODEL, PROFILE_PATH

logger = logging.getLogger(__name__)

# Conversation history per user (in-memory for v0.5)
_conversations: dict[int, list[dict]] = {}

# System prompt loaded once
_system_prompt: str | None = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        prompt_path = Path(__file__).parent.parent / "agent" / "system_prompt.md"
        _system_prompt = prompt_path.read_text(encoding="utf-8")
        if PROFILE_PATH is not None:
            _system_prompt += "\n\n## Local subject profile\n" + PROFILE_PATH.read_text(encoding="utf-8")
        # Append skills
        skills_dir = Path(__file__).parent.parent / "skills"
        for skill_file in sorted(skills_dir.glob("*.md")):
            _system_prompt += f"\n\n---\n\n{skill_file.read_text(encoding='utf-8')}"
    return _system_prompt


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


# Tool definitions for the Messages API
TOOLS = [
    {
        "name": "read_note",
        "description": "Read a markdown note from the vault. path is relative to vault root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Vault-relative path (e.g. 'canonical/profile/baselines.md')"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_scratch",
        "description": "Write to scratch/ or logs/ (unrestricted zones). For drafts, daily logs, working notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Vault-relative path starting with scratch/ or logs/"},
                "content": {"type": "string", "description": "Full text content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "promote_canonical",
        "description": "Write to canonical/ or summaries/ (guarded zones). The ONLY way to persist finalized knowledge. Requires a reason.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Vault-relative path starting with canonical/ or summaries/"},
                "content": {"type": "string", "description": "Finalized markdown content"},
                "reason": {"type": "string", "description": "Why this is being promoted (audit-logged)"},
            },
            "required": ["path", "content", "reason"],
        },
    },
    {
        "name": "search_vault",
        "description": "Full-text search across all .md files in the vault. Returns matching paths with snippets.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search string (case-insensitive)"}},
            "required": ["query"],
        },
    },
    {
        "name": "list_vault",
        "description": "List files and directories at a vault path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Vault-relative directory path (default: root)", "default": ""}},
        },
    },
    {
        "name": "append_metric",
        "description": "Record a health metric. Inserts into SQLite. Use for weight, nutrition, workout, symptom, supplement, sleep, body_comp.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["weight", "nutrition", "workout", "symptom", "supplement", "sleep", "body_comp"]},
                "date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
                "data": {"type": "string", "description": "JSON string with metric fields (e.g. {\"weight\": 178.2})"},
            },
            "required": ["kind", "date", "data"],
        },
    },
    {
        "name": "query_trend",
        "description": "Query recent trend data for a health metric from SQLite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": ["weight", "nutrition", "workout", "symptom", "supplement", "sleep", "body_comp"]},
                "days": {"type": "integer", "description": "Days to look back (default 14)", "default": 14},
            },
            "required": ["metric"],
        },
    },
    {
        "name": "get_adherence",
        "description": "Return weight-logging adherence rate for a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End (YYYY-MM-DD)"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_open_issues",
        "description": "List all open health issues from the issue tracker.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_issue",
        "description": "Create a new health issue to track. Creates a .md file in issues/ with frontmatter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short descriptive name"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "description": {"type": "string", "description": "Markdown body describing the issue"},
                "trigger": {"type": "string", "description": "What triggered this issue", "default": ""},
            },
            "required": ["name", "severity", "description"],
        },
    },
    {
        "name": "update_issue",
        "description": "Update frontmatter on an existing issue (e.g. status, severity, confidence).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Vault-relative path to issue file"},
                "updates": {"type": "string", "description": "JSON string of fields to update"},
            },
            "required": ["path", "updates"],
        },
    },
]


async def _execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool call locally and return the result string."""
    import asyncio

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

    tool_map = {
        "read_note": lambda d: read_note(d["path"]),
        "write_scratch": lambda d: write_scratch(d["path"], d["content"]),
        "promote_canonical": lambda d: promote_canonical(d["path"], d["content"], d["reason"]),
        "search_vault": lambda d: search_vault(d["query"]),
        "list_vault": lambda d: list_vault(d.get("path", "")),
        "append_metric": lambda d: append_metric(d["kind"], d["date"], d["data"]),
        "query_trend": lambda d: query_trend(d["metric"], d.get("days", 14)),
        "get_adherence": lambda d: get_adherence(d["start_date"], d["end_date"]),
        "get_open_issues": lambda d: get_open_issues(),
        "create_issue": lambda d: create_issue(d["name"], d["severity"], d["description"], d.get("trigger", "")),
        "update_issue": lambda d: update_issue(d["path"], d["updates"]),
    }

    if name not in tool_map:
        return f"Unknown tool: {name}"

    try:
        result = await tool_map[name](input_data)
        return result
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return f"Error: {e}"


async def handle_message(telegram_user_id: int, text: str) -> str:
    """Send a message to Bryan via Messages API with tool use loop."""
    client = _get_client()
    system = _get_system_prompt()

    # Get or init conversation history
    if telegram_user_id not in _conversations:
        _conversations[telegram_user_id] = []

    messages = _conversations[telegram_user_id]
    messages.append({"role": "user", "content": text})

    # Trim history to last 40 messages to stay under context limits
    if len(messages) > 40:
        messages = messages[-40:]
        _conversations[telegram_user_id] = messages

    # Agent loop: send message, execute tools, repeat until text response
    max_iterations = 10
    for _ in range(max_iterations):
        response = await client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=TOOLS,
        )

        # Collect assistant response content
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Check if we need to execute tools
        tool_uses = [b for b in assistant_content if b.type == "tool_use"]
        if not tool_uses:
            # No tool calls — extract text response
            text_parts = [b.text for b in assistant_content if b.type == "text"]
            return "\n".join(text_parts) if text_parts else "(No response from Bryan.)"

        # Execute all tool calls and collect results
        tool_results = []
        for tool_use in tool_uses:
            logger.info("Tool call: %s", tool_use.name)
            result = await _execute_tool(tool_use.name, tool_use.input)
            logger.debug("Tool completed: %s", tool_use.name)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return "(Bryan hit the iteration limit. Try a simpler request.)"


async def handle_proactive(telegram_user_id: int, prompt: str) -> str:
    """Handle a proactive message (from scheduler). Fresh conversation."""
    client = _get_client()
    system = _get_system_prompt()

    messages = [{"role": "user", "content": prompt}]

    max_iterations = 15  # proactive jobs may need more tool calls
    for _ in range(max_iterations):
        response = await client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=TOOLS,
        )

        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        tool_uses = [b for b in assistant_content if b.type == "tool_use"]
        if not tool_uses:
            text_parts = [b.text for b in assistant_content if b.type == "text"]
            return "\n".join(text_parts) if text_parts else "(No response.)"

        tool_results = []
        for tool_use in tool_uses:
            logger.info("Proactive tool call: %s", tool_use.name)
            result = await _execute_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return "(Proactive job hit iteration limit.)"
