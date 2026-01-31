# Multi-Chat Management Feature

## TL;DR

> **Quick Summary**: Add multi-chat management commands (`/addchat`, `/editchat`, `/listchats`, `/removechat`) with user ownership tracking, allowing users to manage external Telegram chatrooms by ID.
> 
> **Deliverables**:
> - Modified `ChatSettings` model with `added_by_user_id` column
> - 4 new command handlers in `handlers.py`
> - Handler registration in `main.py`
> - Updated `README.md` documentation
> 
> **Estimated Effort**: Medium (4-6 hours)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 (Model) → Task 2 (Handlers) → Task 5 (README)

---

## Context

### Original Request
User wants to add a feature where users can add/edit external Telegram chatroom IDs to receive briefs, not just manage the current chat.

### Interview Summary
**Key Discussions**:
- **Ownership Model**: Add `added_by_user_id` column to track who added each chat
- **Validation**: No bot membership validation (simple, fast approach)
- **Deletion**: Soft delete via `active=false` flag (existing pattern)
- **List Scope**: `/listchats` shows only chats added by the requesting user
- **Testing**: Manual verification only (no test infrastructure)

**Research Findings**:
- Handlers use `async def xxx_command(update, context)` pattern
- DB sessions: `db.get_sync_session()` with try/finally cleanup
- Scheduler integration: `reschedule_chat()` and `unschedule_chat()` functions exist
- ChatSettings has `chat_id` as unique indexed column
- Argument parsing uses `context.args` with `key=value` pattern

---

## Work Objectives

### Core Objective
Enable users to manage multiple external Telegram chatrooms by adding ownership tracking and CRUD commands for chatroom management.

### Concrete Deliverables
1. `src/db/models.py` - ChatSettings model with `added_by_user_id` column
2. `src/bot/handlers.py` - 4 new command handlers
3. `src/main.py` - Handler registration for new commands
4. `README.md` - Documentation for new commands

### Definition of Done
- [ ] `/addchat 123456789` creates a new ChatSettings with caller as owner
- [ ] `/editchat 123456789 timezone=Asia/Seoul` updates only if caller is owner
- [ ] `/listchats` shows only chats owned by the requesting user
- [ ] `/removechat 123456789` soft-deletes only if caller is owner
- [ ] All new commands are documented in README.md

### Must Have
- Ownership check before any edit/remove operation
- Scheduler rescheduling after settings change
- Error messages for unauthorized access attempts
- Consistent emoji formatting with existing handlers

### Must NOT Have (Guardrails)
- NO bot membership validation via Telegram API
- NO hard delete (use `active=false` only)
- NO pagination for `/listchats`
- NO test files or test infrastructure
- NO database migration tooling (Alembic)
- NO admin/superuser permission levels
- NO inline keyboards (keep text commands only)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: NO - Manual verification only
- **Framework**: none

### Manual Verification Approach

Each TODO includes executable verification procedures using the bot directly:

**Verification Method**: 
1. Run bot locally: `python -m src.main`
2. Open Telegram, interact with bot
3. Verify responses match expected behavior
4. Check database state with sqlite3 CLI

**Evidence Requirements**:
- Terminal output from bot startup (no errors)
- Screenshots of Telegram conversation showing command responses
- Database query output confirming data changes

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Add added_by_user_id column to ChatSettings model
└── Task 3: Register new handlers in main.py (skeleton imports)

Wave 2 (After Wave 1):
├── Task 2: Implement all 4 command handlers
└── Task 4: Update existing /start to populate added_by_user_id

Wave 3 (After Wave 2):
└── Task 5: Update README.md with new commands

Critical Path: Task 1 → Task 2 → Task 5
Parallel Speedup: ~30% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 4 | 3 |
| 2 | 1 | 5 | 4 |
| 3 | None | 2 | 1 |
| 4 | 1 | 5 | 2 |
| 5 | 2, 4 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Approach |
|------|-------|---------------------|
| 1 | 1, 3 | Run in parallel - model change + import setup |
| 2 | 2, 4 | Run in parallel - handlers + /start update |
| 3 | 5 | Final documentation task |

---

## TODOs

