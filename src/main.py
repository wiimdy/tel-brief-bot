"""Main entry point for Telegram Brief Bot."""

import asyncio
import logging
import sys
from zoneinfo import ZoneInfo

from telegram.ext import Application, CommandHandler

from src.config import Config
from src.db.database import init_db
from src.bot.handlers import (
    start_command,
    settings_command,
    status_command,
    test_command,
    addchat_command,
    editchat_command,
    listchats_command,
    removechat_command,
    topics_command,
)
from src.bot.scheduler import schedule_all_chats

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log")],
)

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize bot after application is created.

    Args:
        application: Telegram Application instance
    """
    logger.info("Initializing bot...")

    # Schedule all existing chats
    await schedule_all_chats(application)

    # Start message collection if enabled
    if Config.ENABLE_MESSAGE_COLLECTION:
        try:
            Config.validate_message_collection()
            await start_message_collection(application)
        except ValueError as e:
            logger.warning(f"Message collection disabled: {e}")

    logger.info("Bot initialization complete")


async def start_message_collection(application: Application) -> None:
    """Start the message collection background task.

    Args:
        application: Telegram Application instance
    """
    from src.userbot.client import get_telethon_client
    from src.userbot.collector import get_message_collector

    logger.info("Starting message collection...")

    # Connect Telethon client
    client = get_telethon_client()
    connected = await client.connect()

    if not connected:
        logger.error(
            "Failed to connect Telethon client. "
            "Run 'python -m src.userbot.auth' to authenticate first."
        )
        return

    logger.info("Telethon client connected successfully")

    # Schedule periodic collection job
    collector = get_message_collector()

    async def collect_messages_job(context):
        """Background job to collect messages from all monitored chats."""
        if not Config.BRIEF_RECIPIENT_ID:
            return

        try:
            # Get last brief time to collect only new messages
            last_brief = collector.get_last_brief_time(Config.BRIEF_RECIPIENT_ID)
            await collector.collect_from_all_monitored(
                user_id=Config.BRIEF_RECIPIENT_ID, since=last_brief
            )
        except Exception as e:
            logger.error(f"Error in message collection job: {e}")

    # Run collection every COLLECTION_INTERVAL seconds
    application.job_queue.run_repeating(
        collect_messages_job,
        interval=Config.COLLECTION_INTERVAL,
        first=10,  # Start 10 seconds after boot
        name="message_collection",
    )

    logger.info(
        f"Message collection scheduled every {Config.COLLECTION_INTERVAL} seconds"
    )


async def post_shutdown(application: Application) -> None:
    """Cleanup before bot shutdown.

    Args:
        application: Telegram Application instance
    """
    logger.info("Shutting down bot...")

    # Stop all running jobs
    if application.job_queue:
        application.job_queue.stop()

    # Disconnect Telethon client if connected
    if Config.ENABLE_MESSAGE_COLLECTION:
        try:
            from src.userbot.client import get_telethon_client

            client = get_telethon_client()
            await client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Telethon client: {e}")

    logger.info("Bot shutdown complete")


def main() -> None:
    """Start the bot."""
    logger.info("=" * 50)
    logger.info("Starting Telegram Brief Bot")
    logger.info("=" * 50)

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize database
    logger.info(f"Initializing database: {Config.DATABASE_URL}")
    init_db(Config.DATABASE_URL)

    # Create application
    logger.info("Creating Telegram application...")
    application = (
        Application.builder()
        .token(Config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register command handlers
    logger.info("Registering command handlers...")
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("test", test_command))

    # Multi-chat management commands
    application.add_handler(CommandHandler("addchat", addchat_command))
    application.add_handler(CommandHandler("editchat", editchat_command))
    application.add_handler(CommandHandler("listchats", listchats_command))
    application.add_handler(CommandHandler("removechat", removechat_command))
    application.add_handler(CommandHandler("topics", topics_command))

    # Start the bot
    logger.info("Starting bot polling...")
    logger.info(f"Default timezone: {Config.DEFAULT_TIMEZONE}")
    logger.info(f"Default brief times: {Config.get_default_brief_times()}")
    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Run the bot until Ctrl+C
    application.run_polling(
        allowed_updates=["message", "callback_query"], drop_pending_updates=True
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
