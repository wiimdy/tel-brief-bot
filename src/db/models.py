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
