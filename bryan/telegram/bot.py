"""Telegram bot for Bryan health agent."""

from __future__ import annotations

import asyncio
import logging
import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bryan.config import TELEGRAM_BOT_TOKEN
from bryan.telegram.session_bridge import handle_message

logger = logging.getLogger(__name__)

# Max Telegram message length
_TG_MAX_LEN = 4096

# How often (seconds) to re-send the typing indicator before it expires
_TYPING_INTERVAL = 4.0


async def _keep_typing(chat) -> None:
    """Send 'typing...' action every few seconds until cancelled."""
    try:
        while True:
            await chat.send_action(ChatAction.TYPING)
            await asyncio.sleep(_TYPING_INTERVAL)
    except asyncio.CancelledError:
        pass


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "Bryan health agent is online. Send me health data — weight, meals, "
        "symptoms, workout notes, photos, whatever you've got."
    )


async def _handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text

    logger.info("Received text message")

    await update.message.chat.send_action(ChatAction.TYPING)
    typing_task = asyncio.create_task(_keep_typing(update.message.chat))
    try:
        response = await handle_message(user_id, text)
    except Exception:
        logger.exception("Error handling message from user %s", user_id)
        response = "Something went wrong processing that. Try again in a moment."
    finally:
        typing_task.cancel()

    # Split long responses for Telegram
    for i in range(0, len(response), _TG_MAX_LEN):
        await update.message.reply_text(response[i : i + _TG_MAX_LEN])


async def _handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos (progress pics, meal photos, etc.)."""
    if not update.message:
        return

    user_id = update.effective_user.id
    caption = update.message.caption or "Photo uploaded, no caption"

    # For v0.5: note the photo in scratch, don't process the image itself
    # Full image handling (Files API upload) comes in a later phase
    text = f"[Photo received] {caption}"

    logger.info("Received photo caption")

    await update.message.chat.send_action(ChatAction.TYPING)
    typing_task = asyncio.create_task(_keep_typing(update.message.chat))
    try:
        response = await handle_message(user_id, text)
    except Exception:
        logger.exception("Error handling photo from user %s", user_id)
        response = "Got the photo but had trouble processing it. Try sending just a text description for now."
    finally:
        typing_task.cancel()

    for i in range(0, len(response), _TG_MAX_LEN):
        await update.message.reply_text(response[i : i + _TG_MAX_LEN])


def create_app() -> Application:
    """Build and return the Telegram Application (not yet running)."""
    allowed_id = int(os.environ.get("BRYAN_TELEGRAM_USER_ID", "0"))
    if not allowed_id:
        raise RuntimeError("Set BRYAN_TELEGRAM_USER_ID to the single authorized user")
    allowed = filters.User(user_id=allowed_id)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", _start, filters=allowed))
    app.add_handler(MessageHandler(allowed & filters.TEXT & ~filters.COMMAND, _handle_text))
    app.add_handler(MessageHandler(allowed & filters.PHOTO, _handle_photo))

    return app


def main() -> None:
    """Run the Telegram bot (polling mode for v0.5)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("Starting Bryan Telegram bot (polling mode)")
    app = create_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
