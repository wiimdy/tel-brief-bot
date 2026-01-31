# Draft: Multi-Chat Management Feature

## Requirements (confirmed)
- Users can ADD new chatroom IDs to receive briefs
- Users can EDIT settings for specific chatroom IDs  
- Users can LIST all registered chatrooms
- Users can REMOVE chatrooms

## Technical Decisions
- (pending discussion)

## Research Findings

### Current Codebase Patterns (from explore agents)

**handlers.py Patterns:**
- All handlers: `async def xxx_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None`
- DB session: `session: Session = db.get_sync_session()` with try/finally for cleanup
- Argument parsing: `context.args` list, parsed with `key=value` pattern using `arg.split("=", 1)`
- Error handling: try/except with logger.error and user-facing error messages (❌ prefix)
- Response formatting: Multi-line f-strings with emoji decorations (⏰🌍📌✅)

**Database Patterns:**
- `ChatSettings` model: `chat_id` is UNIQUE and INDEXED
- JSON storage for arrays via Text columns with getter/setter helpers
- Global `db` instance: `from src.db.database import db`
- Session lifecycle: `get_sync_session()` → operations → `session.close()` in finally

**Scheduler Patterns:**
- `reschedule_chat(application, chat_id)` - updates jobs after settings change
- `unschedule_chat(application, chat_id)` - removes all jobs for a chat
- Jobs named as `brief_{chat_id}_{time}` for identification

**main.py Handler Registration:**
```python
from src.bot.handlers import start_command, settings_command, ...
application.add_handler(CommandHandler("start", start_command))
```

**Current CRUD Operations:**
- CREATE: `/start` checks existence, creates if missing
- READ: `session.query(ChatSettings).filter_by(chat_id=chat_id).first()`
- UPDATE: `/settings` parses args, updates model, commits
- DELETE: No hard delete - uses `active` flag for soft deactivation

### Key Technical Considerations

1. **chat_id Uniqueness**: Enforced at DB level (`unique=True`) and app level (check before insert)
2. **No User Ownership**: Current model has NO `owner_id` or `added_by` field
3. **Scheduler Integration**: Any setting change must call `reschedule_chat()` 

### Proposed New Commands
1. `/addchat <chat_id>` - Add a new chatroom by ID
2. `/editchat <chat_id> timezone=X times=X topics=X` - Edit specific chatroom
3. `/listchats` - List all registered chatrooms
4. `/removechat <chat_id>` - Remove a chatroom

## Open Questions - RESOLVED

1. **Ownership Model**: ✅ ADD ownership tracking (`added_by_user_id` column)
2. **Bot Membership Validation**: ✅ NO validation (simple, fast)
3. **Duplicate chat_id**: Follows from uniqueness - error if exists, but ownership check applies
4. **List Scope**: ✅ Show only chats added by requesting user
5. **Deletion Strategy**: ✅ Soft delete (`active=false`)
6. **Permission checks**: ✅ Only owner can edit/remove their chats

## Scope Boundaries

### INCLUDE
- New `added_by_user_id` column in ChatSettings model
- `/addchat <chat_id>` command handler
- `/editchat <chat_id> timezone=X times=X topics=X` command handler
- `/listchats` command handler (user's chats only)
- `/removechat <chat_id>` command handler (soft delete)
- Handler registration in main.py
- README.md update with new commands

### EXCLUDE
- Database migration tooling (Alembic) - manual schema update
- Bot membership validation via Telegram API
- Test infrastructure setup
- Admin/superuser permissions
- Pagination for /listchats
