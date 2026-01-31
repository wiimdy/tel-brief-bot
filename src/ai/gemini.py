"""Google Gemini AI integration for message analysis."""

import logging
from typing import List, Dict, Any, Optional

import google.generativeai as genai

from src.config import Config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini AI API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key, or None to use config
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self._model = None

        if self.api_key:
            genai.configure(api_key=self.api_key)

    @property
    def model(self):
        """Get or create the Gemini model."""
        if self._model is None:
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    async def generate(self, prompt: str) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Generated text response
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise

    async def filter_messages_by_topics(
        self, messages: List[Dict[str, Any]], topics: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter messages by relevance to topics.

        Args:
            messages: List of message dicts with 'text', 'sender_name', etc.
            topics: List of topics to filter by

        Returns:
            List of relevant messages with 'relevance_score' added
        """
        if not messages:
            return []

        if not topics:
            # No topics = return all messages
            for msg in messages:
                msg["relevance_score"] = 5
                msg["matched_topic"] = "general"
            return messages

        # Prepare messages for analysis
        message_texts = []
        for i, msg in enumerate(messages):
            sender = msg.get("sender_name", "Unknown")
            text = msg.get("text", "")[:500]  # Limit text length
            message_texts.append(f"[{i}] {sender}: {text}")

        prompt = f"""Analyze these Telegram messages and determine which are relevant to these topics: {", ".join(topics)}

For each message, respond with ONLY a JSON array where each element has:
- "index": the message index number
- "relevant": true/false
- "topic": matched topic name or "none"
- "score": relevance score 1-10 (10 = highly relevant)

Messages:
{chr(10).join(message_texts)}

Respond with ONLY valid JSON array, no other text. Example:
[{{"index": 0, "relevant": true, "topic": "web3", "score": 8}}]"""

        try:
            response = await self.generate(prompt)

            # Parse JSON response
            import json

            # Clean up response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response.rsplit("\n", 1)[0]
            response = response.strip()

            results = json.loads(response)

            # Add relevance info to messages
            relevant_messages = []
            for result in results:
                idx = result.get("index", -1)
                if 0 <= idx < len(messages) and result.get("relevant", False):
                    msg = messages[idx].copy()
                    msg["relevance_score"] = result.get("score", 5)
                    msg["matched_topic"] = result.get("topic", "general")
                    relevant_messages.append(msg)

            logger.info(
                f"Filtered {len(relevant_messages)} relevant messages from {len(messages)}"
            )
            return relevant_messages

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            # Return all messages with default score on parse error
            for msg in messages:
                msg["relevance_score"] = 5
                msg["matched_topic"] = "unknown"
            return messages
        except Exception as e:
            logger.error(f"Error filtering messages: {e}")
            return messages

    async def summarize_messages(
        self, messages: List[Dict[str, Any]], topics: List[str], max_length: int = 2000
    ) -> str:
        """Summarize messages into a brief.

        Args:
            messages: List of relevant message dicts
            topics: Topics for context
            max_length: Maximum length of summary

        Returns:
            Formatted summary text
        """
        if not messages:
            return "No relevant messages to summarize."

        # Group messages by topic
        by_topic: Dict[str, List[Dict]] = {}
        for msg in messages:
            topic = msg.get("matched_topic", "general")
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(msg)

        # Prepare message content for summarization
        message_content = []
        for topic, topic_msgs in by_topic.items():
            message_content.append(f"\n=== {topic.upper()} ===")
            for msg in topic_msgs[:20]:  # Limit per topic
                sender = msg.get("sender_name", "Unknown")
                chat = msg.get("source_chat_name", "Chat")
                text = msg.get("text", "")[:300]
                message_content.append(f"[{chat}] {sender}: {text}")

        prompt = f"""You are a helpful assistant creating a briefing summary of Telegram messages.

Topics of interest: {", ".join(topics) if topics else "general"}

Create a concise, well-organized summary of these messages. Include:
1. Key highlights and important information
2. Group by topic when relevant
3. Mention who said what when important
4. Keep it under {max_length} characters

Messages to summarize:
{chr(10).join(message_content)}

Write the summary now (in a friendly, informative tone):"""

        try:
            summary = await self.generate(prompt)

            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[: max_length - 3] + "..."

            return summary

        except Exception as e:
            logger.error(f"Error summarizing messages: {e}")
            # Fallback: simple listing
            fallback = "Summary unavailable. Recent messages:\n\n"
            for msg in messages[:10]:
                sender = msg.get("sender_name", "Unknown")
                text = msg.get("text", "")[:100]
                fallback += f"• {sender}: {text}...\n"
            return fallback


# Singleton instance
_gemini_instance: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get the global Gemini client instance."""
    global _gemini_instance
    if _gemini_instance is None:
        _gemini_instance = GeminiClient()
    return _gemini_instance
