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

    # Database URL (defaults to SQLite in current directory)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///briefbot.db")

    # SQL Debug mode
    SQL_DEBUG: bool = os.getenv("SQL_DEBUG", "false").lower() == "true"

    # Default timezone for new chats
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    # Default brief times (comma-separated, 24-hour format)
    DEFAULT_BRIEF_TIMES: str = os.getenv("DEFAULT_BRIEF_TIMES", "09:00,18:00")

    # Scheduler check interval (seconds)
    SCHEDULER_CHECK_INTERVAL: int = int(os.getenv("SCHEDULER_CHECK_INTERVAL", "60"))

    # Log level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

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
