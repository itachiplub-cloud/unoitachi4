import json
import os

MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB
MAX_UPLOADS_PER_HOUR = 30
MAX_UPLOADS_PER_DAY = 300
UPLOAD_COOLDOWN = 5  # seconds

RATE_LIMITS = {
    "saved": 5,
    "get": 3,
    "genlink": 10,
    "login": 5,      # per hour
    "register": 3,   # per day
    "search": 3,
}

PIN_LOCK_ATTEMPTS = 3
PIN_LOCK_DURATION = 600  # 10 min
PIN_DAILY_LOCKOUT_ATTEMPTS = 10
PIN_DAILY_LOCKOUT_DURATION = 86400  # 24 hr

LOGIN_LOCK_ATTEMPTS = 5
LOGIN_LOCK_DURATION = 1800  # 30 min

MAX_SHARE_LINKS = 50
DEFAULT_STORAGE_QUOTA = 20 * 1024 * 1024 * 1024  # 20 GB

SPAM_WARNINGS = 1
SPAM_MUTE_DURATION = 600  # 10 min
SPAM_BAN_DURATION = 86400  # 24 hr

try:
    with open("config.json", "r") as f:
        _cfg = json.load(f)
except Exception:
    _cfg = {}

MONGO_URL = os.getenv("MONGO_URL", _cfg.get("MONGO_URL", ""))
CLOUD_DB_NAME = "unoitachi_cloud"
OWNER_ID = int(_cfg.get("OWNER_ID", 8055084559))


def _load_maintenance():
    try:
        with open("maintenance.json", "r") as f:
            return json.load(f).get("enabled", False)
    except Exception:
        return False


def set_maintenance(enabled):
    with open("maintenance.json", "w") as f:
        json.dump({"enabled": enabled}, f)
