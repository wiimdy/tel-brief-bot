# Message Briefing Feature

## TL;DR

> **Quick Summary**: Add AI-powered message briefing that collects messages from user's Telegram chats via Telethon, filters by topics using Gemini AI, and sends summarized briefs at scheduled times.
> 
> **Deliverables**:
> - Telethon userbot client for message collection
> - Gemini AI integration for filtering/summarization
> - Message storage model
> - Modified briefing system with AI summaries
> - New /topics command
> 
> **Estimated Effort**: Large (8-12 hours)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (deps) → Task 2 (model) → Task 4 (collector) → Task 6 (briefing) → Task 8 (integration)

---

## Work Objectives

### Core Objective
Enable automated collection and AI-summarization of Telegram messages from user's chatrooms, delivering topic-filtered briefs at scheduled times.

### Concrete Deliverables
1. `src/userbot/client.py` - Telethon client wrapper
2. `src/userbot/collector.py` - Message collection logic
3. `src/ai/gemini.py` - Gemini API integration
4. `src/ai/analyzer.py` - Topic filtering + summarization
5. Modified `src/db/models.py` - Message model
6. Modified `src/bot/briefing.py` - AI-generated summaries
7. Modified `src/main.py` - Concurrent userbot + bot
8. New `/topics` command handler

### Definition of Done
- [ ] Userbot connects with user's Telegram account
- [ ] Messages collected periodically (every 5 min)
- [ ] Gemini filters messages by topics
- [ ] Briefs contain AI-generated summaries
- [ ] Messages cleared after brief sent

### Must NOT Have (Guardrails)
- NO hardcoded API credentials
- NO session files in git
- NO exceeding Gemini free tier (15 RPM)
- NO real-time collection (use periodic)
- NO storing messages indefinitely

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Update requirements.txt + config.py
└── Task 2: Add Message model to database

Wave 2 (After Wave 1):
├── Task 3: Create Telethon client wrapper
├── Task 4: Create message collector
└── Task 5: Create Gemini AI integration

Wave 3 (After Wave 2):
├── Task 6: Update briefing.py with AI summaries
├── Task 7: Add /topics command
└── Task 8: Integrate userbot in main.py

