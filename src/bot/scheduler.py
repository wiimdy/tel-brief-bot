"""APScheduler integration for timezone-aware brief scheduling."""

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application
from sqlalchemy.orm import Session

from src.db.database import db
from src.db.models import ChatSettings
from src.bot.briefing import send_scheduled_brief

logger = logging.getLogger(__name__)


async def schedule_all_chats(application: Application) -> None:
    """Schedule briefing jobs for all active chats.

    Args:
        application: Telegram Application instance
    """
    logger.info("Scheduling briefing jobs for all active chats...")

    session: Session = db.get_sync_session()
    try:
        # Get all active chat settings
        active_chats = session.query(ChatSettings).filter_by(active=True).all()

        for chat_settings in active_chats:
            await schedule_chat(application, chat_settings)

        logger.info(f"Scheduled briefing jobs for {len(active_chats)} chats")

    finally:
        session.close()


async def schedule_chat(application: Application, chat_settings: ChatSettings) -> None:
    """Schedule briefing jobs for a single chat.

    Args:
        application: Telegram Application instance
        chat_settings: ChatSettings object with timezone and brief times
    """
    chat_id = chat_settings.chat_id
    timezone = chat_settings.timezone
    brief_times = chat_settings.get_brief_times()

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
            brief_time = time(hour=int(hour), minute=int(minute))

            # Schedule daily job in user's timezone
            application.job_queue.run_daily(
                callback=send_scheduled_brief,
                time=brief_time,
                days=(0, 1, 2, 3, 4, 5, 6),  # All days
                chat_id=chat_id,
                name=f"brief_{chat_id}_{brief_time_str}",
                data={"chat_id": chat_id, "timezone": timezone},
                job_kwargs={"timezone": tz},
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
    session: Session = db.get_sync_session()
    try:
        chat_settings = session.query(ChatSettings).filter_by(chat_id=chat_id).first()

        if chat_settings and chat_settings.active:
            await schedule_chat(application, chat_settings)
            logger.info(f"Rescheduled chat {chat_id}")
        else:
            # Remove all jobs if chat is inactive
            current_jobs = application.job_queue.get_jobs_by_name(f"brief_{chat_id}")
            for job in current_jobs:
                job.schedule_removal()
            logger.info(f"Removed jobs for inactive chat {chat_id}")

    finally:
        session.close()


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
