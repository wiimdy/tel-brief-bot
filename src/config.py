"""Configuration management for Telegram Brief Bot."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""

    # Telegram Bot Token (REQUIRED)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Database URL (defaults to SQLite in current directory) - Legacy
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///briefbot.db")

    # SQL Debug mode
    SQL_DEBUG: bool = os.getenv("SQL_DEBUG", "false").lower() == "true"

    # Supabase (Primary database)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    USE_SUPABASE: bool = os.getenv("USE_SUPABASE", "true").lower() == "true"

    # Default timezone for new chats
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    # Default brief times (comma-separated, 24-hour format)
    DEFAULT_BRIEF_TIMES: str = os.getenv("DEFAULT_BRIEF_TIMES", "09:00,18:00")

    # Scheduler check interval (seconds)
    SCHEDULER_CHECK_INTERVAL: int = int(os.getenv("SCHEDULER_CHECK_INTERVAL", "60"))

    # Log level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Telegram User API (for message collection)
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE: str = os.getenv("TELEGRAM_PHONE", "")
    TELEGRAM_SESSION_PATH: str = os.getenv("TELEGRAM_SESSION_PATH", "sessions/userbot")

    # Google Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Brief recipient (your personal chat ID for receiving briefs)
    BRIEF_RECIPIENT_ID: int = int(os.getenv("BRIEF_RECIPIENT_ID", "0"))

    # Message collection settings
    COLLECTION_INTERVAL: int = int(os.getenv("COLLECTION_INTERVAL", "300"))  # 5 minutes

    # Feature flags
    ENABLE_MESSAGE_COLLECTION: bool = (
        os.getenv("ENABLE_MESSAGE_COLLECTION", "false").lower() == "true"
    )

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If required configuration is missing
        """
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required. "
                "Please set it in .env file or environment variables."
            )
        return True

    @classmethod
    def validate_message_collection(cls) -> bool:
        """Validate message collection configuration.

        Returns:
            True if message collection config is valid

        Raises:
            ValueError: If required configuration is missing
        """
        errors = []

        if not cls.TELEGRAM_API_ID:
            errors.append("TELEGRAM_API_ID is required for message collection")
        if not cls.TELEGRAM_API_HASH:
            errors.append("TELEGRAM_API_HASH is required for message collection")
        if not cls.TELEGRAM_PHONE:
            errors.append("TELEGRAM_PHONE is required for message collection")
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required for AI summarization")
        if not cls.BRIEF_RECIPIENT_ID:
            errors.append("BRIEF_RECIPIENT_ID is required (your Telegram user ID)")

        if errors:
            raise ValueError(
                "Message collection configuration errors:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return True

    @classmethod
    def get_default_brief_times(cls) -> list[str]:
        """Parse default brief times from config.

        Returns:
            List of brief times in HH:MM format
        """
        return [time.strip() for time in cls.DEFAULT_BRIEF_TIMES.split(",")]


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Warning: {e}")
    print("   The bot will not start without TELEGRAM_BOT_TOKEN")
