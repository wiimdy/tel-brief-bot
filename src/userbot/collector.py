"""Message collector for gathering messages from monitored chats using Supabase."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.db.supabase_client import get_supabase
from src.userbot.client import TelethonClient, get_telethon_client

logger = logging.getLogger(__name__)


class MessageCollector:
    """Collects messages from monitored Telegram chats."""

    def __init__(self, client: Optional[TelethonClient] = None):
        """Initialize the collector.

        Args:
            client: Telethon client to use, or None to use global instance
        """
        self.client = client or get_telethon_client()
        self.db = get_supabase()

    async def collect_from_chat(
        self, chat_id: int, since: Optional[datetime] = None, limit: int = 100
    ) -> int:
        """Collect messages from a single chat.

        Args:
            chat_id: Chat ID to collect from
            since: Only collect messages after this time
            limit: Maximum messages to collect

        Returns:
            Number of messages collected
        """
        messages = await self.client.get_messages(chat_id, since=since, limit=limit)

        if not messages:
            return 0

        collected = 0
        messages_to_insert = []

        for msg in messages:
            # Check if message already exists
            if self.db.message_exists(msg["chat_id"], msg["message_id"]):
                continue

            # Prepare message for insertion
            messages_to_insert.append(
                {
                    "source_chat_id": msg["chat_id"],
                    "source_chat_name": msg.get("chat_name"),
                    "sender_id": msg.get("sender_id"),
                    "sender_name": msg.get("sender_name"),
                    "message_id": msg["message_id"],
                    "text": msg["text"],
                    "timestamp": msg["timestamp"].isoformat()
                    if msg.get("timestamp")
                    else None,
                    "processed": False,
                }
            )

        # Batch insert
        if messages_to_insert:
            collected = self.db.add_collected_messages_batch(messages_to_insert)
            logger.info(f"Collected {collected} new messages from chat {chat_id}")

        return collected

    async def collect_from_all_monitored(
        self, user_id: int, since: Optional[datetime] = None
    ) -> int:
        """Collect messages from all chats monitored by a user.

        Args:
            user_id: User ID who owns the monitored chats
            since: Only collect messages after this time

        Returns:
            Total number of messages collected
        """
        chats = self.db.get_user_chats(user_id)
        chat_ids = [chat.get("chat_id") for chat in chats if chat.get("chat_id")]

        if not chat_ids:
            logger.debug(f"No monitored chats for user {user_id}")
            return 0

        total_collected = 0

        for chat_id in chat_ids:
            try:
                collected = await self.collect_from_chat(chat_id, since=since)
                total_collected += collected
            except Exception as e:
                logger.error(f"Error collecting from chat {chat_id}: {e}")

        logger.info(
            f"Collected {total_collected} total messages from {len(chat_ids)} chats"
        )
        return total_collected

    def get_unprocessed_messages(
        self, chat_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Get all unprocessed messages.

        Args:
            chat_ids: Optional list of chat IDs to filter by

        Returns:
            List of unprocessed message dictionaries
        """
        return self.db.get_unprocessed_messages(chat_ids)

    def mark_messages_processed(self, message_ids: List[int]) -> bool:
        """Mark messages as processed.

        Args:
            message_ids: List of message IDs to mark as processed

        Returns:
            True if successful
        """
        return self.db.mark_messages_processed(message_ids)

    def delete_messages(self, message_ids: List[int]) -> int:
        """Delete messages by IDs (cleanup after brief).

        Args:
            message_ids: List of message IDs to delete

        Returns:
            Number of messages deleted
        """
        return self.db.delete_messages_by_ids(message_ids)

    def cleanup_processed_messages(self) -> int:
        """Delete all processed messages.

        Returns:
            Number of messages deleted
        """
        return self.db.delete_processed_messages()

    def get_last_brief_time(self, user_id: int) -> Optional[datetime]:
        """Get the time of the last brief sent to a user.

        Args:
            user_id: User ID to check

        Returns:
            Datetime of last brief or None
        """
        return self.db.get_last_brief_time(user_id)

    def record_brief_sent(
        self, user_id: int, message_count: int, topics: List[str], summary_preview: str
    ) -> None:
        """Record that a brief was sent.

        Args:
            user_id: Recipient user ID
            message_count: Number of messages in the brief
            topics: Topics covered
            summary_preview: Preview of the summary
        """
        self.db.add_brief_history(
            {
                "recipient_id": user_id,
                "brief_time": datetime.utcnow().isoformat(),
                "message_count": message_count,
                "topics_covered": topics,
                "summary_preview": summary_preview[:500] if summary_preview else None,
            }
        )


# Singleton instance
_collector_instance: Optional[MessageCollector] = None


def get_message_collector() -> MessageCollector:
    """Get the global message collector instance."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = MessageCollector()
    return _collector_instance
