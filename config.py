import json

with open("config.json", "r") as f:
    config = json.load(f)

BOT_TOKEN = config.get("BOT_TOKEN")
ADMIN_IDS = config.get("ADMIN_IDS", [])

DB_PATH = "stickers.db"
