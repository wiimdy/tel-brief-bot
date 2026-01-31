# Telegram Brief Bot 🤖

A Telegram bot that sends scheduled briefings at user-configured times with timezone support. Perfect for daily updates, news digests, and personalized notifications.

## Features ✨

- **📅 Timezone-Aware Scheduling**: Configure briefs in your local timezone with automatic DST handling
- **⏰ Multiple Daily Briefs**: Set multiple brief times (e.g., 09:00, 15:00, 21:00)
- **📌 Custom Topics**: Configure topics of interest for personalized content
- **👥 Multi-User Support**: Each chat has independent settings
- **🔗 Multi-Chat Management**: Add and manage multiple external chatrooms by ID
- **💾 Persistent Storage**: SQLite (default) or PostgreSQL for production
- **🐳 Docker Ready**: Easy deployment with Docker and docker-compose
- **🔄 Auto-Rescheduling**: Settings changes instantly update scheduled jobs

## Architecture

```
tel-brief-bot/
├── src/
│   ├── bot/
│   │   ├── handlers.py      # Command handlers (/start, /settings, etc.)
│   │   ├── scheduler.py     # APScheduler timezone-aware scheduling
│   │   └── briefing.py      # Brief generation logic
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models (ChatSettings)
│   │   └── database.py      # Database connection management
│   ├── config.py            # Environment configuration
│   └── main.py              # Entry point
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick Start 🚀

### 1. Get a Telegram Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy your bot token

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your bot token
nano .env
```

Update `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DEFAULT_TIMEZONE=Asia/Seoul
DEFAULT_BRIEF_TIMES=15:00,21:00
```

### 3. Run with Docker (Recommended)

```bash
# Build and start the bot
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop the bot
docker-compose down
```

### 4. Run Locally (Development)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python -m src.main
```

## Usage 💬

### Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot for your chat | `/start` |
| `/settings` | Configure timezone, times, and topics | `/settings timezone=Asia/Seoul times=15:00,21:00 topics=tech,news` |
| `/status` | View current configuration | `/status` |
| `/test` | Send test brief immediately | `/test` |
| `/addchat` | Add external chatroom to receive briefs | `/addchat -123456789` |
| `/editchat` | Edit settings for a specific chatroom | `/editchat -123456789 timezone=UTC` |
| `/listchats` | List all chatrooms you manage | `/listchats` |
| `/removechat` | Remove a chatroom (soft delete) | `/removechat -123456789` |

### Configuration Examples

**Set timezone and brief times:**
```
/settings timezone=America/New_York times=09:00,21:00
```

**Add topics:**
```
/settings topics=technology,news,weather
```

**Full configuration:**
```
/settings timezone=Europe/London times=08:00,12:00,18:00 topics=tech,finance
```

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

> **Note**: You can only edit/remove chatrooms you added. Get the chat_id by forwarding a message from the target chat to [@userinfobot](https://t.me/userinfobot).

## Supported Timezones 🌍

The bot supports all IANA timezone strings. Common examples:

- `UTC`
- `America/New_York`
- `Europe/London`
- `Asia/Tokyo`
- `Asia/Seoul`
- `Australia/Sydney`

[Full timezone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

## Environment Variables 🔧

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | **Required**. Your Telegram bot token | - |
| `DATABASE_URL` | Database connection string | `sqlite:///briefbot.db` |
| `DEFAULT_TIMEZONE` | Default timezone for new chats | `UTC` |
| `DEFAULT_BRIEF_TIMES` | Default brief times (comma-separated) | `09:00,18:00` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `SQL_DEBUG` | Enable SQL query logging | `false` |

## Database Options 💾

### SQLite (Default)

Perfect for single-instance deployments:
```env
DATABASE_URL=sqlite:///briefbot.db
```

### PostgreSQL (Production)

For high-concurrency and multiple instances:

1. Uncomment PostgreSQL service in `docker-compose.yml`
2. Update `.env`:
```env
DATABASE_URL=postgresql://briefbot:changeme@db:5432/briefbot
```

## Extending Brief Content 📰

The brief generation logic is in `src/bot/briefing.py`. Current implementation is a placeholder. You can extend it to:

- **Fetch news from APIs**: NewsAPI, RSS feeds
- **Generate AI summaries**: OpenAI, Claude, local LLMs
- **Pull weather data**: OpenWeatherMap
- **Aggregate crypto/stock prices**: CoinGecko, Alpha Vantage
- **Summarize chat messages**: Analyze chat history

Example integration:
```python
# src/bot/briefing.py

async def generate_brief(chat_settings: ChatSettings) -> str:
    topics = chat_settings.get_topics()
    brief_parts = []
    
    for topic in topics:
        if topic == "news":
            # Fetch news from API
            news_items = await fetch_news()
            brief_parts.append(format_news(news_items))
        elif topic == "weather":
            weather_data = await fetch_weather()
            brief_parts.append(format_weather(weather_data))
    
    return "\n\n".join(brief_parts)
```

## Development 🛠️

### Project Structure

- **`src/main.py`**: Application entry point
- **`src/config.py`**: Configuration management
- **`src/db/`**: Database models and connections
- **`src/bot/handlers.py`**: Command handlers
- **`src/bot/scheduler.py`**: Job scheduling logic
- **`src/bot/briefing.py`**: Brief content generation

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests (when implemented)
pytest tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

## Deployment 🌐

### Docker Compose (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.yml up -d

# With PostgreSQL
# 1. Uncomment PostgreSQL service in docker-compose.yml
# 2. Update DATABASE_URL in .env
docker-compose up -d
```

### Systemd Service (Linux)

Create `/etc/systemd/system/briefbot.service`:
```ini
[Unit]
Description=Telegram Brief Bot
After=network.target

[Service]
Type=simple
User=briefbot
WorkingDirectory=/opt/tel-brief-bot
Environment="PATH=/opt/tel-brief-bot/venv/bin"
ExecStart=/opt/tel-brief-bot/venv/bin/python -m src.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable briefbot
sudo systemctl start briefbot
sudo systemctl status briefbot
```

## Troubleshooting 🔍

### Bot not responding

1. Check bot token is correct in `.env`
2. Verify bot is running: `docker-compose logs bot`
3. Check Telegram API is accessible

### Briefs not sending at scheduled time

1. Verify timezone is correct: `/status`
2. Check scheduler logs for errors
3. Ensure chat is active in database

### Database errors

```bash
# Reset database (WARNING: deletes all data)
rm briefbot.db
# Restart bot to recreate tables
docker-compose restart bot
```

## Future Enhancements 🚀

Planned features:

- [ ] Web admin dashboard
- [ ] Brief templates and customization
- [ ] Integration with news APIs
- [ ] AI-powered content summarization
- [ ] User authentication for multi-user server
- [ ] Inline keyboard for settings
- [ ] Brief history and archives
- [ ] Analytics and usage metrics

## Contributing 🤝

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License 📄

MIT License - feel free to use this project for personal or commercial purposes.

## Support 💪

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `docker-compose logs bot`
3. Open an issue on GitHub

---

**Built with:**
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v20.7
- [APScheduler](https://github.com/agronholm/apscheduler) v3.10.4
- [SQLAlchemy](https://www.sqlalchemy.org/) v2.0.25

**Happy briefing! 📬**
