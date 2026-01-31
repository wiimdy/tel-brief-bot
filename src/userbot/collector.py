"""Message collector for gathering messages from monitored chats."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.database import db
from src.db.models import ChatSettings, CollectedMessage, BriefHistory
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

        session: Session = db.get_sync_session()
        collected = 0

        try:
            for msg in messages:
                # Check if message already exists
                existing = (
                    session.query(CollectedMessage)
                    .filter_by(
                        source_chat_id=msg["chat_id"], message_id=msg["message_id"]
                    )
                    .first()
                )

                if existing:
                    continue

                # Create new message record
                collected_msg = CollectedMessage(
                    source_chat_id=msg["chat_id"],
                    source_chat_name=msg.get("chat_name"),
                    sender_id=msg.get("sender_id"),
                    sender_name=msg.get("sender_name"),
                    message_id=msg["message_id"],
                    text=msg["text"],
                    timestamp=msg["timestamp"],
                    processed=False,
                )
                session.add(collected_msg)
                collected += 1

            session.commit()
            logger.info(f"Collected {collected} new messages from chat {chat_id}")

        except Exception as e:
            logger.error(f"Error saving messages: {e}")
            session.rollback()

        finally:
            session.close()

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
        session: Session = db.get_sync_session()

        try:
            # Get all active chats for this user
            chats = (
                session.query(ChatSettings)
                .filter_by(added_by_user_id=user_id, active=True)
                .all()
            )

            chat_ids = [chat.chat_id for chat in chats]

        finally:
            session.close()

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
    ) -> List[CollectedMessage]:
        """Get all unprocessed messages.

        Args:
            chat_ids: Optional list of chat IDs to filter by

        Returns:
            List of unprocessed CollectedMessage objects
        """
        session: Session = db.get_sync_session()

        try:
            query = session.query(CollectedMessage).filter_by(processed=False)

            if chat_ids:
                query = query.filter(CollectedMessage.source_chat_id.in_(chat_ids))

            # Order by timestamp
            messages = query.order_by(CollectedMessage.timestamp.asc()).all()

            return messages

        finally:
            session.close()

    def mark_messages_processed(self, message_ids: List[int]):
        """Mark messages as processed.

        Args:
            message_ids: List of message IDs to mark as processed
        """
        session: Session = db.get_sync_session()

        try:
            session.query(CollectedMessage).filter(
                CollectedMessage.id.in_(message_ids)
            ).update({CollectedMessage.processed: True}, synchronize_session=False)

            session.commit()
            logger.debug(f"Marked {len(message_ids)} messages as processed")

        except Exception as e:
            logger.error(f"Error marking messages processed: {e}")
            session.rollback()

        finally:
            session.close()

    def clear_processed_messages(self, older_than_hours: int = 24):
        """Delete old processed messages.

        Args:
            older_than_hours: Delete messages older than this many hours
        """
        session: Session = db.get_sync_session()
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)

        try:
            deleted = (
                session.query(CollectedMessage)
                .filter(
                    CollectedMessage.processed == True,
                    CollectedMessage.created_at < cutoff,
                )
                .delete(synchronize_session=False)
            )

            session.commit()
            logger.info(f"Deleted {deleted} old processed messages")

        except Exception as e:
            logger.error(f"Error clearing old messages: {e}")
            session.rollback()

        finally:
            session.close()

    def get_last_brief_time(self, user_id: int) -> Optional[datetime]:
        """Get the time of the last brief sent to a user.

        Args:
            user_id: User ID to check

        Returns:
            Datetime of last brief or None
        """
        session: Session = db.get_sync_session()

        try:
            last_brief = (
                session.query(BriefHistory)
                .filter_by(recipient_id=user_id)
                .order_by(BriefHistory.brief_time.desc())
                .first()
            )

            if last_brief:
                return last_brief.brief_time
            return None

        finally:
            session.close()

    def record_brief_sent(
        self, user_id: int, message_count: int, topics: List[str], summary_preview: str
    ):
        """Record that a brief was sent.

        Args:
            user_id: Recipient user ID
            message_count: Number of messages in the brief
            topics: Topics covered
            summary_preview: Preview of the summary
        """
        import json

        session: Session = db.get_sync_session()

        try:
            history = BriefHistory(
                recipient_id=user_id,
                brief_time=datetime.utcnow(),
                message_count=message_count,
                topics_covered=json.dumps(topics),
                summary_preview=summary_preview[:500] if summary_preview else None,
            )
            session.add(history)
            session.commit()

        except Exception as e:
            logger.error(f"Error recording brief history: {e}")
            session.rollback()

        finally:
            session.close()


# Singleton instance
_collector_instance: Optional[MessageCollector] = None


def get_message_collector() -> MessageCollector:
    """Get the global message collector instance."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = MessageCollector()
    return _collector_instance