- [ ] 1. Add `added_by_user_id` column to ChatSettings model

  **What to do**:
  - Add `added_by_user_id = Column(Integer, nullable=True, index=True)` to ChatSettings
  - Column is nullable to support existing rows (backwards compatible)
  - Add index for efficient filtering in `/listchats`
  - Note: No Alembic migration - SQLite will need manual schema update or DB reset

  **Must NOT do**:
  - Do NOT add foreign key constraints (no User table exists)
  - Do NOT use Alembic or create migration files
  - Do NOT make column non-nullable (breaks existing data)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, small change, straightforward model modification
  - **Skills**: None required
    - Simple SQLAlchemy column addition, no specialized knowledge needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 3)
  - **Blocks**: Tasks 2, 4
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `src/db/models.py:18-29` - Existing column definitions in ChatSettings (follow same pattern for new column)

  **API/Type References**:
  - `src/db/models.py:7` - SQLAlchemy Column import (already imported)

  **WHY Each Reference Matters**:
  - Line 18-29 shows exact column definition syntax used in this project (nullable, index, default patterns)

  **Acceptance Criteria**:

  **Automated Verification (using Bash)**:
  ```bash
  # Agent runs:
  python3 -c "from src.db.models import ChatSettings; print([c.name for c in ChatSettings.__table__.columns])"
  # Assert: Output contains 'added_by_user_id'
  
  # Verify column properties:
  python3 -c "from src.db.models import ChatSettings; col = ChatSettings.__table__.c.added_by_user_id; print(f'nullable={col.nullable}, index={col.index}')"
  # Assert: Output is "nullable=True, index=True"
  ```

  **Evidence to Capture**:
  - [ ] Terminal output showing column exists in model
  - [ ] Python verification output showing nullable=True, index=True

  **Commit**: YES
  - Message: `feat(db): add added_by_user_id column for chat ownership tracking`
  - Files: `src/db/models.py`
  - Pre-commit: `python3 -c "from src.db.models import ChatSettings; print('OK')"`

---

- [ ] 2. Implement 4 new command handlers in handlers.py

  **What to do**:
  - Implement `addchat_command`: Create ChatSettings for external chat_id with caller as owner
  - Implement `editchat_command`: Update settings for chat_id (ownership check required)
  - Implement `listchats_command`: List all chats owned by requesting user
  - Implement `removechat_command`: Soft-delete chat_id (set active=false, ownership check)
  - All handlers must call `reschedule_chat()` or `unschedule_chat()` as appropriate
  - Use emoji formatting consistent with existing handlers

  **Must NOT do**:
  - Do NOT validate bot membership via Telegram API
  - Do NOT hard-delete records (use active=false only)
  - Do NOT add pagination to listchats
  - Do NOT use inline keyboards

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple related handlers, requires careful ownership logic, substantial code
  - **Skills**: None required
    - Standard python-telegram-bot patterns already established in codebase

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1 completes)
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1 (needs added_by_user_id column)

  **References**:

  **Pattern References**:
  - `src/bot/handlers.py:18-64` - `start_command` pattern: session management, ChatSettings creation, response formatting
  - `src/bot/handlers.py:67-175` - `settings_command` pattern: argument parsing (`key=value`), validation, update flow, reschedule call
  - `src/bot/handlers.py:178-208` - `status_command` pattern: read-only query, formatted response

  **API/Type References**:
  - `src/bot/scheduler.py:95-117` - `reschedule_chat(application, chat_id)` function signature
  - `src/bot/scheduler.py:120-132` - `unschedule_chat(application, chat_id)` function signature
  - `src/db/models.py:31-51` - `get_brief_times()`, `set_brief_times()`, `get_topics()`, `set_topics()` helpers

  **Documentation References**:
  - Existing handlers use `update.effective_user.id` to get user ID (for added_by_user_id)
  - Existing handlers use `update.effective_chat.id` for current chat (different from target chat_id)

  **WHY Each Reference Matters**:
  - `start_command` shows how to create new ChatSettings with defaults
  - `settings_command` shows argument parsing loop and scheduler integration
  - `reschedule_chat`/`unschedule_chat` must be called after any settings modification

  **Acceptance Criteria**:

  **Automated Verification (using Bash)**:
  ```bash
  # Verify all 4 handlers are defined:
  python3 -c "from src.bot.handlers import addchat_command, editchat_command, listchats_command, removechat_command; print('All handlers imported successfully')"
  # Assert: Output is "All handlers imported successfully"
  
  # Verify handler signatures are correct:
  python3 -c "
  import inspect
  from src.bot.handlers import addchat_command
  sig = inspect.signature(addchat_command)
  params = list(sig.parameters.keys())
  print(f'Parameters: {params}')
  "
  # Assert: Parameters include 'update' and 'context'
  ```

  **Manual Verification via Bot**:
  1. Start bot: `python -m src.main`
  2. In Telegram, send `/addchat 123456789`
     - Expected: Success message with chat settings created
  3. Send `/listchats`
     - Expected: Shows chat 123456789 in list
  4. Send `/editchat 123456789 timezone=Asia/Seoul`
     - Expected: Success message, settings updated
  5. Send `/removechat 123456789`
     - Expected: Success message, chat deactivated
  6. Send `/listchats`
     - Expected: Chat no longer shown (inactive)

  **Evidence to Capture**:
  - [ ] Terminal output from handler import verification
  - [ ] Screenshot of Telegram showing each command response

  **Commit**: YES
  - Message: `feat(bot): add multi-chat management commands (addchat, editchat, listchats, removechat)`
  - Files: `src/bot/handlers.py`
  - Pre-commit: `python3 -c "from src.bot.handlers import addchat_command, editchat_command, listchats_command, removechat_command; print('OK')"`

