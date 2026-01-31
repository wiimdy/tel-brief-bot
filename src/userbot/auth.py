"""Authentication script for Telethon (Telegram User API).

Run this script once to authenticate your Telegram account.
This will create a session file that allows the bot to access your messages.

Usage:
    python -m src.userbot.auth
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.config import Config
from src.userbot.client import TelethonClient


async def main():
    """Run the authentication flow."""
    print("=" * 50)
    print("Telegram User API Authentication")
    print("=" * 50)
    print()

    # Validate config
    errors = []
    if not Config.TELEGRAM_API_ID:
        errors.append("TELEGRAM_API_ID is not set")
    if not Config.TELEGRAM_API_HASH:
        errors.append("TELEGRAM_API_HASH is not set")
    if not Config.TELEGRAM_PHONE:
        errors.append("TELEGRAM_PHONE is not set")

    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print()
        print("Please set these in your .env file:")
        print("  1. Go to https://my.telegram.org/apps")
        print("  2. Log in with your phone number")
        print("  3. Create a new application")
        print("  4. Copy the API ID and API Hash to .env")
        print()
        print("Example .env:")
        print("  TELEGRAM_API_ID=12345678")
        print("  TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890")
        print("  TELEGRAM_PHONE=+1234567890")
        sys.exit(1)

    print(f"API ID: {Config.TELEGRAM_API_ID}")
    print(f"Phone: {Config.TELEGRAM_PHONE}")
    print(f"Session path: {Config.TELEGRAM_SESSION_PATH}")
    print()

    client = TelethonClient()

    try:
        success = await client.authenticate()
        if success:
            print()
            print("=" * 50)
            print("Authentication successful!")
            print("=" * 50)
            print()
            print("Your session has been saved. The bot can now access your messages.")
            print()
            print("Next steps:")
            print("  1. Set ENABLE_MESSAGE_COLLECTION=true in .env")
            print("  2. Set BRIEF_RECIPIENT_ID to your Telegram user ID")
            print("  3. Add chats to monitor with /addchat")
            print("  4. Set your topics with /topics")
            print("  5. Start the bot: python -m src.main")
        else:
            print("Authentication failed. Please check your credentials.")
            sys.exit(1)

    except Exception as e:
        print(f"Error during authentication: {e}")
        sys.exit(1)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
