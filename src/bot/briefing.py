"""Brief generation and delivery logic."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from src.db.models import ChatSettings
from src.db.database import db

logger = logging.getLogger(__name__)


async def generate_brief(chat_settings: ChatSettings) -> str:
    """Generate brief content for a chat.

    Args:
        chat_settings: ChatSettings object with user preferences

    Returns:
        Formatted brief content string

    Note:
        This is a placeholder implementation. In production, you would:
        - Fetch news from APIs based on topics
        - Generate AI summaries of chat messages
        - Pull data from RSS feeds
        - Aggregate information from multiple sources
    """
    timezone = chat_settings.timezone
    topics = chat_settings.get_topics()

    # Get current time in user's timezone
    tz = ZoneInfo(timezone)
    current_time = datetime.now(tz)

    # Format brief content
    brief_parts = [
        f"📅 {current_time.strftime('%A, %B %d, %Y')}",
        f"🕐 {current_time.strftime('%I:%M %p %Z')}",
        "",
        "📰 Your Daily Brief",
        "─" * 30,
    ]

    # Add topic-based sections
    if topics:
        brief_parts.append("\n📌 Topics:")
        for topic in topics:
            brief_parts.append(f"  • {topic.upper()}")
            # TODO: Fetch actual content for each topic
            brief_parts.append(f"    - Placeholder content for {topic}")
        brief_parts.append("")
    else:
        brief_parts.append("\n💡 No topics configured yet!")
        brief_parts.append("Use /settings to add topics.\n")

    # Add footer
    brief_parts.extend(
        [
            "─" * 30,
            "",
            "💬 Commands:",
            "  /settings - Update preferences",
            "  /status - View configuration",
            "  /test - Test brief delivery",
        ]
    )

    return "\n".join(brief_parts)


async def send_scheduled_brief(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send scheduled brief to a chat (called by job queue).

    Args:
        context: Telegram context from job callback
    """
    job = context.job
    chat_id = job.data.get("chat_id")
    timezone = job.data.get("timezone", "UTC")

    logger.info(f"Sending scheduled brief to chat_id={chat_id}, timezone={timezone}")

    try:
        # Get chat settings from database
        session = db.get_sync_session()
        try:
            chat_settings = (
                session.query(ChatSettings).filter_by(chat_id=chat_id).first()
            )

            if not chat_settings or not chat_settings.active:
                logger.warning(f"Chat {chat_id} not found or inactive, skipping brief")
                return

            # Generate brief content
            brief_content = await generate_brief(chat_settings)

            # Send to chat
            await context.bot.send_message(
                chat_id=chat_id,
                text=brief_content,
                parse_mode=None,  # Plain text for now
            )

            logger.info(f"Successfully sent brief to chat {chat_id}")

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error sending brief to chat {chat_id}: {e}", exc_info=True)


async def send_test_brief(chat_id: int, bot) -> str:
    """Send a test brief immediately.

    Args:
        chat_id: Target chat ID
        bot: Telegram Bot instance

    Returns:
        Brief content that was sent
    """
    session = db.get_sync_session()
    try:
        chat_settings = session.query(ChatSettings).filter_by(chat_id=chat_id).first()

        if not chat_settings:
            return "No settings found. Use /start to initialize."

        brief_content = await generate_brief(chat_settings)
        return brief_content

    finally:
        session.close()
