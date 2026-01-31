# Telegram Brief Bot

A Telegram bot that sends scheduled briefings with AI-powered message summarization. Collects messages from your Telegram chats, filters by topics you care about (web3, AI, security, etc.), and delivers intelligent summaries at your preferred times.

## Features

- **AI-Powered Briefings**: Uses Google Gemini to analyze and summarize messages from your Telegram chats
- **Topic Filtering**: AI filters messages based on your interests (web3, ai, security, crypto, etc.)
- **Timezone-Aware Scheduling**: Configure briefs in your local timezone with automatic DST handling
- **Multiple Daily Briefs**: Set multiple brief times (e.g., 09:00, 15:00, 21:00)
- **Multi-Chat Monitoring**: Monitor multiple channels/groups and get aggregated briefs
- **Supabase Database**: Free cloud database with auto-cleanup after briefs
- **Auto-Cleanup**: Messages are deleted after each brief to save storage
- **Docker Ready**: Easy deployment with Docker and docker-compose

## Architecture

```
tel-brief-bot/
├── src/
│   ├── bot/
│   │   ├── handlers.py      # Command handlers (/start, /topics, etc.)
│   │   ├── scheduler.py     # APScheduler timezone-aware scheduling
│   │   └── briefing.py      # Brief generation with AI
│   ├── db/
│   │   ├── supabase_client.py  # Supabase client wrapper
│   │   └── models.py           # Legacy SQLAlchemy models
│   ├── userbot/             # Telegram User API (Telethon)
│   │   ├── client.py        # Telethon wrapper
│   │   ├── collector.py     # Message collection
│   │   └── auth.py          # Authentication script
│   ├── ai/                  # AI analysis
│   │   ├── gemini.py        # Google Gemini client
│   │   └── analyzer.py      # Message analysis
│   ├── config.py            # Environment configuration
│   └── main.py              # Entry point
├── sessions/                # Telethon session files
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick Start

### 1. Get Required Credentials

**Telegram Bot Token:**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy your bot token

**Telegram User API (for message collection):**
1. Go to [my.telegram.org/apps](https://my.telegram.org/apps)
2. Log in with your phone number
3. Create a new application
4. Note the `api_id` and `api_hash`

**Google Gemini API:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Copy the API key

**Your Telegram User ID:**
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Note your user ID number

**Supabase Database:**
1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project
3. Go to Settings -> API and copy the URL and anon key
4. Go to SQL Editor and run the table creation SQL (see below)

### 2. Create Supabase Tables

Run this SQL in your Supabase SQL Editor:

```sql
-- Chat Settings Table
CREATE TABLE chat_settings (
  id BIGSERIAL PRIMARY KEY,
  chat_id BIGINT UNIQUE NOT NULL,
  added_by_user_id BIGINT,
  timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
  brief_times JSONB NOT NULL DEFAULT '["09:00", "18:00"]',
  topics JSONB NOT NULL DEFAULT '[]',
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Collected Messages Table (temporary storage)
CREATE TABLE collected_messages (
  id BIGSERIAL PRIMARY KEY,
  source_chat_id BIGINT NOT NULL,
  source_chat_name VARCHAR(255),
  sender_id BIGINT,
  sender_name VARCHAR(255),
  message_id BIGINT NOT NULL,
  text TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  processed BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Brief History Table
CREATE TABLE brief_history (
  id BIGSERIAL PRIMARY KEY,
  recipient_id BIGINT NOT NULL,
  brief_time TIMESTAMPTZ NOT NULL,
  message_count INTEGER DEFAULT 0,
  topics_covered JSONB,
  summary_preview TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chat_settings_chat_id ON chat_settings(chat_id);
CREATE INDEX idx_collected_messages_processed ON collected_messages(processed);
CREATE INDEX idx_brief_history_recipient ON brief_history(recipient_id);
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env
```

Update `.env` with your credentials:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here

# For AI briefings (optional but recommended)
ENABLE_MESSAGE_COLLECTION=true
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+1234567890
GEMINI_API_KEY=your_gemini_api_key_here
BRIEF_RECIPIENT_ID=123456789

# Preferences
DEFAULT_TIMEZONE=Asia/Seoul
DEFAULT_BRIEF_TIMES=09:00,18:00
```

### 3. Authenticate Telegram User API

Before running the bot, authenticate your Telegram account:

```bash
# Install dependencies
pip install -r requirements.txt

# Run authentication
python -m src.userbot.auth
```

Enter the verification code sent to your Telegram app. This creates a session file so the bot can access your messages.

### 4. Run the Bot

**With Docker (Recommended):**
```bash
docker-compose up -d
docker-compose logs -f bot
```

**Locally:**
```bash
python -m src.main
```

### 5. Configure Your Briefs

In Telegram, chat with your bot:

```
/start                           # Initialize
/addchat @cryptonews             # Add a channel to monitor
/addchat -1001234567890          # Add by chat ID
/topics web3,ai,security,crypto  # Set your interests
/test                            # Get a sample brief
```

## Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot | `/start` |
| `/topics` | View or set topic filters | `/topics web3,ai,security` |
| `/settings` | Configure timezone and times | `/settings timezone=Asia/Seoul times=09:00,21:00` |
| `/status` | View current configuration | `/status` |
| `/test` | Send test brief immediately | `/test` |
| `/addchat` | Add chatroom to monitor | `/addchat @channel` or `/addchat -123456` |
| `/editchat` | Edit chatroom settings | `/editchat @channel timezone=UTC` |
| `/listchats` | List monitored chatrooms | `/listchats` |
| `/removechat` | Stop monitoring a chatroom | `/removechat @channel` |

## How It Works

1. **Message Collection**: Every 5 minutes (configurable), the bot collects messages from your monitored chats using the Telegram User API (Telethon).

2. **AI Analysis**: At scheduled brief times, Gemini AI:
   - Filters messages relevant to your topics
   - Summarizes important discussions
   - Groups by topic/chat

3. **Brief Delivery**: The bot sends a formatted brief to you with:
   - Message statistics
   - Topic-filtered summaries
   - Source attribution

## Example Brief

```
Your Message Brief
Friday, January 31, 2025
09:00 AM KST
------------------------------

Stats
- Total messages: 142
- Relevant to your topics: 23
- Topics: web3, ai, security

------------------------------

Summary

Web3 & Crypto:
- @CryptoAlerts: Bitcoin broke $100k, discussion of ETF inflows
- @DeFiNews: New L2 launch with improved gas efficiency

AI & Technology:
- @TechNews: OpenAI released new model, benchmarks discussed
- @AIResearch: Paper on efficient fine-tuning methods

Security:
- @SecurityAlerts: New vulnerability in popular library, patch available

------------------------------

Commands: /topics, /listchats, /status
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | **Required**. Bot token from @BotFather | - |
| `SUPABASE_URL` | **Required**. Your Supabase project URL | - |
| `SUPABASE_KEY` | **Required**. Your Supabase anon/public key | - |
| `DEFAULT_TIMEZONE` | Default timezone for new chats | `UTC` |
| `DEFAULT_BRIEF_TIMES` | Default brief times | `09:00,18:00` |
| `ENABLE_MESSAGE_COLLECTION` | Enable AI briefings | `false` |
| `TELEGRAM_API_ID` | Telegram API ID | - |
| `TELEGRAM_API_HASH` | Telegram API Hash | - |
| `TELEGRAM_PHONE` | Your phone number | - |
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `GEMINI_MODEL` | Gemini model to use | `gemini-1.5-flash` |
| `BRIEF_RECIPIENT_ID` | Your Telegram user ID | - |
| `COLLECTION_INTERVAL` | Message collection interval (seconds) | `300` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Database

This bot uses **Supabase** (PostgreSQL) as the primary database.

**Why Supabase?**
- Free tier: 500MB storage, unlimited API requests
- Web dashboard to view/edit data
- Automatic backups
- No server management needed

**Auto-Cleanup:** Messages are automatically deleted after each brief is generated, keeping storage minimal (~1MB).

## Deployment

### Docker Compose

```bash
docker-compose up -d
docker-compose logs -f bot
```

### Systemd (Linux)

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

```bash
sudo systemctl enable briefbot
sudo systemctl start briefbot
```

### AWS EC2 Free Tier (t3.micro)

**Best for:** New AWS accounts (free for 12 months)

**Why use it:**
- ✅ **Free for 12 months** (750 hours/month)
- ✅ Reliable AWS infrastructure
- ✅ Good for learning AWS

**⚠️ Important:** t3.micro has only 1GB RAM. You MUST add swap space.

#### Setup Steps

**1. Launch EC2 Instance:**
- Instance type: `t3.micro`
- OS: Ubuntu 22.04 LTS
- Storage: 20GB gp2 (within free tier)
- Security group: Allow SSH (port 22)

**2. Connect and Setup:**
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip

# Add 2GB swap file (CRITICAL for 1GB RAM)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**3. Deploy the Bot:**
```bash
# Clone repository
git clone https://github.com/yourusername/tel-brief-bot.git
cd tel-brief-bot

# Create .env file
nano .env
# (Add your environment variables)

# Run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

**4. Monitor Resources:**
```bash
# Check memory usage (should stay under 800MB)
free -h

# Check swap usage (should be low, <500MB)
vmstat 1 5

# Check CPU credits (should stay above 0)
curl http://169.254.169.254/latest/meta-data/instance-type
```

**5. Auto-start on Boot:**
```bash
# Enable Docker auto-start
sudo systemctl enable docker

# The container will auto-start with Docker
```

#### After Free Tier (12 months)
- **Option A:** Continue on t3.micro (~$8-10/month)
- **Option B:** Migrate to Hetzner CX11 (€3.79/month - better value)
- **Option C:** Upgrade to t3.small (~$15/month)

#### Troubleshooting EC2

**High memory usage:**
```bash
# Check what's using memory
docker stats

# If swapping too much, restart container
docker-compose restart
```

**CPU throttling:**
```bash
# Check CPU credit balance
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUCreditBalance \
  --dimensions Name=InstanceId,Value=i-xxxxxxxxxxxxx \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 3600 \
  --statistics Average
```

**Connection issues:**
- Ensure security group allows outbound HTTPS (port 443) for Telegram API
- Check instance has internet access via NAT Gateway or public IP

## Troubleshooting

### "User not authorized" error
Run authentication again:
```bash
python -m src.userbot.auth
```

### Bot not collecting messages
1. Check `ENABLE_MESSAGE_COLLECTION=true`
2. Verify Telethon authentication
3. Make sure you've added chats with `/addchat`

### AI briefs empty
1. Verify `GEMINI_API_KEY` is set
2. Check that monitored chats have recent messages
3. Try broader topics or add more chats

### Briefs not sending at scheduled time
1. Verify timezone with `/status`
2. Check logs for errors
3. Ensure chat is active in database

## Security Notes

- **Session files**: The `sessions/` directory contains your Telegram session. Keep it secure and never share it.
- **API keys**: Never commit `.env` or expose API keys
- **User API**: The bot uses your personal Telegram account to read messages. Use responsibly.

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Format code
black src/

# Lint
flake8 src/

# Type check
mypy src/
```

## License

MIT License

---

**Built with:**
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v20.7
- [Telethon](https://github.com/LonamiWebs/Telethon) v1.36.0
- [Google Generative AI](https://github.com/google/generative-ai-python) v0.8.3
- [APScheduler](https://github.com/agronholm/apscheduler) v3.10.4
- [SQLAlchemy](https://www.sqlalchemy.org/) v2.0.25
