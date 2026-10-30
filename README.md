# Personal Health Agent

A Telegram-based health journal with durable memory, SQLite metrics, and a Markdown vault. A Claude tool-use loop reads and updates records, while a scheduler handles check-ins and summaries.

Everyday notes go to scratch, logs, and issues. Changes to canonical facts and summaries require a promotion tool and an audit record.

## Setup

Python 3.11+:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.template .env
```

Set `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `BRYAN_TELEGRAM_USER_ID`, then run:

```sh
python3 -m bryan.main
```

Telegram access is restricted to the configured user. Model requests use your Anthropic account.

Point `BRYAN_PROFILE_PATH` at a local Markdown profile. `BRYAN_VAULT_PATH` and `BRYAN_DB_PATH` configure storage; the defaults use `~/.local/share/personal-health-agent`.

## Design

- `bryan/telegram/session_bridge.py`: bounded tool-use loop and conversation state
- `bryan/mcp_server/`: note, metric, and issue tools with enforced write policy
- `bryan/db/`: schema, validation models, and trend queries
- `bryan/scheduler/`: proactive jobs
- `bryan/agent/system_prompt.md`: agent instructions

## Tests

```sh
python3 -m pytest -q
python3 -m compileall -q bryan
```

Tests use temporary records to check empty database initialization, guarded promotion, audit logging, and vault path restrictions. Telegram and model calls are mocked.

## Storage and behavior

The agent runs for one user on a trusted local machine. The vault is plaintext storage. Conversation history resets on restart, and photo messages currently pass their captions to the model. The optional stdio MCP server expects a trusted local caller.

[MIT](LICENSE)
