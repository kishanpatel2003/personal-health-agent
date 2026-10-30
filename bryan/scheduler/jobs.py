"""APScheduler jobs for Bryan's proactive behaviors."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bryan.config import DB_PATH
from bryan.db.queries import get_adherence

logger = logging.getLogger(__name__)

# Will be set by main.py at startup
_send_telegram = None
_telegram_user_id: int | None = None


def configure(send_fn, user_id: int) -> None:
    """Set the Telegram send function and target user ID.

    Called once at startup by main.py after the bot is initialized.
    """
    global _send_telegram, _telegram_user_id
    _send_telegram = send_fn
    _telegram_user_id = user_id


async def _send(prompt: str) -> None:
    """Send a proactive message through Bryan to Telegram."""
    if not _send_telegram or not _telegram_user_id:
        logger.warning("Scheduler not configured — skipping proactive message")
        return

    from bryan.telegram.session_bridge import handle_proactive

    try:
        response = await handle_proactive(_telegram_user_id, prompt)
        await _send_telegram(_telegram_user_id, response)
    except Exception:
        logger.exception("Failed to send proactive message")


async def morning_checkin() -> None:
    """Daily 8am: morning check-in prompt."""
    today = date.today().isoformat()
    prompt = (
        f"It's {today}, morning check-in time. "
        "Read the user's recent canonical memory and open issues. "
        "Check the last few days of weight and nutrition data via query_trend. "
        "Send a brief, useful check-in: acknowledge recent progress or gaps, "
        "remind of any open issues, and give one actionable item for today. "
        "Keep it under 5 sentences."
    )
    await _send(prompt)


async def missing_log_reminder() -> None:
    """Daily 9pm: remind if no weight was logged today."""
    today = date.today().isoformat()
    result = await get_adherence(DB_PATH, today, today)

    if result["days_logged"] == 0:
        prompt = (
            f"the user hasn't logged weight today ({today}). "
            "Send a brief, friendly reminder to log weight before bed. "
            "One sentence, no lecture."
        )
        await _send(prompt)
    else:
        logger.info("Weight already logged for %s — skipping reminder", today)


async def weekly_review() -> None:
    """Sunday 6pm: generate weekly summary."""
    today = date.today()
    week_start = (today - timedelta(days=6)).isoformat()
    week_end = today.isoformat()

    prompt = (
        f"Generate a weekly health review for {week_start} to {week_end}. "
        "Steps:\n"
        "1. Query weight trend for the last 14 days via query_trend('weight', 14)\n"
        "2. Query nutrition data via query_trend('nutrition', 7)\n"
        "3. Check adherence via get_adherence for the week\n"
        "4. Check open issues via get_open_issues\n"
        "5. Read relevant canonical memory (baselines, constraints)\n"
        "6. Write a weekly summary to summaries/weekly/{week_end}.md via promote_canonical. "
        "Include: adherence score, trend summary, wins, misses, risks, proposed adjustments.\n"
        "7. Send the summary to the user via your response (keep it concise, "
        "highlight the 2-3 most important takeaways)."
    )
    await _send(prompt)


async def stale_issue_followup() -> None:
    """Wednesday + Saturday: check for stale unresolved issues."""
    prompt = (
        "Check open issues via get_open_issues. "
        "For any issue with last_seen > 5 days ago, ask the user for an update. "
        "For any issue with severity=high, remind the user it's still open. "
        "If there are no open issues or none are stale, do nothing — "
        "respond with just 'No stale issues to follow up on.'"
    )
    response = None
    from bryan.telegram.session_bridge import handle_proactive

    try:
        client_response = await handle_proactive(_telegram_user_id or 0, prompt)
        if "no stale issues" not in client_response.lower():
            if _send_telegram and _telegram_user_id:
                await _send_telegram(_telegram_user_id, client_response)
    except Exception:
        logger.exception("Failed stale issue followup")


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler with all Bryan jobs."""
    scheduler = AsyncIOScheduler()

    # Daily 8am morning check-in
    scheduler.add_job(
        morning_checkin,
        CronTrigger(hour=8, minute=0),
        id="morning_checkin",
        name="Morning check-in",
        replace_existing=True,
    )

    # Daily 9pm missing-log reminder
    scheduler.add_job(
        missing_log_reminder,
        CronTrigger(hour=21, minute=0),
        id="missing_log_reminder",
        name="Missing log reminder",
        replace_existing=True,
    )

    # Sunday 6pm weekly review
    scheduler.add_job(
        weekly_review,
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="weekly_review",
        name="Weekly review",
        replace_existing=True,
    )

    # Wednesday + Saturday 10am stale issue followup
    scheduler.add_job(
        stale_issue_followup,
        CronTrigger(day_of_week="wed,sat", hour=10, minute=0),
        id="stale_issue_followup",
        name="Stale issue followup",
        replace_existing=True,
    )

    return scheduler
