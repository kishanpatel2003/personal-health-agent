"""Bryan agent — main entrypoint.

Starts the MCP server, Telegram bot, and scheduler in a single process.
"""

from __future__ import annotations

import asyncio
import logging
import os

from bryan.config import DB_PATH, TELEGRAM_BOT_TOKEN
from bryan.db.queries import init_db
from bryan.scheduler.jobs import configure, create_scheduler
from bryan.telegram.bot import create_app

logger = logging.getLogger(__name__)

# Configure the single authorized Telegram user via the environment
TELEGRAM_USER_ID = int(os.environ.get("BRYAN_TELEGRAM_USER_ID", "0"))


async def _send_telegram(user_id: int, text: str) -> None:
    """Send a message to a Telegram user via the bot."""
    from telegram import Bot

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    max_len = 4096
    for i in range(0, len(text), max_len):
        await bot.send_message(chat_id=user_id, text=text[i : i + max_len])


async def _run() -> None:
    # Init database (idempotent)
    logger.info("Initializing SQLite database at %s", DB_PATH)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    await init_db(DB_PATH)

    # Configure scheduler with Telegram send function
    if TELEGRAM_USER_ID:
        configure(_send_telegram, TELEGRAM_USER_ID)
        logger.info("Scheduler configured for Telegram user %s", TELEGRAM_USER_ID)
    else:
        logger.warning(
            "BRYAN_TELEGRAM_USER_ID not set — scheduler proactive messages disabled. "
            "Set it after your first /start interaction."
        )

    # Start scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))
    for job in scheduler.get_jobs():
        logger.info("  %s: %s", job.id, job.next_run_time)

    # Start Telegram bot (runs until interrupted)
    app = create_app()
    logger.info("Starting Telegram bot (polling mode)")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down...")
    finally:
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(_run())


if __name__ == "__main__":
    main()