---

- [ ] 3. Register new handlers in main.py

  **What to do**:
  - Add imports for 4 new handlers from handlers.py
  - Register each handler with `application.add_handler(CommandHandler(...))`
  - Place registrations after existing handler registrations (lines 87-90)

  **Must NOT do**:
  - Do NOT change existing handler registrations
  - Do NOT modify post_init or post_shutdown functions

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple import + 4 lines of registration, follows existing pattern exactly
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: None directly (but Task 2 needs handlers to exist)
  - **Blocked By**: None (can prepare imports even before handlers exist)

  **References**:

  **Pattern References**:
  - `src/main.py:11-16` - Existing handler imports (follow same pattern)
  - `src/main.py:85-90` - Existing handler registration (follow same pattern)

  **WHY Each Reference Matters**:
  - Lines 11-16 show exact import syntax: `from src.bot.handlers import (...)`
  - Lines 85-90 show registration: `application.add_handler(CommandHandler("name", handler_function))`

  **Acceptance Criteria**:

  **Automated Verification (using Bash)**:
  ```bash
  # Verify imports are present:
  grep -c "addchat_command\|editchat_command\|listchats_command\|removechat_command" src/main.py
  # Assert: Output is 8 (4 imports + 4 registrations)
  
  # Verify bot starts without errors:
  timeout 5 python -m src.main 2>&1 | head -20 || true
  # Assert: Shows "Registering command handlers..." without import errors
  ```

  **Evidence to Capture**:
  - [ ] grep output showing all 4 handlers referenced
  - [ ] Bot startup log showing no import errors

  **Commit**: NO (groups with Task 2)
  - Will be committed together with Task 2 handlers

---

- [ ] 4. Update `/start` command to populate `added_by_user_id`

  **What to do**:
  - Modify `start_command` to set `added_by_user_id = update.effective_user.id` when creating new ChatSettings
  - This ensures chats created via `/start` are owned by the initiating user
  - Backwards compatible: existing records will have `added_by_user_id = None`

  **Must NOT do**:
  - Do NOT update existing records (migration)
  - Do NOT change any other behavior of /start

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single line addition to existing function
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1 completes)
  - **Parallel Group**: Wave 2 (with Task 2)
  - **Blocks**: Task 5 (docs)
  - **Blocked By**: Task 1 (needs column to exist)

  **References**:

  **Pattern References**:
  - `src/bot/handlers.py:32-38` - ChatSettings creation in start_command (add added_by_user_id here)
  - `src/bot/handlers.py:20-21` - How to get user ID: `update.effective_user.id`

  **WHY Each Reference Matters**:
  - Lines 32-38 show the exact ChatSettings constructor call to modify
  - Line 20-21 shows `update.effective_user` pattern already used for logging

  **Acceptance Criteria**:

  **Automated Verification (using Bash)**:
  ```bash
  # Verify added_by_user_id is set in start_command:
  grep -A5 "chat_settings = ChatSettings(" src/bot/handlers.py | grep "added_by_user_id"
  # Assert: Output shows added_by_user_id assignment
  ```

  **Manual Verification**:
  1. Delete existing `briefbot.db` to start fresh
  2. Run bot: `python -m src.main`
  3. Send `/start` in Telegram
  4. Check database:
     ```bash
     sqlite3 briefbot.db "SELECT chat_id, added_by_user_id FROM chat_settings"
     ```
  5. Expected: Row shows non-null added_by_user_id matching your Telegram user ID

  **Evidence to Capture**:
  - [ ] grep output showing added_by_user_id in ChatSettings creation
  - [ ] sqlite3 query output showing populated owner field

  **Commit**: NO (groups with Task 2)
  - Will be committed together with Task 2 handlers

