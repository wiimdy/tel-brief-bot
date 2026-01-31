"""Telethon client wrapper for Telegram User API."""

import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message, User, Chat, Channel

from src.config import Config

logger = logging.getLogger(__name__)


class TelethonClient:
    """Wrapper for Telethon Telegram client."""

    def __init__(self):
        """Initialize Telethon client with config."""
        self.api_id = Config.TELEGRAM_API_ID
        self.api_hash = Config.TELEGRAM_API_HASH
        self.phone = Config.TELEGRAM_PHONE
        self.session_path = Config.TELEGRAM_SESSION_PATH

        # Ensure session directory exists
        session_dir = os.path.dirname(self.session_path)
        if session_dir and not os.path.exists(session_dir):
            os.makedirs(session_dir)

        self._client: Optional[TelegramClient] = None
        self._connected = False

    @property
    def client(self) -> TelegramClient:
        """Get or create the Telethon client."""
        if self._client is None:
            self._client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        return self._client

    async def connect(self) -> bool:
        """Connect to Telegram.

        Returns:
            True if connected and authorized
        """
        try:
            await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.warning("User not authorized. Please run authentication flow.")
                return False

            me = await self.client.get_me()
            logger.info(f"Connected as: {me.first_name} (@{me.username})")
            self._connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Telegram."""
        if self._client:
            await self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from Telegram")

    async def is_connected(self) -> bool:
        """Check if client is connected and authorized."""
        if not self._client:
            return False
        return self._client.is_connected() and await self._client.is_user_authorized()

    async def authenticate(self):
        """Interactive authentication flow.

        This should be run once to create the session file.
        """
        await self.client.connect()

        if await self.client.is_user_authorized():
            me = await self.client.get_me()
            logger.info(f"Already authorized as: {me.first_name}")
            return True

        # Send code request
        await self.client.send_code_request(self.phone)
        logger.info(f"Code sent to {self.phone}")

        # Get code from user
        code = input("Enter the verification code: ")

        try:
            await self.client.sign_in(self.phone, code)
        except Exception as e:
            # May need 2FA password
            if "Two-steps verification" in str(e) or "password" in str(e).lower():
                password = input("Enter 2FA password: ")
                await self.client.sign_in(password=password)
            else:
                raise

        me = await self.client.get_me()
        logger.info(f"Authenticated as: {me.first_name} (@{me.username})")
        return True

    async def get_messages(
        self, chat_id: int, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get messages from a chat.

        Args:
            chat_id: Chat ID to fetch messages from
            since: Only get messages after this datetime
            limit: Maximum number of messages to fetch

        Returns:
            List of message dictionaries
        """
        if not await self.is_connected():
            logger.error("Client not connected")
            return []

        try:
            messages = []

            # Note: Telethon's offset_date returns messages BEFORE that date,
            # so we fetch recent messages and filter by 'since' afterward
            async for message in self.client.iter_messages(
                chat_id,
                limit=limit,
                # Don't use offset_date - it returns messages OLDER than the date
                # We'll filter by 'since' manually below
            ):
                # Skip non-text messages or empty messages
                if not message.text:
                    continue

                # Filter: only include messages AFTER the 'since' datetime
                if since and message.date:
                    # Make sure both are comparable (aware datetimes)
                    msg_date = message.date
                    if msg_date.tzinfo is None:
                        from datetime import timezone

                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                    since_aware = since
                    if since.tzinfo is None:
                        from datetime import timezone

                        since_aware = since.replace(tzinfo=timezone.utc)

                    if msg_date <= since_aware:
                        # Message is older than or equal to 'since', skip it
                        continue

                # Get sender info
                sender_name = "Unknown"
                sender_id = None

                if message.sender:
                    sender_id = message.sender_id
                    if isinstance(message.sender, User):
                        sender_name = message.sender.first_name or "User"
                        if message.sender.last_name:
                            sender_name += f" {message.sender.last_name}"
                    elif hasattr(message.sender, "title"):
                        sender_name = message.sender.title

                # Get chat info
                chat_name = None
                if message.chat:
                    if hasattr(message.chat, "title"):
                        chat_name = message.chat.title
                    elif hasattr(message.chat, "first_name"):
                        chat_name = message.chat.first_name

                messages.append(
                    {
                        "message_id": message.id,
                        "chat_id": chat_id,
                        "chat_name": chat_name,
                        "sender_id": sender_id,
                        "sender_name": sender_name,
                        "text": message.text,
                        "timestamp": message.date,
                    }
                )

            logger.debug(f"Fetched {len(messages)} messages from chat {chat_id}")
            return messages

        except Exception as e:
            logger.error(f"Error fetching messages from {chat_id}: {e}")
            return []

    async def get_chat_info(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a chat.

        Args:
            chat_id: Chat ID to get info for

        Returns:
            Chat info dictionary or None
        """
        if not await self.is_connected():
            return None

        try:
            entity = await self.client.get_entity(chat_id)

            info = {
                "id": entity.id,
                "type": type(entity).__name__,
            }

            if hasattr(entity, "title"):
                info["name"] = entity.title
            elif hasattr(entity, "first_name"):
                info["name"] = entity.first_name
            else:
                info["name"] = str(entity.id)

            if hasattr(entity, "username"):
                info["username"] = entity.username

            return info

        except Exception as e:
            logger.error(f"Error getting chat info for {chat_id}: {e}")
            return None

    async def run_until_disconnected(self):
        """Keep the client running until disconnected."""
        await self.client.run_until_disconnected()


# Singleton instance
_client_instance: Optional[TelethonClient] = None


def get_telethon_client() -> TelethonClient:
    """Get the global Telethon client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = TelethonClient()
    return _client_instance