Wave 4 (After Wave 3):
└── Task 9: Update README + .env.example
```

---

## TODOs

- [ ] 1. Update requirements.txt and config.py

  **What to do**:
  - Add `telethon>=2.0.0a0` to requirements.txt
  - Add `google-generativeai>=0.3.0` to requirements.txt
  - Add new config variables for Telegram API and Gemini

  **Files**: `requirements.txt`, `src/config.py`
  
  **New Config Variables**:
  ```python
  TELEGRAM_API_ID: int
  TELEGRAM_API_HASH: str
  TELEGRAM_PHONE: str
  GEMINI_API_KEY: str
  BRIEF_RECIPIENT_ID: int  # User's chat ID for receiving briefs
  COLLECTION_INTERVAL: int = 300  # 5 minutes
  ```

---

- [ ] 2. Add Message model to database

  **What to do**:
  - Create CollectedMessage model for temporary message storage
  - Fields: id, source_chat_id, sender_name, text, timestamp, processed
  - Add index on source_chat_id and processed

  **File**: `src/db/models.py`
  
  **Schema**:
  ```python
  class CollectedMessage(Base):
      __tablename__ = "collected_messages"
      
      id = Column(Integer, primary_key=True)
      source_chat_id = Column(Integer, nullable=False, index=True)
      sender_name = Column(String(255))
      text = Column(Text)
      timestamp = Column(DateTime, nullable=False)
      processed = Column(Boolean, default=False, index=True)
      created_at = Column(DateTime, default=datetime.utcnow)
  ```

---

- [ ] 3. Create Telethon client wrapper

  **What to do**:
  - Create `src/userbot/__init__.py`
  - Create `src/userbot/client.py` with TelethonClient class
  - Handle session management and authentication
  - Provide methods: connect(), disconnect(), get_messages()

  **File**: `src/userbot/client.py`
  
  **Key Methods**:
  ```python
  class TelethonClient:
      async def connect(self) -> bool
      async def disconnect(self)
      async def get_messages(self, chat_id: int, since: datetime) -> List[Message]
      async def is_connected(self) -> bool
  ```

---

- [ ] 4. Create message collector

  **What to do**:
  - Create `src/userbot/collector.py`
  - Periodic collection from all monitored chats
  - Store messages in database
  - Track last collection time per chat

  **File**: `src/userbot/collector.py`
  
  **Key Functions**:
  ```python
  async def collect_messages(client: TelethonClient, chat_ids: List[int]) -> int
  async def get_unprocessed_messages(chat_id: int) -> List[CollectedMessage]
  async def mark_messages_processed(message_ids: List[int])
  async def clear_old_messages()
  ```

---

- [ ] 5. Create Gemini AI integration

  **What to do**:
  - Create `src/ai/__init__.py`
  - Create `src/ai/gemini.py` with GeminiClient class
  - Create `src/ai/analyzer.py` with message analysis logic
  - Implement topic filtering and summarization prompts

  **Files**: `src/ai/gemini.py`, `src/ai/analyzer.py`
  
  **GeminiClient Methods**:
  ```python
  class GeminiClient:
      async def filter_by_topics(self, messages: List[str], topics: List[str]) -> List[dict]
      async def summarize_messages(self, messages: List[str], topics: List[str]) -> str
  ```
  
  **Prompts**:
  ```
  FILTER_PROMPT = """
  You are analyzing Telegram messages. Filter and return only messages relevant to these topics: {topics}
  
  For each message, respond with JSON:
  {"relevant": true/false, "topic": "matched_topic", "importance": 1-10}
  
  Messages:
  {messages}
  """
  
  SUMMARIZE_PROMPT = """
  Summarize these Telegram messages about {topics}.
  Group by topic. Highlight key information.
  Be concise but informative. Use bullet points.
  
  Messages:
  {messages}
  """
  ```

---

- [ ] 6. Update briefing.py with AI summaries

  **What to do**:
  - Modify `generate_brief()` to use AI summarization
  - Fetch unprocessed messages from database
  - Call Gemini for filtering and summarization
  - Format brief with AI-generated content
  - Mark messages as processed after brief sent

  **File**: `src/bot/briefing.py`
  
  **New Flow**:
  ```python
  async def generate_brief(chat_settings):
      # 1. Get monitored chat IDs from user's settings
      # 2. Fetch unprocessed messages for those chats
      # 3. If no messages, return "No new messages"
      # 4. Call Gemini to filter by topics
      # 5. Call Gemini to summarize relevant messages
      # 6. Format brief with summary
      # 7. Mark messages as processed
      return formatted_brief
  ```

---

- [ ] 7. Add /topics command handler

  **What to do**:
  - Add `topics_command` handler to handlers.py
  - Show current topics with `/topics`
  - Set topics with `/topics web3,security,ai`
  - Store in ChatSettings.topics (already exists)

  **File**: `src/bot/handlers.py`
  
  **Usage**:
  ```
  /topics              - View current topics
  /topics web3,ai,security - Set topics
  ```

---

- [ ] 8. Integrate userbot in main.py

  **What to do**:
  - Import and initialize TelethonClient
  - Start periodic collection task
  - Run userbot and bot concurrently with asyncio.gather()
  - Handle graceful shutdown for both

  **File**: `src/main.py`
  
  **Integration Pattern**:
  ```python
  async def start_collection_loop():
      while True:
          await collect_messages(...)
          await asyncio.sleep(COLLECTION_INTERVAL)
  
  async def main():
      await asyncio.gather(
          application.run_polling(),
          userbot.run_until_disconnected(),
          start_collection_loop()
      )
  ```

---

- [ ] 9. Update README and .env.example

  **What to do**:
  - Add Telegram API credentials section
  - Document my.telegram.org setup process
  - Add Gemini API key section
  - Update commands table with /topics
  - Add message briefing feature description

  **Files**: `README.md`, `.env.example`
  
  **New .env variables**:
  ```env
  # Telegram User API (from my.telegram.org)
  TELEGRAM_API_ID=12345678
  TELEGRAM_API_HASH=your_api_hash
  TELEGRAM_PHONE=+1234567890
  
  # Google Gemini API
  GEMINI_API_KEY=your_gemini_key
  
  # Brief recipient (your Telegram user ID)
  BRIEF_RECIPIENT_ID=123456789
  
  # Collection settings
  COLLECTION_INTERVAL=300
  ```

---

## Commit Strategy

| After Task | Message | Files |
|------------|---------|-------|
| 1 | `chore: add telethon and gemini dependencies` | requirements.txt, config.py |
| 2 | `feat(db): add CollectedMessage model` | models.py |
| 3-4 | `feat(userbot): add Telethon client and collector` | userbot/*.py |
| 5 | `feat(ai): add Gemini integration for message analysis` | ai/*.py |
| 6-7 | `feat(bot): integrate AI briefing and add /topics command` | briefing.py, handlers.py |
| 8 | `feat: integrate userbot with main application` | main.py |
| 9 | `docs: add message briefing setup instructions` | README.md, .env.example |

---

## Success Criteria

### Verification Commands
```bash
# 1. Dependencies installed
pip install -r requirements.txt

# 2. Models importable
python3 -c "from src.db.models import CollectedMessage; print('OK')"

# 3. Userbot importable
python3 -c "from src.userbot.client import TelethonClient; print('OK')"

# 4. AI importable
python3 -c "from src.ai.gemini import GeminiClient; print('OK')"

# 5. Bot starts without errors
timeout 10 python -m src.main 2>&1 | head -20
```

### Manual Verification
1. Run bot with valid credentials
2. Send `/topics web3,ai,security`
3. Wait for scheduled brief time
4. Verify brief contains AI-generated summary of relevant messages