---

- [ ] 5. Update README.md with new commands documentation

  **What to do**:
  - Add new commands to "Bot Commands" table (lines 90-95)
  - Add new section "Multi-Chat Management" with usage examples
  - Update architecture description if needed
  - Add to "Features" section: multi-chat management capability

  **Must NOT do**:
  - Do NOT remove or modify existing command documentation
  - Do NOT change environment variables section
  - Do NOT add test documentation (no tests in this feature)

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation task, needs clear technical writing
  - **Skills**: None required

  **Parallelization**:
  - **Can Run In Parallel**: NO (final task)
  - **Parallel Group**: Wave 3 (sequential, after Wave 2)
  - **Blocks**: None (final deliverable)
  - **Blocked By**: Tasks 2, 4 (needs handlers finalized to document accurately)

  **References**:

  **Pattern References**:
  - `README.md:88-95` - Existing "Bot Commands" table format
  - `README.md:97-112` - Existing "Configuration Examples" format

  **WHY Each Reference Matters**:
  - Lines 88-95 show exact markdown table format for commands
  - Lines 97-112 show code block format for examples

  **Acceptance Criteria**:

  **Automated Verification (using Bash)**:
  ```bash
  # Verify new commands are documented:
  grep -c "addchat\|editchat\|listchats\|removechat" README.md
  # Assert: Output is >= 4 (at least one mention per command)
  
  # Verify table format preserved:
  grep -c "| Command | Description |" README.md
  # Assert: Output is 1 (table header still exists)
  ```

  **Content to Include**:

  **New rows for Bot Commands table**:
  ```
  | `/addchat <chat_id>` | Add external chatroom to receive briefs | `/addchat -123456789` |
  | `/editchat <chat_id>` | Edit settings for a specific chatroom | `/editchat -123456789 timezone=UTC` |
  | `/listchats` | List all chatrooms you manage | `/listchats` |
  | `/removechat <chat_id>` | Remove a chatroom (soft delete) | `/removechat -123456789` |
  ```

  **New section after "Configuration Examples"**:
  ```markdown
  ### Multi-Chat Management
  
  Manage multiple chatrooms from a single conversation:
  
  **Add a new chatroom:**
  ```
  /addchat -123456789
  ```
  
  **Configure the chatroom:**
  ```
  /editchat -123456789 timezone=Asia/Seoul times=09:00,21:00 topics=news
  ```
  
  **View all your managed chatrooms:**
  ```
  /listchats
  ```
  
  **Remove a chatroom:**
  ```
  /removechat -123456789
  ```
  
  > **Note**: You can only edit/remove chatrooms you added. The chat_id can be obtained from Telegram or by forwarding a message from the target chat to @userinfobot.
  ```

  **Evidence to Capture**:
  - [ ] grep output showing all 4 new commands in README
  - [ ] Visual review of README formatting

  **Commit**: YES
  - Message: `docs: add multi-chat management commands to README`
  - Files: `README.md`
  - Pre-commit: `grep -q "addchat" README.md && echo "OK"`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(db): add added_by_user_id column for chat ownership tracking` | src/db/models.py | python import check |
| 2+3+4 | `feat(bot): add multi-chat management commands (addchat, editchat, listchats, removechat)` | src/bot/handlers.py, src/main.py | python import check |
| 5 | `docs: add multi-chat management commands to README` | README.md | grep check |

---

## Success Criteria

### Verification Commands
```bash
# 1. Verify model has new column:
python3 -c "from src.db.models import ChatSettings; print('added_by_user_id' in [c.name for c in ChatSettings.__table__.columns])"
# Expected: True

# 2. Verify all handlers importable:
python3 -c "from src.bot.handlers import addchat_command, editchat_command, listchats_command, removechat_command; print('OK')"
# Expected: OK

# 3. Verify bot starts:
timeout 5 python -m src.main 2>&1 | grep -i error || echo "No errors"
# Expected: No errors

# 4. Verify README updated:
grep -c "/addchat\|/editchat\|/listchats\|/removechat" README.md
# Expected: >= 4
```

### Final Checklist
- [ ] All "Must Have" features present
- [ ] All "Must NOT Have" guardrails respected
- [ ] All 4 commands functional via Telegram
- [ ] Ownership checks enforced on edit/remove
- [ ] Scheduler updated on settings changes
- [ ] README documentation complete
