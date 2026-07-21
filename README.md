# Itachi Bot

A Telegram bot built with Python that allows users to earn coins, draw cards, cast spells, and battle friends in a chaotic UNO-style economy — plus a personal cloud file saver.

## Features

- `/start`, `/earn`, `/balance`, `/draw`, `/steal`, `/reverse`
- Prestige system: `/spellbook`, `/castspell`, `/equipspell`
- Fusion engine: `/fusion burn mimic`
- Achievements: `/duelachievements`
- Admin commands: `/uploadcard`, `/removecard`, `/broadcast`, `/purgeusers`
- Daily reward system + user tracking
- Personal cloud file storage with share links
- Full admin system (Owner → Sudo Admin → Normal User)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/itachiplub-cloud/unoitachi4.git
cd unoitachi4
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values. **At minimum, `BOT_TOKEN` is required.**

```env
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_telegram_id
ADMIN_IDS=your_id,admin_id
MONGO_URL=mongodb+srv://...
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the bot

```bash
python main.py
```

## Deployment

### VPS / Dedicated Server

```bash
# Install dependencies
sudo apt update && sudo apt install python3-pip -y
pip install -r requirements.txt

# Set up .env
cp .env.example .env
nano .env  # fill in your values

# Run with systemd
sudo cp itachi-bot.service /etc/systemd/system/
sudo systemctl enable itachi-bot
sudo systemctl start itachi-bot
```

### Docker

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f bot

# Stop
docker compose down
```

### Heroku

1. Push to Heroku: `git push heroku main`
2. Set config vars in Heroku dashboard or:
```bash
heroku config:set BOT_TOKEN=your_token
heroku config:set OWNER_ID=your_id
heroku config:set MONGO_URL=your_mongo_uri
```

### Railway

1. Connect your GitHub repo at [railway.app](https://railway.app)
2. Add environment variables in the Railway dashboard
3. Railway auto-deploys from your repo

### Koyeb / Render

1. Connect your GitHub repo
2. Set environment variables in the dashboard
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python main.py`

## Environment Variables

All configuration is loaded from environment variables. See [`.env.example`](.env.example) for the complete list.

### Required

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `OWNER_ID` | Owner's Telegram user ID |

### Recommended

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_IDS` | Comma-separated admin IDs | `[]` |
| `MONGO_URL` | MongoDB URI for cloud features | `""` |
| `LOGGER_GROUP_ID` | Log channel ID | `0` |
| `GROQ_API_KEY` | Groq AI key for reply engine | `""` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_PATH` | Main SQLite database path | `uno.db` |
| `BACKUP_INTERVAL` | Backup interval in seconds | `1800` |
| `DUEL_REWARD` | Duel win reward | `50` |
| `ACTIVITY_COOLDOWN` | Keyword reward cooldown | `14400` |
| `ACTIVITY_REWARD` | Keyword reward amount | `1000` |
| `LOAN_INTEREST_RATE` | Loan interest rate | `0.07` |
| `AUTO_DELETE` | Auto-delete messages | `false` |
| `MAINTENANCE_MODE` | Maintenance mode | `false` |
| `WEBHOOK_URL` | Webhook URL for production | `""` |
| `PORT` | Server port | `8080` |

See `.env.example` for all 50+ supported variables.

## Configuration System

The bot uses a centralized `config.py` that loads all values from environment variables via `python-dotenv`. No `config.json` is needed.

- **Required variables** raise a clear error on startup if missing
- **Sensitive values** are masked in startup logs
- **Type conversion** is handled automatically (int, float, bool, list)
- **Comma-separated lists** (e.g., `ADMIN_IDS=1,2,3`) are parsed automatically

## Project Structure

```
├── main.py              # Entry point
├── config.py            # Centralized env config
├── database.py          # SQLite database layer
├── card_utils.py        # Card system
├── cloud_*.py           # Cloud storage features
├── economy_commands.py  # Banking system
├── games.py             # Mini-games
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker deployment
├── docker-compose.yml   # Docker Compose
└── itachi-bot.service   # systemd service
```

## Support

If you have any problem or query about the bot, reach out to:
- 👤 [@Itachiplub2](https://t.me/Itachiplub2)
- 👤 [@Avalon_18](https://t.me/Avalon_18)

## License

MIT
