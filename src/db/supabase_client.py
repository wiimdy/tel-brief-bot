"""Supabase client wrapper for database operations."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from supabase import create_client, Client

from src.config import Config

logger = logging.getLogger(__name__)


class SupabaseDB:
    """Supabase database client wrapper."""

    def __init__(self):
        """Initialize Supabase client."""
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Get or create Supabase client."""
        if self._client is None:
            self._client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        return self._client

    # ==================== Chat Settings ====================

    def get_chat_settings(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get chat settings by chat_id."""
        try:
            response = (
                self.client.table("chat_settings")
                .select("*")
                .eq("chat_id", chat_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            if "No rows found" in str(e) or "0 rows" in str(e):
                return None
            logger.error(f"Error getting chat settings: {e}")
            return None

    def get_all_active_chats(self) -> List[Dict[str, Any]]:
        """Get all active chat settings."""
        try:
            response = (
                self.client.table("chat_settings")
                .select("*")
                .eq("active", True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting active chats: {e}")
            return []

    def get_user_chats(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all chats owned by a user."""
        try:
            response = (
                self.client.table("chat_settings")
                .select("*")
                .eq("added_by_user_id", user_id)
                .eq("active", True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting user chats: {e}")
            return []

    def create_chat_settings(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new chat settings."""
        try:
            response = self.client.table("chat_settings").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating chat settings: {e}")
            return None

    def update_chat_settings(
        self, chat_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update chat settings."""
        try:
            response = (
                self.client.table("chat_settings")
                .update(data)
                .eq("chat_id", chat_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating chat settings: {e}")
            return None

    def deactivate_chat(self, chat_id: int) -> bool:
        """Soft delete (deactivate) a chat."""
        result = self.update_chat_settings(chat_id, {"active": False})
        return result is not None

    # ==================== Collected Messages ====================

    def add_collected_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a collected message."""
        try:
            response = self.client.table("collected_messages").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error adding collected message: {e}")
            return None

    def add_collected_messages_batch(self, messages: List[Dict[str, Any]]) -> int:
        """Add multiple collected messages at once."""
        if not messages:
            return 0
        try:
            response = (
                self.client.table("collected_messages").insert(messages).execute()
            )
            return len(response.data) if response.data else 0
        except Exception as e:
            logger.error(f"Error batch inserting messages: {e}")
            return 0

    def get_unprocessed_messages(
        self, chat_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Get unprocessed messages, optionally filtered by chat IDs."""
        try:
            query = (
                self.client.table("collected_messages")
                .select("*")
                .eq("processed", False)
                .order("timestamp", desc=False)
            )
            if chat_ids:
                query = query.in_("source_chat_id", chat_ids)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting unprocessed messages: {e}")
            return []

    def message_exists(self, source_chat_id: int, message_id: int) -> bool:
        """Check if a message already exists."""
        try:
            response = (
                self.client.table("collected_messages")
                .select("id")
                .eq("source_chat_id", source_chat_id)
                .eq("message_id", message_id)
                .limit(1)
                .execute()
            )
            return len(response.data) > 0 if response.data else False
        except Exception as e:
            logger.error(f"Error checking message exists: {e}")
            return False

    def mark_messages_processed(self, message_ids: List[int]) -> bool:
        """Mark messages as processed."""
        if not message_ids:
            return True
        try:
            self.client.table("collected_messages").update({"processed": True}).in_(
                "id", message_ids
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking messages processed: {e}")
            return False

    def delete_processed_messages(self) -> int:
        """Delete all processed messages (cleanup after brief)."""
        try:
            response = (
                self.client.table("collected_messages")
                .delete()
                .eq("processed", True)
                .execute()
            )
            deleted = len(response.data) if response.data else 0
            logger.info(f"Deleted {deleted} processed messages")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting processed messages: {e}")
            return 0

    def delete_messages_by_ids(self, message_ids: List[int]) -> int:
        """Delete messages by their IDs (immediate cleanup)."""
        if not message_ids:
            return 0
        try:
            response = (
                self.client.table("collected_messages")
                .delete()
                .in_("id", message_ids)
                .execute()
            )
            deleted = len(response.data) if response.data else 0
            logger.info(f"Deleted {deleted} messages after brief")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
            return 0

    # ==================== Brief History ====================

    def add_brief_history(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a brief history record."""
        try:
            response = self.client.table("brief_history").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error adding brief history: {e}")
            return None

    def get_last_brief_time(self, recipient_id: int) -> Optional[datetime]:
        """Get the time of the last brief sent to a user."""
        try:
            response = (
                self.client.table("brief_history")
                .select("brief_time")
                .eq("recipient_id", recipient_id)
                .order("brief_time", desc=True)
                .limit(1)
                .execute()
            )
            if response.data:
                return datetime.fromisoformat(
                    response.data[0]["brief_time"].replace("Z", "+00:00")
                )
            return None
        except Exception as e:
            logger.error(f"Error getting last brief time: {e}")
            return None


# Singleton instance
_supabase_instance: Optional[SupabaseDB] = None


def get_supabase() -> SupabaseDB:
    """Get the global Supabase instance."""
    global _supabase_instance
    if _supabase_instance is None:
        _supabase_instance = SupabaseDB()
    return _supabase_instance
