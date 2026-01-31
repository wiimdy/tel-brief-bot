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
                added_by_user_id=user.id,
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


async def addchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addchat command - Add a new chatroom by ID.

    Usage: /addchat <chat_id>
    Example: /addchat -123456789
    """
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 1:
        await update.message.reply_text(
            "📝 Usage: /addchat <chat_id>\n\n"
            "Example: /addchat -123456789\n\n"
            "💡 Tip: Get chat_id by forwarding a message from the target chat to @userinfobot"
        )
        return

    try:
        target_chat_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat_id. Must be a number.")
        return

    logger.info(f"Addchat command from user={user_id} for chat_id={target_chat_id}")

    session: Session = db.get_sync_session()
    try:
        # Check if chat already exists
        existing = session.query(ChatSettings).filter_by(chat_id=target_chat_id).first()

        if existing:
            if existing.active:
                await update.message.reply_text(
                    f"⚠️ Chat {target_chat_id} is already registered.\n\n"
                    "Use /editchat to modify settings or /listchats to see all chats."
                )
            else:
                # Reactivate if inactive
                existing.active = True
                existing.added_by_user_id = user_id
                session.commit()

                from src.bot.scheduler import reschedule_chat

                await reschedule_chat(context.application, target_chat_id)

                await update.message.reply_text(
                    f"✅ Chat {target_chat_id} has been reactivated!\n\n"
                    "Use /editchat to modify settings."
                )
            return

        # Create new chat settings
        chat_settings = ChatSettings(
            chat_id=target_chat_id,
            added_by_user_id=user_id,
            timezone=Config.DEFAULT_TIMEZONE,
            brief_times='["09:00", "18:00"]',
            topics="[]",
            active=True,
        )
        session.add(chat_settings)
        session.commit()

        # Schedule briefs for the new chat
        from src.bot.scheduler import schedule_chat

        await schedule_chat(context.application, chat_settings)

        await update.message.reply_text(
            f"✅ Chat {target_chat_id} added successfully!\n\n"
            f"Default settings:\n"
            f"⏰ Brief times: 09:00, 18:00\n"
            f"🌍 Timezone: {Config.DEFAULT_TIMEZONE}\n\n"
            "Use /editchat to customize settings."
        )

    except Exception as e:
        logger.error(f"Error adding chat: {e}")
        await update.message.reply_text(f"❌ Error adding chat: {str(e)}")

    finally:
        session.close()


async def editchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /editchat command - Edit settings for a specific chatroom.

    Usage: /editchat <chat_id> timezone=<tz> times=<HH:MM,HH:MM> topics=<topic1,topic2>
    Example: /editchat -123456789 timezone=Asia/Seoul times=15:00,21:00
    """
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 1:
        await update.message.reply_text(
            "📝 Usage: /editchat <chat_id> [settings]\n\n"
            "Examples:\n"
            "/editchat -123456789 timezone=Asia/Seoul\n"
            "/editchat -123456789 times=09:00,18:00\n"
            "/editchat -123456789 topics=tech,news\n\n"
            "💡 Tip: Run without settings to see current config"
        )
        return

    try:
        target_chat_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat_id. Must be a number.")
        return

    logger.info(f"Editchat command from user={user_id} for chat_id={target_chat_id}")

    session: Session = db.get_sync_session()
    try:
        chat_settings = (
            session.query(ChatSettings).filter_by(chat_id=target_chat_id).first()
        )

        if not chat_settings:
            await update.message.reply_text(
                f"❌ Chat {target_chat_id} not found.\n\nUse /addchat to add it first."
            )
            return

        # Check ownership
        if chat_settings.added_by_user_id != user_id:
            await update.message.reply_text(
                f"🔒 You don't have permission to edit chat {target_chat_id}.\n\n"
                "Only the user who added this chat can edit it."
            )
            return

        # If only chat_id provided, show current settings
        if len(args) == 1:
            brief_times = chat_settings.get_brief_times()
            topics = chat_settings.get_topics()

            await update.message.reply_text(
                f"⚙️ Settings for chat {target_chat_id}:\n\n"
                f"🌍 Timezone: {chat_settings.timezone}\n"
                f"⏰ Brief times: {', '.join(brief_times)}\n"
                f"📌 Topics: {', '.join(topics) if topics else 'None'}\n"
                f"✅ Active: {'Yes' if chat_settings.active else 'No'}\n\n"
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
                                f"❌ Invalid time format: {t}. Use HH:MM"
                            )
                            return
                    settings_update["brief_times"] = times
                elif key == "topics":
                    topics = [t.strip() for t in value.split(",")]
                    settings_update["topics"] = topics

        if not settings_update:
            await update.message.reply_text("❌ No valid settings provided.")
            return

        # Apply updates
        if "timezone" in settings_update:
            chat_settings.timezone = settings_update["timezone"]
        if "brief_times" in settings_update:
            chat_settings.set_brief_times(settings_update["brief_times"])
        if "topics" in settings_update:
            chat_settings.set_topics(settings_update["topics"])

        session.commit()

        # Reschedule jobs
        from src.bot.scheduler import reschedule_chat

        await reschedule_chat(context.application, target_chat_id)

        await update.message.reply_text(
            f"✅ Chat {target_chat_id} settings updated!\n\n"
            f"Use /editchat {target_chat_id} to view current settings."
        )

    except Exception as e:
        logger.error(f"Error editing chat: {e}")
        await update.message.reply_text(f"❌ Error editing chat: {str(e)}")

    finally:
        session.close()


