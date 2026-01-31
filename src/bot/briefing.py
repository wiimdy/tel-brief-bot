"""Brief generation and delivery logic with AI summarization."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from src.db.models import ChatSettings
from src.db.database import db
from src.config import Config

logger = logging.getLogger(__name__)


async def generate_brief(chat_settings: ChatSettings) -> str:
    """Generate brief content for a chat.

    Args:
        chat_settings: ChatSettings object with user preferences

    Returns:
        Formatted brief content string
    """
    timezone = chat_settings.timezone
    topics = chat_settings.get_topics()

    # Get current time in user's timezone
    tz = ZoneInfo(timezone)
    current_time = datetime.now(tz)

    # Check if message collection is enabled
    if Config.ENABLE_MESSAGE_COLLECTION and chat_settings.added_by_user_id:
        # Use AI-powered brief generation
        return await generate_ai_brief(chat_settings, current_time)

    # Fallback to basic brief (placeholder)
    return await generate_basic_brief(chat_settings, current_time)


async def generate_ai_brief(chat_settings: ChatSettings, current_time: datetime) -> str:
    """Generate AI-powered brief with message analysis.

    Args:
        chat_settings: ChatSettings object
        current_time: Current time in user's timezone

    Returns:
        AI-generated brief content
    """
    from src.ai.analyzer import get_message_analyzer

    user_id = chat_settings.added_by_user_id
    topics = chat_settings.get_topics()
    timezone = chat_settings.timezone

    if not user_id:
        return "Error: No user ID associated with this chat."

    try:
        analyzer = get_message_analyzer()
        brief_content = await analyzer.generate_brief_content(
            user_id=user_id, topics=topics, timezone=timezone
        )
        return brief_content

    except Exception as e:
        logger.error(f"Error generating AI brief: {e}", exc_info=True)
        # Fallback to basic brief on error
        return await generate_basic_brief(chat_settings, current_time)


async def generate_basic_brief(
    chat_settings: ChatSettings, current_time: datetime
) -> str:
    """Generate basic brief without AI (fallback/placeholder).

    Args:
        chat_settings: ChatSettings object
        current_time: Current time in user's timezone

    Returns:
        Basic brief content
    """
    topics = chat_settings.get_topics()

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
        brief_parts.append("\n📌 Your Topics:")
        for topic in topics:
            brief_parts.append(f"  • {topic}")
        brief_parts.append("")

        if not Config.ENABLE_MESSAGE_COLLECTION:
            brief_parts.append("💡 Message collection is disabled.")
            brief_parts.append(
                "Set ENABLE_MESSAGE_COLLECTION=true in .env to enable AI briefs."
            )
            brief_parts.append("")
    else:
        brief_parts.append("\n💡 No topics configured yet!")
        brief_parts.append("Use /topics to add topics like: web3, ai, security")
        brief_parts.append("")

    # Add footer
    brief_parts.extend(
        [
            "─" * 30,
            "",
            "💬 Commands:",
            "  /topics - Set interest topics",
            "  /listchats - View monitored chats",
            "  /status - View configuration",
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


async def send_brief_to_recipient(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send aggregated brief to the configured recipient (called by job queue).

    This sends a combined brief from all monitored chats to the BRIEF_RECIPIENT_ID.

    Args:
        context: Telegram context from job callback
    """
    recipient_id = Config.BRIEF_RECIPIENT_ID

    if not recipient_id:
        logger.warning("No BRIEF_RECIPIENT_ID configured, skipping brief")
        return

    logger.info(f"Sending aggregated brief to recipient {recipient_id}")

    try:
        from src.ai.analyzer import get_message_analyzer

        analyzer = get_message_analyzer()

        # Get topics from any of user's chats
        session = db.get_sync_session()
        try:
            chat = (
                session.query(ChatSettings)
                .filter_by(added_by_user_id=recipient_id, active=True)
                .first()
            )

            topics = chat.get_topics() if chat else []
            timezone = chat.timezone if chat else "UTC"

        finally:
            session.close()

        # Generate AI brief
        brief_content = await analyzer.generate_brief_content(
            user_id=recipient_id, topics=topics, timezone=timezone
        )

        # Send to recipient
        await context.bot.send_message(
            chat_id=recipient_id,
            text=brief_content,
            parse_mode=None,
        )

        logger.info(f"Successfully sent aggregated brief to {recipient_id}")

    except Exception as e:
        logger.error(
            f"Error sending brief to recipient {recipient_id}: {e}", exc_info=True
        )


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
