"""Telegram bot command handlers using Supabase."""

import logging
from datetime import datetime
from typing import List, Tuple, Optional

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from src.db.supabase_client import get_supabase
from src.config import Config

logger = logging.getLogger(__name__)


async def resolve_chat_identifier(
    chat_identifier: str, bot
) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """Resolve a chat identifier (username or ID) to a numeric chat_id.

    Args:
        chat_identifier: Either @username or numeric chat_id as string
        bot: Telegram Bot instance

    Returns:
        Tuple of (chat_id, chat_title, error_message)
        - On success: (chat_id, chat_title, None)
        - On failure: (None, None, error_message)
    """
    # Check if it's a username (starts with @)
    if chat_identifier.startswith("@"):
        try:
            chat = await bot.get_chat(chat_identifier)
            return chat.id, chat.title or chat.username, None
        except TelegramError as e:
            error_msg = str(e)
            if "chat not found" in error_msg.lower():
                return (
                    None,
                    None,
                    (
                        f"Chat '{chat_identifier}' not found.\n\n"
                        "Make sure:\n"
                        "- The username is correct\n"
                        "- The chat is public, OR\n"
                        "- The bot is a member of the chat"
                    ),
                )
            return None, None, f"Error resolving '{chat_identifier}': {error_msg}"

    # Try to parse as numeric ID
    try:
        chat_id = int(chat_identifier)
        # Optionally try to get chat info for the title
        try:
            chat = await bot.get_chat(chat_id)
            return chat_id, chat.title or str(chat_id), None
        except TelegramError:
            # Can't get chat info, but ID is valid - proceed anyway
            return chat_id, None, None
    except ValueError:
        return (
            None,
            None,
            (
                "Invalid chat identifier.\n\n"
                "Use either:\n"
                "- @username (e.g., @minchoisfuture)\n"
                "- Numeric ID (e.g., -123456789)"
            ),
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - Initialize bot for chat."""
    chat_id = update.effective_chat.id
    user = update.effective_user

    logger.info(f"Start command from chat_id={chat_id}, user={user.username}")

    db = get_supabase()
    chat_settings = db.get_chat_settings(chat_id)

    if not chat_settings:
        # Create new chat settings
        db.create_chat_settings(
            {
                "chat_id": chat_id,
                "added_by_user_id": user.id,
                "timezone": Config.DEFAULT_TIMEZONE,
                "brief_times": ["09:00", "18:00"],
                "topics": [],
                "active": True,
            }
        )

        message = (
            "Welcome to Telegram Brief Bot!\n\n"
            f"Default settings:\n"
            f"Brief times: 09:00, 18:00\n"
            f"Timezone: {Config.DEFAULT_TIMEZONE}\n\n"
            "Commands:\n"
            "/settings - Configure your settings\n"
            "/topics - Set interest topics\n"
            "/status - View current configuration\n"
            "/test - Send test brief immediately"
        )
    else:
        message = (
            "Welcome back!\n\n"
            "Commands:\n"
            "/settings - Configure your settings\n"
            "/topics - Set interest topics\n"
            "/status - View current configuration\n"
            "/test - Send test brief immediately"
        )

    await update.message.reply_text(message)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command - Configure timezone, brief times, topics.

    Usage: /settings timezone=<tz> times=<HH:MM,HH:MM> topics=<topic1,topic2>
    Example: /settings timezone=Asia/Seoul times=15:00,21:00 topics=tech,news
    """
    chat_id = update.effective_chat.id
    args = context.args

    db = get_supabase()
    chat_settings = db.get_chat_settings(chat_id)

    if not args:
        # Show current settings and usage
        if chat_settings:
            brief_times = chat_settings.get("brief_times", [])
            topics = chat_settings.get("topics", [])

            message = (
                "Current Settings:\n\n"
                f"Timezone: {chat_settings.get('timezone', 'UTC')}\n"
                f"Brief times: {', '.join(brief_times)}\n"
                f"Topics: {', '.join(topics) if topics else 'None'}\n"
                f"Active: {'Yes' if chat_settings.get('active') else 'No'}\n\n"
                "Usage:\n"
                "/settings timezone=<tz> times=<HH:MM,HH:MM> topics=<topic1,topic2>\n\n"
                "Example:\n"
                "/settings timezone=Asia/Seoul times=15:00,21:00 topics=tech,news"
            )
        else:
            message = "No settings found. Use /start to initialize."

        await update.message.reply_text(message)
        return

    if not chat_settings:
        await update.message.reply_text("No settings found. Use /start to initialize.")
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
    db.update_chat_settings(chat_id, settings_update)

    # Reschedule jobs
    from src.bot.scheduler import reschedule_chat

    await reschedule_chat(context.application, chat_id)

    await update.message.reply_text(
        "Settings updated successfully!\n\nUse /status to view current configuration."
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - Show current configuration."""
    chat_id = update.effective_chat.id

    db = get_supabase()
    chat_settings = db.get_chat_settings(chat_id)

    if not chat_settings:
        await update.message.reply_text("No settings found. Use /start to initialize.")
        return

    brief_times = chat_settings.get("brief_times", [])
    topics = chat_settings.get("topics", [])
    created_at = chat_settings.get("created_at", "")
    updated_at = chat_settings.get("updated_at", "")

    message = (
        "Current Status:\n\n"
        f"Timezone: {chat_settings.get('timezone', 'UTC')}\n"
        f"Brief times: {', '.join(brief_times)}\n"
        f"Topics: {', '.join(topics) if topics else 'None'}\n"
        f"Active: {'Yes' if chat_settings.get('active') else 'No'}\n"
        f"Created: {created_at[:19] if created_at else 'N/A'}\n"
        f"Updated: {updated_at[:19] if updated_at else 'N/A'}"
    )

    await update.message.reply_text(message)


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /test command - Send test brief immediately."""
    chat_id = update.effective_chat.id

    logger.info(f"Test command from chat_id={chat_id}")

    # Generate and send test brief
    from src.bot.briefing import generate_brief

    db = get_supabase()
    chat_settings = db.get_chat_settings(chat_id)

    if not chat_settings:
        await update.message.reply_text("No settings found. Use /start to initialize.")
        return

    brief_content = await generate_brief(chat_settings)

    await update.message.reply_text(
        f"Test Brief ({chat_settings.get('timezone', 'UTC')}):\n\n{brief_content}"
    )


async def addchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addchat command - Add a new chatroom by ID or username.

    Usage: /addchat <chat_id or @username>
    Examples: /addchat -123456789 or /addchat @minchoisfuture
    """
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 1:
        await update.message.reply_text(
            "Usage: /addchat <chat_id or @username>\n\n"
            "Examples:\n"
            "/addchat -123456789\n"
            "/addchat @minchoisfuture\n\n"
            "Tip: Use @username for public chats, or get chat_id from @userinfobot"
        )
        return

    # Resolve chat identifier (username or ID)
    target_chat_id, chat_title, error = await resolve_chat_identifier(
        args[0], context.bot
    )

    if error:
        await update.message.reply_text(error)
        return

    logger.info(f"Addchat command from user={user_id} for chat_id={target_chat_id}")

    db = get_supabase()
    existing = db.get_chat_settings(target_chat_id)

    chat_display = (
        f"{chat_title} ({target_chat_id})" if chat_title else str(target_chat_id)
    )

    if existing:
        if existing.get("active"):
            await update.message.reply_text(
                f"Chat {chat_display} is already registered.\n\n"
                "Use /editchat to modify settings or /listchats to see all chats."
            )
        else:
            # Reactivate if inactive
            db.update_chat_settings(
                target_chat_id, {"active": True, "added_by_user_id": user_id}
            )

            from src.bot.scheduler import reschedule_chat

            await reschedule_chat(context.application, target_chat_id)

            await update.message.reply_text(
                f"Chat {chat_display} has been reactivated!\n\n"
                "Use /editchat to modify settings."
            )
        return

    # Create new chat settings
    db.create_chat_settings(
        {
            "chat_id": target_chat_id,
            "added_by_user_id": user_id,
            "timezone": Config.DEFAULT_TIMEZONE,
            "brief_times": ["09:00", "18:00"],
            "topics": [],
            "active": True,
        }
    )

    # Schedule briefs for the new chat
    from src.bot.scheduler import schedule_chat

    await schedule_chat(context.application, db.get_chat_settings(target_chat_id))

    await update.message.reply_text(
        f"Chat {chat_display} added successfully!\n\n"
        f"Default settings:\n"
        f"Brief times: 09:00, 18:00\n"
        f"Timezone: {Config.DEFAULT_TIMEZONE}\n\n"
        "Use /editchat to customize settings."
    )


async def editchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /editchat command - Edit settings for a specific chatroom.

    Usage: /editchat <chat_id or @username> timezone=<tz> times=<HH:MM,HH:MM> topics=<topic1,topic2>
    Examples: /editchat -123456789 timezone=Asia/Seoul or /editchat @minchoisfuture times=15:00
    """
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 1:
        await update.message.reply_text(
            "Usage: /editchat <chat_id or @username> [settings]\n\n"
            "Examples:\n"
            "/editchat @minchoisfuture timezone=Asia/Seoul\n"
            "/editchat -123456789 times=09:00,18:00\n"
            "/editchat @mychannel topics=tech,news\n\n"
            "Tip: Run without settings to see current config"
        )
        return

    # Resolve chat identifier (username or ID)
    target_chat_id, chat_title, error = await resolve_chat_identifier(
        args[0], context.bot
    )

    if error:
        await update.message.reply_text(error)
        return

    logger.info(f"Editchat command from user={user_id} for chat_id={target_chat_id}")

    db = get_supabase()
    chat_settings = db.get_chat_settings(target_chat_id)

    if not chat_settings:
        await update.message.reply_text(
            f"Chat {target_chat_id} not found.\n\nUse /addchat to add it first."
        )
        return

    # Check ownership
    if chat_settings.get("added_by_user_id") != user_id:
        await update.message.reply_text(
            f"You don't have permission to edit chat {target_chat_id}.\n\n"
            "Only the user who added this chat can edit it."
        )
        return

    # If only chat_id provided, show current settings
    if len(args) == 1:
        brief_times = chat_settings.get("brief_times", [])
        topics = chat_settings.get("topics", [])

        await update.message.reply_text(
            f"Settings for chat {target_chat_id}:\n\n"
            f"Timezone: {chat_settings.get('timezone', 'UTC')}\n"
            f"Brief times: {', '.join(brief_times)}\n"
            f"Topics: {', '.join(topics) if topics else 'None'}\n"
            f"Active: {'Yes' if chat_settings.get('active') else 'No'}\n\n"
            "To edit:\n"
            f"/editchat {target_chat_id} timezone=Asia/Seoul times=09:00,18:00"
        )
        return

    # Parse settings from remaining arguments
    settings_update = {}

    for arg in args[1:]:
        if "=" in arg:
            key, value = arg.split("=", 1)

            if key == "timezone":
                settings_update["timezone"] = value
            elif key == "times":
                times = [t.strip() for t in value.split(",")]
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
                topics = [t.strip() for t in value.split(",")]
                settings_update["topics"] = topics

    if not settings_update:
        await update.message.reply_text("No valid settings provided.")
        return

    # Apply updates
    db.update_chat_settings(target_chat_id, settings_update)

    # Reschedule jobs
    from src.bot.scheduler import reschedule_chat

    await reschedule_chat(context.application, target_chat_id)

    await update.message.reply_text(
        f"Chat {target_chat_id} settings updated!\n\n"
        f"Use /editchat {target_chat_id} to view current settings."
    )


async def listchats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /listchats command - List all chatrooms owned by the user."""
    user_id = update.effective_user.id

    logger.info(f"Listchats command from user={user_id}")

    db = get_supabase()
    chats = db.get_user_chats(user_id)

    if not chats:
        await update.message.reply_text(
            "You haven't added any chatrooms yet.\n\nUse /addchat <chat_id> to add one."
        )
        return

    message_parts = ["Your managed chatrooms:\n"]

    for chat in chats:
        brief_times = chat.get("brief_times", [])
        topics = chat.get("topics", [])

        message_parts.append(
            f"\nChat ID: {chat.get('chat_id')}\n"
            f"   Timezone: {chat.get('timezone', 'UTC')}\n"
            f"   Times: {', '.join(brief_times)}\n"
            f"   Topics: {', '.join(topics) if topics else 'None'}"
        )

    message_parts.append(f"\n\nTotal: {len(chats)} chatroom(s)")

    await update.message.reply_text("".join(message_parts))


async def removechat_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /removechat command - Remove (deactivate) a chatroom.

    Usage: /removechat <chat_id or @username>
    Examples: /removechat -123456789 or /removechat @minchoisfuture
    """
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 1:
        await update.message.reply_text(
            "Usage: /removechat <chat_id or @username>\n\n"
            "Examples:\n"
            "/removechat -123456789\n"
            "/removechat @minchoisfuture\n\n"
            "This will deactivate briefs for the specified chat."
        )
        return

    # Resolve chat identifier (username or ID)
    target_chat_id, chat_title, error = await resolve_chat_identifier(
        args[0], context.bot
    )

    if error:
        await update.message.reply_text(error)
        return

    logger.info(f"Removechat command from user={user_id} for chat_id={target_chat_id}")

    db = get_supabase()
    chat_settings = db.get_chat_settings(target_chat_id)

    if not chat_settings:
        await update.message.reply_text(f"Chat {target_chat_id} not found.")
        return

    # Check ownership
    if chat_settings.get("added_by_user_id") != user_id:
        await update.message.reply_text(
            f"You don't have permission to remove chat {target_chat_id}.\n\n"
            "Only the user who added this chat can remove it."
        )
        return

    if not chat_settings.get("active"):
        await update.message.reply_text(f"Chat {target_chat_id} is already inactive.")
        return

    # Soft delete (deactivate)
    db.deactivate_chat(target_chat_id)

    # Unschedule jobs
    from src.bot.scheduler import unschedule_chat

    await unschedule_chat(context.application, target_chat_id)

    await update.message.reply_text(
        f"Chat {target_chat_id} has been removed.\n\n"
        "Briefs will no longer be sent to this chat.\n"
        "Use /addchat to re-add it if needed."
    )


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /topics command - View or set topics for AI filtering.

    Usage:
        /topics - Show current topics
        /topics web3,ai,security - Set new topics
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    args = context.args

    db = get_supabase()

    # Get chat settings for current chat, or the user's first chat
    chat_settings = db.get_chat_settings(chat_id)

    if not chat_settings:
        # Try to find any chat owned by this user
        user_chats = db.get_user_chats(user_id)
        if user_chats:
            chat_settings = user_chats[0]

    if not chat_settings:
        await update.message.reply_text(
            "No chats configured yet.\n\n"
            "Use /start to initialize or /addchat to add a chatroom."
        )
        return

    # If no args, show current topics
    if not args:
        topics = chat_settings.get("topics", [])

        if topics:
            message = (
                "**Current Topics:**\n\n"
                + "\n".join(f"  - {topic}" for topic in topics)
                + "\n\n"
                "These topics are used by AI to filter relevant messages.\n\n"
                "To change topics:\n"
                "`/topics web3,ai,security,crypto`"
            )
        else:
            message = (
                "**No Topics Set**\n\n"
                "Topics help the AI filter messages that matter to you.\n\n"
                "Examples:\n"
                "`/topics web3,ai,security`\n"
                "`/topics crypto,defi,nft`\n"
                "`/topics tech,startup,investing`\n\n"
                "The AI will analyze messages and only include those "
                "related to your topics in the brief."
            )

        await update.message.reply_text(message, parse_mode="Markdown")
        return

    # Set new topics
    # Join all args in case user used spaces
    topics_str = " ".join(args)
    # Split by comma and clean up
    new_topics = [t.strip().lower() for t in topics_str.split(",") if t.strip()]

    if not new_topics:
        await update.message.reply_text(
            "No valid topics provided.\n\n"
            "Use comma-separated topics:\n"
            "`/topics web3,ai,security`"
        )
        return

    # Limit topics to reasonable number
    if len(new_topics) > 10:
        new_topics = new_topics[:10]
        await update.message.reply_text(
            "Limited to 10 topics maximum. Extra topics were ignored."
        )

    # Update topics
    target_chat_id = chat_settings.get("chat_id")
    db.update_chat_settings(target_chat_id, {"topics": new_topics})

    await update.message.reply_text(
        f"Topics updated!\n\n"
        f"**Your Topics:**\n"
        + "\n".join(f"  - {topic}" for topic in new_topics)
        + "\n\n"
        "The AI will filter messages based on these topics.\n"
        "Use `/test` to see a sample brief.",
        parse_mode="Markdown",
    )

    logger.info(f"User {user_id} updated topics to: {new_topics}")
