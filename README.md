# Personal Health Agent

A local journaling agent with durable, inspectable memory. Telegram messages feed
a Claude Messages API tool loop; structured metrics live in SQLite and notes live
in a Markdown vault. A scheduler can request check-ins and summaries.

The useful boundary is in code: everyday notes go to scratch/logs/issues, while
canonical facts and summaries require a separate promotion tool and audit record.
This prototype is for tracking and organizing information, not diagnosis or care.

## Setup

Python 3.11+:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.template .env
```

For live use, set your own Anthropic key, Telegram bot token, and
`BRYAN_TELEGRAM_USER_ID`. The Telegram adapter refuses to start without an
explicit authorized user. Then run `python3 -m bryan.main`. Running it contacts
those services and can incur API usage. No keys, personal records, or model
conversations are bundled.

To configure a personal profile, point `BRYAN_PROFILE_PATH` at a local Markdown
file outside this repository. Vault and database paths are configurable with
`BRYAN_VAULT_PATH` and `BRYAN_DB_PATH`; defaults use
`~/.local/share/personal-health-agent`. Treat both as private data.

## Offline verification

```sh
python3 -m pytest -q
python3 -m compileall -q bryan
```

Tests create temporary synthetic records, check that a fresh database is empty,
verify guarded promotion/audit behavior, and reject writes outside the vault.
They do not call Telegram or an LLM.

## Layout

- `bryan/telegram/session_bridge.py`: bounded tool-use loop and conversation state
- `bryan/mcp_server/`: local note, metric, and issue tools with write policy
- `bryan/db/`: schema, validation models, trend queries
- `bryan/scheduler/`: proactive jobs
- `bryan/agent/system_prompt.md`: generic agent instructions

## Limits

Conversation history is in memory and resets on restart. Photo handling currently
passes the caption to the agent, not the image. The vault is plaintext local
storage, not encrypted. The optional stdio MCP server assumes a trusted local
caller. This is a single-user prototype, not a clinical system or a multi-user
service. Review generated interpretations rather than treating them as facts.

MIT licensed. This public code edition has no original private history or data.