async def listchats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /listchats command - List all chatrooms owned by the user."""
    user_id = update.effective_user.id

    logger.info(f"Listchats command from user={user_id}")

    session: Session = db.get_sync_session()
    try:
        # Get all active chats owned by this user
        chats = (
            session.query(ChatSettings)
            .filter_by(added_by_user_id=user_id, active=True)
            .all()
        )

        if not chats:
            await update.message.reply_text(
                "📭 You haven't added any chatrooms yet.\n\n"
                "Use /addchat <chat_id> to add one."
            )
            return

        message_parts = ["📋 Your managed chatrooms:\n"]

        for chat in chats:
            brief_times = chat.get_brief_times()
            topics = chat.get_topics()

            message_parts.append(
                f"\n🔹 Chat ID: {chat.chat_id}\n"
                f"   🌍 Timezone: {chat.timezone}\n"
                f"   ⏰ Times: {', '.join(brief_times)}\n"
                f"   📌 Topics: {', '.join(topics) if topics else 'None'}"
            )

        message_parts.append(f"\n\n📊 Total: {len(chats)} chatroom(s)")

        await update.message.reply_text("".join(message_parts))

    finally:
        session.close()


async def removechat_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /removechat command - Remove (deactivate) a chatroom.

    Usage: /removechat <chat_id>
    Example: /removechat -123456789
    """
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 1:
        await update.message.reply_text(
            "📝 Usage: /removechat <chat_id>\n\n"
            "Example: /removechat -123456789\n\n"
            "⚠️ This will deactivate briefs for the specified chat."
        )
        return

    try:
        target_chat_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid chat_id. Must be a number.")
        return

    logger.info(f"Removechat command from user={user_id} for chat_id={target_chat_id}")

    session: Session = db.get_sync_session()
    try:
        chat_settings = (
            session.query(ChatSettings).filter_by(chat_id=target_chat_id).first()
        )

        if not chat_settings:
            await update.message.reply_text(f"❌ Chat {target_chat_id} not found.")
            return

        # Check ownership
        if chat_settings.added_by_user_id != user_id:
            await update.message.reply_text(
                f"🔒 You don't have permission to remove chat {target_chat_id}.\n\n"
                "Only the user who added this chat can remove it."
            )
            return

        if not chat_settings.active:
            await update.message.reply_text(
                f"⚠️ Chat {target_chat_id} is already inactive."
            )
            return

        # Soft delete (deactivate)
        chat_settings.active = False
        session.commit()

        # Unschedule jobs
        from src.bot.scheduler import unschedule_chat

        await unschedule_chat(context.application, target_chat_id)

        await update.message.reply_text(
            f"✅ Chat {target_chat_id} has been removed.\n\n"
            "Briefs will no longer be sent to this chat.\n"
            "Use /addchat to re-add it if needed."
        )

    except Exception as e:
        logger.error(f"Error removing chat: {e}")
        await update.message.reply_text(f"❌ Error removing chat: {str(e)}")

    finally:
        session.close()
