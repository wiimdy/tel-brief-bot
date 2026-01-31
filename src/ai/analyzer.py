"""Message analyzer combining collection and AI analysis with auto-cleanup."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.db.supabase_client import get_supabase
from src.ai.gemini import GeminiClient, get_gemini_client
from src.userbot.collector import MessageCollector, get_message_collector

logger = logging.getLogger(__name__)


class MessageAnalyzer:
    """Analyzes collected messages using AI with automatic cleanup."""

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        collector: Optional[MessageCollector] = None,
    ):
        """Initialize the analyzer.

        Args:
            gemini_client: Gemini client to use
            collector: Message collector to use
        """
        self.gemini = gemini_client or get_gemini_client()
        self.collector = collector or get_message_collector()
        self.db = get_supabase()

    async def analyze_for_user(
        self, user_id: int, topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze collected messages for a user.

        Args:
            user_id: User ID to analyze messages for
            topics: Topics to filter by (or get from user's settings)

        Returns:
            Analysis result dict with 'summary', 'message_count', 'topics', etc.
        """
        # Get user's chats
        chats = self.db.get_user_chats(user_id)
        chat_ids = [chat.get("chat_id") for chat in chats if chat.get("chat_id")]

        # Get topics from first chat if not provided
        if topics is None and chats:
            topics = chats[0].get("topics", [])

        if not chat_ids:
            return {
                "success": False,
                "error": "No monitored chats found",
                "summary": None,
                "message_count": 0,
                "topics": topics or [],
            }

        # Get unprocessed messages
        messages = self.collector.get_unprocessed_messages(chat_ids)

        if not messages:
            return {
                "success": True,
                "summary": "No new messages since last brief.",
                "message_count": 0,
                "topics": topics or [],
                "relevant_count": 0,
            }

        # Convert to format for AI
        message_dicts = []
        message_ids = []
        for msg in messages:
            message_ids.append(msg.get("id"))
            message_dicts.append(
                {
                    "id": msg.get("id"),
                    "source_chat_id": msg.get("source_chat_id"),
                    "source_chat_name": msg.get("source_chat_name"),
                    "sender_id": msg.get("sender_id"),
                    "sender_name": msg.get("sender_name"),
                    "text": msg.get("text"),
                    "timestamp": msg.get("timestamp"),
                }
            )

        logger.info(f"Analyzing {len(message_dicts)} messages for user {user_id}")

        # Filter by topics using AI
        relevant_messages = await self.gemini.filter_messages_by_topics(
            message_dicts, topics or []
        )

        if not relevant_messages:
            # Delete all messages immediately (cleanup)
            deleted = self.collector.delete_messages(message_ids)
            logger.info(f"Cleaned up {deleted} messages (none relevant)")

            return {
                "success": True,
                "summary": f"Analyzed {len(message_dicts)} messages. None were relevant to your topics: {', '.join(topics or ['general'])}",
                "message_count": len(message_dicts),
                "topics": topics or [],
                "relevant_count": 0,
            }

        # Summarize relevant messages
        summary = await self.gemini.summarize_messages(relevant_messages, topics or [])

        # Record brief history
        self.collector.record_brief_sent(
            user_id=user_id,
            message_count=len(relevant_messages),
            topics=topics or [],
            summary_preview=summary[:500] if summary else "",
        )

        # DELETE all processed messages immediately (auto-cleanup)
        deleted = self.collector.delete_messages(message_ids)
        logger.info(f"Auto-cleanup: deleted {deleted} messages after brief generation")

        return {
            "success": True,
            "summary": summary,
            "message_count": len(message_dicts),
            "topics": topics or [],
            "relevant_count": len(relevant_messages),
            "relevant_messages": relevant_messages[:10],  # Include sample
        }

    async def generate_brief_content(
        self, user_id: int, topics: Optional[List[str]] = None, timezone: str = "UTC"
    ) -> str:
        """Generate formatted brief content for a user.

        Args:
            user_id: User ID to generate brief for
            topics: Topics to filter by
            timezone: User's timezone for display

        Returns:
            Formatted brief text ready to send
        """
        from zoneinfo import ZoneInfo

        # Get analysis result
        result = await self.analyze_for_user(user_id, topics)

        # Get current time in user's timezone
        tz = ZoneInfo(timezone)
        current_time = datetime.now(tz)

        # Build formatted brief
        lines = [
            f"Your Message Brief",
            f"{current_time.strftime('%A, %B %d, %Y')}",
            f"{current_time.strftime('%I:%M %p %Z')}",
            "",
            "-" * 30,
        ]

        if not result["success"]:
            lines.append(f"\n{result.get('error', 'Unknown error')}")
        elif result["message_count"] == 0:
            lines.append("\nNo new messages since your last brief.")
        else:
            lines.append(f"\n**Stats**")
            lines.append(f"- Total messages: {result['message_count']}")
            lines.append(f"- Relevant to your topics: {result['relevant_count']}")

            if result["topics"]:
                lines.append(f"- Topics: {', '.join(result['topics'])}")

            lines.append("")
            lines.append("-" * 30)
            lines.append("")
            lines.append("**Summary**")
            lines.append("")
            lines.append(result["summary"] or "No summary available.")

        lines.extend(["", "-" * 30, "", "Commands: /topics, /listchats, /status"])

        return "\n".join(lines)


# Singleton instance
_analyzer_instance: Optional[MessageAnalyzer] = None


def get_message_analyzer() -> MessageAnalyzer:
    """Get the global message analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MessageAnalyzer()
    return _analyzer_instance
