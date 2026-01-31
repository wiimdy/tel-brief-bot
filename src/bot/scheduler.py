"""APScheduler integration for timezone-aware brief scheduling using Supabase."""

import logging
from datetime import time
from typing import Dict, Any
from zoneinfo import ZoneInfo

from telegram.ext import Application

from src.db.supabase_client import get_supabase
from src.bot.briefing import send_scheduled_brief

logger = logging.getLogger(__name__)


async def schedule_all_chats(application: Application) -> None:
    """Schedule briefing jobs for all active chats.

    Args:
        application: Telegram Application instance
    """
    logger.info("Scheduling briefing jobs for all active chats...")

    db = get_supabase()
    active_chats = db.get_all_active_chats()

    for chat_settings in active_chats:
        await schedule_chat(application, chat_settings)

    logger.info(f"Scheduled briefing jobs for {len(active_chats)} chats")


async def schedule_chat(
    application: Application, chat_settings: Dict[str, Any]
) -> None:
    """Schedule briefing jobs for a single chat.

    Args:
        application: Telegram Application instance
        chat_settings: Chat settings dictionary from Supabase
    """
    chat_id = chat_settings.get("chat_id")
    timezone = chat_settings.get("timezone", "UTC")
    brief_times = chat_settings.get("brief_times", ["09:00", "18:00"])

    if not chat_id:
        logger.error("No chat_id in chat_settings")
        return

    logger.info(
        f"Scheduling chat_id={chat_id}, timezone={timezone}, times={brief_times}"
    )

    try:
        tz = ZoneInfo(timezone)
    except Exception as e:
        logger.error(f"Invalid timezone '{timezone}' for chat {chat_id}: {e}")
        return

    # Remove existing jobs for this chat
    current_jobs = application.job_queue.get_jobs_by_name(f"brief_{chat_id}")
    for job in current_jobs:
        job.schedule_removal()
        logger.debug(f"Removed existing job for chat {chat_id}")

    # Schedule new jobs for each brief time
    for brief_time_str in brief_times:
        try:
            # Parse time string (HH:MM format)
            hour, minute = brief_time_str.split(":")
            # Create time object with timezone info
            brief_time = time(hour=int(hour), minute=int(minute), tzinfo=tz)

            # Schedule daily job in user's timezone
            application.job_queue.run_daily(
                callback=send_scheduled_brief,
                time=brief_time,
                days=(0, 1, 2, 3, 4, 5, 6),  # All days
                chat_id=chat_id,
                name=f"brief_{chat_id}_{brief_time_str}",
                data={"chat_id": chat_id, "timezone": timezone},
            )

            logger.info(
                f"Scheduled brief for chat {chat_id} at {brief_time_str} {timezone}"
            )

        except Exception as e:
            logger.error(
                f"Error scheduling brief time '{brief_time_str}' "
                f"for chat {chat_id}: {e}"
            )


async def reschedule_chat(application: Application, chat_id: int) -> None:
    """Reschedule jobs for a chat (after settings update).

    Args:
        application: Telegram Application instance
        chat_id: Chat ID to reschedule
    """
    db = get_supabase()
    chat_settings = db.get_chat_settings(chat_id)

    if chat_settings and chat_settings.get("active"):
        await schedule_chat(application, chat_settings)
        logger.info(f"Rescheduled chat {chat_id}")
    else:
        # Remove all jobs if chat is inactive
        current_jobs = application.job_queue.get_jobs_by_name(f"brief_{chat_id}")
        for job in current_jobs:
            job.schedule_removal()
        logger.info(f"Removed jobs for inactive chat {chat_id}")


async def unschedule_chat(application: Application, chat_id: int) -> None:
    """Remove all scheduled jobs for a chat.

    Args:
        application: Telegram Application instance
        chat_id: Chat ID to unschedule
    """
    current_jobs = application.job_queue.get_jobs_by_name(f"brief_{chat_id}")

    for job in current_jobs:
        job.schedule_removal()

    logger.info(f"Unscheduled all jobs for chat {chat_id}")
