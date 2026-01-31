"""Database models for Telegram Brief Bot."""

from datetime import datetime
from typing import List
import json

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatSettings(Base):
    """Settings for each Telegram chat."""

    __tablename__ = "chat_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, unique=True, nullable=False, index=True)
    added_by_user_id = Column(
        Integer, nullable=True, index=True
    )  # Tracks who added this chat
    timezone = Column(String(50), nullable=False, default="UTC")
    brief_times = Column(
        Text, nullable=False, default='["09:00", "18:00"]'
    )  # JSON array
    topics = Column(Text, nullable=False, default="[]")  # JSON array
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def get_brief_times(self) -> List[str]:
        """Parse brief_times JSON string to list."""
        try:
            return json.loads(self.brief_times)
        except (json.JSONDecodeError, TypeError):
            return ["09:00", "18:00"]

    def set_brief_times(self, times: List[str]) -> None:
        """Convert list to JSON string for storage."""
        self.brief_times = json.dumps(times)

    def get_topics(self) -> List[str]:
        """Parse topics JSON string to list."""
        try:
            return json.loads(self.topics)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_topics(self, topics: List[str]) -> None:
        """Convert list to JSON string for storage."""
        self.topics = json.dumps(topics)

    def __repr__(self) -> str:
        return f"<ChatSettings(chat_id={self.chat_id}, timezone={self.timezone}, active={self.active})>"


class CollectedMessage(Base):
    """Temporarily stored messages for briefing."""

    __tablename__ = "collected_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_chat_id = Column(Integer, nullable=False, index=True)
    source_chat_name = Column(String(255), nullable=True)
    sender_id = Column(Integer, nullable=True)
    sender_name = Column(String(255), nullable=True)
    message_id = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        text_preview = (
            (self.text[:50] + "...") if self.text and len(self.text) > 50 else self.text
        )
        return f"<CollectedMessage(chat={self.source_chat_id}, sender={self.sender_name}, text={text_preview})>"


class BriefHistory(Base):
    """History of sent briefs for tracking."""

    __tablename__ = "brief_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_id = Column(Integer, nullable=False, index=True)
    brief_time = Column(DateTime, nullable=False)
    message_count = Column(Integer, default=0)
    topics_covered = Column(Text, nullable=True)  # JSON array
    summary_preview = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<BriefHistory(recipient={self.recipient_id}, time={self.brief_time}, messages={self.message_count})>"
