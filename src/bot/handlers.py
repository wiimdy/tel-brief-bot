"""Telegram bot command handlers."""

import logging
from datetime import time
from typing import List

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from src.db.database import db
from src.db.models import ChatSettings
from src.config import Config

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - Initialize bot for chat."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    logger.info(f"Start command from chat_id={chat_id}, user={user.username}")

    # Check if chat already exists in database
    session: Session = db.get_sync_session()
    try:
        chat_settings = session.query(ChatSettings).filter_by(chat_id=chat_id).first()

        if not chat_settings:
            # Create new chat settings
            chat_settings = ChatSettings(
                chat_id=chat_id,
                timezone=Config.DEFAULT_TIMEZONE,
                brief_times='["09:00", "18:00"]',
                topics="[]",
                active=True,
            )
            session.add(chat_settings)
            session.commit()

            message = (
                "👋 Welcome to Telegram Brief Bot!\n\n"
                f"Default settings:\n"
                f"⏰ Brief times: 09:00, 18:00\n"
                f"🌍 Timezone: {Config.DEFAULT_TIMEZONE}\n\n"
                "Commands:\n"
                "/settings - Configure your settings\n"
                "/status - View current configuration\n"
                "/test - Send test brief immediately"
            )
        else:
            message = (
                "👋 Welcome back!\n\n"
                "Commands:\n"
                "/settings - Configure your settings\n"
                "/status - View current configuration\n"
                "/test - Send test brief immediately"
            )

        await update.message.reply_text(message)

    finally:
        session.close()


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command - Configure timezone, brief times, topics.

    Usage: /settings timezone=<tz> times=<HH:MM,HH:MM> topics=<topic1,topic2>
    Example: /settings timezone=Asia/Seoul times=15:00,21:00 topics=tech,news
    """
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        # Show current settings and usage
        session: Session = db.get_sync_session()
        try:
            chat_settings = (
                session.query(ChatSettings).filter_by(chat_id=chat_id).first()
            )

            if chat_settings:
                brief_times = chat_settings.get_brief_times()
                topics = chat_settings.get_topics()

                message = (
                    "⚙️ Current Settings:\n\n"
                    f"🌍 Timezone: {chat_settings.timezone}\n"
                    f"⏰ Brief times: {', '.join(brief_times)}\n"
                    f"📌 Topics: {', '.join(topics) if topics else 'None'}\n"
                    f"✅ Active: {'Yes' if chat_settings.active else 'No'}\n\n"
                    "Usage:\n"
                    "/settings timezone=<tz> times=<HH:MM,HH:MM> topics=<topic1,topic2>\n\n"
                    "Example:\n"
                    "/settings timezone=Asia/Seoul times=15:00,21:00 topics=tech,news"
                )
            else:
                message = "No settings found. Use /start to initialize."

            await update.message.reply_text(message)
        finally:
            session.close()
        return

    # Parse settings from arguments
    settings_update = {}

    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)

            if key == "timezone":
                settings_update["timezone"] = value
            elif key == "times":
                # Parse comma-separated times
                times = [t.strip() for t in value.split(",")]
                # Validate time format
                for t in times:
                    try:
                        hour, minute = t.split(":")
                        int(hour), int(minute)
                    except:
                        await update.message.reply_text(
                            f"Invalid time format: {t}. Use HH:MM"
                        )
                        return
                settings_update["brief_times"] = times
            elif key == "topics":
                # Parse comma-separated topics
                topics = [t.strip() for t in value.split(",")]
                settings_update["topics"] = topics

    if not settings_update:
        await update.message.reply_text("No valid settings provided.")
        return

    # Update database
    session: Session = db.get_sync_session()
    try:
        chat_settings = session.query(ChatSettings).filter_by(chat_id=chat_id).first()

        if not chat_settings:
            await update.message.reply_text(
                "No settings found. Use /start to initialize."
            )
            return

        # Apply updates
        if "timezone" in settings_update:
            chat_settings.timezone = settings_update["timezone"]
        if "brief_times" in settings_update:
            chat_settings.set_brief_times(settings_update["brief_times"])
        if "topics" in settings_update:
            chat_settings.set_topics(settings_update["topics"])

        session.commit()

        # Reschedule jobs (will be implemented in scheduler.py)
        from src.bot.scheduler import reschedule_chat

        await reschedule_chat(context.application, chat_id)

        await update.message.reply_text(
            "✅ Settings updated successfully!\n\n"
            "Use /status to view current configuration."
        )

    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        await update.message.reply_text(f"❌ Error updating settings: {str(e)}")

    finally:
        session.close()


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - Show current configuration."""
    chat_id = update.effective_chat.id

    session: Session = db.get_sync_session()
    try:
        chat_settings = session.query(ChatSettings).filter_by(chat_id=chat_id).first()

        if not chat_settings:
            await update.message.reply_text(
                "No settings found. Use /start to initialize."
            )
            return

        brief_times = chat_settings.get_brief_times()
        topics = chat_settings.get_topics()

        message = (
            "📊 Current Status:\n\n"
            f"🌍 Timezone: {chat_settings.timezone}\n"
            f"⏰ Brief times: {', '.join(brief_times)}\n"
            f"📌 Topics: {', '.join(topics) if topics else 'None'}\n"
            f"✅ Active: {'Yes' if chat_settings.active else 'No'}\n"
            f"📅 Created: {chat_settings.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"🔄 Updated: {chat_settings.updated_at.strftime('%Y-%m-%d %H:%M')}"
        )

        await update.message.reply_text(message)

    finally:
        session.close()


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test command - Send test brief immediately."""
    chat_id = update.effective_chat.id

    logger.info(f"Test command from chat_id={chat_id}")

    # Generate and send test brief
    from src.bot.briefing import generate_brief

    session: Session = db.get_sync_session()
    try:
        chat_settings = session.query(ChatSettings).filter_by(chat_id=chat_id).first()

        if not chat_settings:
            await update.message.reply_text(
                "No settings found. Use /start to initialize."
            )
            return

        brief_content = await generate_brief(chat_settings)

        await update.message.reply_text(
            f"🧪 Test Brief ({chat_settings.timezone}):\n\n{brief_content}"
        )

    finally:
        session.close()
