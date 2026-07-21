"""
Centralized configuration — single source of truth for all env vars.

Usage:
    from config import BOT_TOKEN, OWNER_ID, ADMIN_IDS

Every value comes from environment variables (loaded via python-dotenv).
Required vars raise SystemExit on startup if missing.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _str(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def _int(key: str, default: int = 0) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"⚠️  Invalid integer for {key}={val}, using default {default}")
        return default

def _float(key: str, default: float = 0.0) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        print(f"⚠️  Invalid float for {key}={val}, using default {default}")
        return default

def _bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("true", "yes", "1", "on")

def _list(key: str, default: str = "", sep: str = ",") -> list:
    """Comma-separated values → list of stripped strings."""
    raw = os.getenv(key, default)
    return [x.strip() for x in raw.split(sep) if x.strip()]

def _int_list(key: str, default: str = "", sep: str = ",") -> list:
    """Comma-separated integers → list of ints."""
    return [int(x) for x in _list(key, default, sep)]

def _mask(value: str, show: int = 4) -> str:
    """Mask a secret, showing only last `show` chars."""
    if not value or len(value) <= show:
        return "****"
    return "*" * (len(value) - show) + value[-show:]

def _require(key: str) -> str:
    """Require an env var or exit with a clear error."""
    val = os.getenv(key)
    if not val:
        print(f"\n❌ FATAL: Missing required environment variable: {key}")
        print(f"   Set it in your .env file or environment.")
        print(f"   See .env.example for reference.\n")
        sys.exit(1)
    return val


# ══════════════════════════════════════════════════════════════════════════════
#  REQUIRED VARIABLES (validated on import)
# ══════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = _require("BOT_TOKEN")


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM / ADMIN
# ══════════════════════════════════════════════════════════════════════════════

OWNER_ID = _int("OWNER_ID", 0)
ADMIN_IDS = _int_list("ADMIN_IDS")
SUDO_USERS = _int_list("SUDO_USERS")
BOT_USERNAME = _str("BOT_USERNAME", "")


# ══════════════════════════════════════════════════════════════════════════════
#  CHANNELS
# ══════════════════════════════════════════════════════════════════════════════

LOG_CHANNEL = _int("LOG_CHANNEL", 0)
UPDATE_CHANNEL = _int("UPDATE_CHANNEL", 0)
FORCE_SUB_CHANNELS = _int_list("FORCE_SUB_CHANNELS")


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════════════════════

DATABASE_URI = _str("DATABASE_URI", "")
DATABASE_NAME = _str("DATABASE_NAME", "unoitachi_cloud")
MONGO_URL = _str("MONGO_URL", DATABASE_URI)
DB_PATH = _str("DB_PATH", "uno.db")
CLAN_DB_PATH = _str("CLAN_DB_PATH", DB_PATH)
STICKERS_DB_PATH = _str("STICKERS_DB_PATH", "stickers.db")
BANK_DB_PATH = _str("BANK_DB_PATH", "bank.db")
DECK_DB_PATH = _str("DECK_DB_PATH", "deck.db")

BACKUP_INTERVAL = _int("BACKUP_INTERVAL", 1800)
MAX_BACKUPS = _int("MAX_BACKUPS", 3)


# ══════════════════════════════════════════════════════════════════════════════
#  REDIS
# ══════════════════════════════════════════════════════════════════════════════

REDIS_URI = _str("REDIS_URI", "")
REDIS_PASSWORD = _str("REDIS_PASSWORD", "")


# ══════════════════════════════════════════════════════════════════════════════
#  WEBHOOK / SERVER
# ══════════════════════════════════════════════════════════════════════════════

WEBHOOK_URL = _str("WEBHOOK_URL", "")
PORT = _int("PORT", 8080)


# ══════════════════════════════════════════════════════════════════════════════
#  AI / API KEYS
# ══════════════════════════════════════════════════════════════════════════════

GROQ_API_KEY = _str("GROQ_API_KEY", "")
GROQ_API_URL = _str("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
OPENAI_API_KEY = _str("OPENAI_API_KEY", "")
GEMINI_API_KEY = _str("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = _str("OPENROUTER_API_KEY", "")


# ══════════════════════════════════════════════════════════════════════════════
#  PYROGRAM / SESSION
# ══════════════════════════════════════════════════════════════════════════════

STRING_SESSION = _str("STRING_SESSION", "")


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGER
# ══════════════════════════════════════════════════════════════════════════════

LOGGER_GROUP_ID = _int("LOGGER_GROUP_ID", 0)
ENABLE_LOGGING = _bool("ENABLE_LOGGING", True)


# ══════════════════════════════════════════════════════════════════════════════
#  ECONOMY / GAME SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

DUEL_REWARD = _int("DUEL_REWARD", 50)
ACTIVITY_COOLDOWN = _int("ACTIVITY_COOLDOWN", 14400)
ACTIVITY_REWARD = _int("ACTIVITY_REWARD", 1000)

LOAN_INTEREST_RATE = _float("LOAN_INTEREST_RATE", 0.07)
LOAN_DURATION_HOURS = _int("LOAN_DURATION_HOURS", 24)
LOAN_DAILY_DEDUCTION_DAYS = _int("LOAN_DAILY_DEDUCTION_DAYS", 3)


# ══════════════════════════════════════════════════════════════════════════════
#  RATE LIMITS / FLOOD
# ══════════════════════════════════════════════════════════════════════════════

MAX_UPLOADS_PER_HOUR = _int("MAX_UPLOADS_PER_HOUR", 30)
MAX_UPLOADS_PER_DAY = _int("MAX_UPLOADS_PER_DAY", 300)
UPLOAD_COOLDOWN = _int("UPLOAD_COOLDOWN", 5)


# ══════════════════════════════════════════════════════════════════════════════
#  CLOUD STORAGE
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_STORAGE_QUOTA = _int("DEFAULT_STORAGE_QUOTA", 20 * 1024 * 1024 * 1024)
MAX_SHARE_LINKS = _int("MAX_SHARE_LINKS", 50)
MAX_FILE_SIZE = _int("MAX_FILE_SIZE", 1 * 1024 * 1024 * 1024)


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-DELETE / PREMIUM / FEATURE FLAGS
# ══════════════════════════════════════════════════════════════════════════════

AUTO_DELETE = _bool("AUTO_DELETE", False)
PREMIUM_USERS = _int_list("PREMIUM_USERS")
DEVELOPER_IDS = _int_list("DEVELOPER_IDS")


# ══════════════════════════════════════════════════════════════════════════════
#  SUPPORT / LINKS
# ══════════════════════════════════════════════════════════════════════════════

SUPPORT_CHAT = _str("SUPPORT_CHAT", "")
SUPPORT_GROUP = _str("SUPPORT_GROUP", "")
GITHUB_URL = _str("GITHUB_URL", "https://github.com/itachiplub-cloud/unoitachi4")
WEBSITE_URL = _str("WEBSITE_URL", "")


# ══════════════════════════════════════════════════════════════════════════════
#  MAINTENANCE
# ══════════════════════════════════════════════════════════════════════════════

MAINTENANCE_MODE = _bool("MAINTENANCE_MODE", False)


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_config_summary():
    """Print a masked config summary on startup."""
    print("═══ Config loaded from .env ═══")
    print(f"  BOT_TOKEN      : {_mask(BOT_TOKEN)}")
    print(f"  OWNER_ID       : {OWNER_ID}")
    print(f"  ADMIN_IDS      : {len(ADMIN_IDS)} admins")
    print(f"  MONGO_URL      : {_mask(MONGO_URL, 8)}")
    print(f"  GROQ_API_KEY   : {_mask(GROQ_API_KEY)}")
    print(f"  LOGGER_GROUP_ID: {LOGGER_GROUP_ID}")
    print(f"  DB_PATH        : {DB_PATH}")
    print(f"  MAINTENANCE    : {MAINTENANCE_MODE}")
    print("═══════════════════════════════")
