from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn
import time
import json

with open("config.json", "r") as f:
    config = json.load(f)

admin_ids = config["ADMIN_IDS"]

from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn
import time

async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        chat_id = chat.id
        title = chat.title or "Unnamed"

        print(f"✅ Bot seen in group: {title} ({chat_id})")  # Optional debug print

        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS known_groups (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO known_groups (chat_id, title)
                VALUES (?, ?)
            """, (chat_id, title))
            conn.commit()


async def mygroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("⛔ Only admins can view group list.")

    with get_conn() as conn:
        rows = conn.execute("SELECT chat_id, title FROM known_groups ORDER BY title ASC").fetchall()

    if not rows:
        return await update.message.reply_text("📭 Bot is not added to any groups yet.")

    message = "<b>📋 Groups where bot is added:</b>\n\n"
    for i, (chat_id, title) in enumerate(rows):
        message += f"{i+1}. <b>{title}</b>\n🆔 <code>{chat_id}</code>\n\n"

    await update.message.reply_text(message.strip(), parse_mode="HTML")



async def groupcount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM known_groups").fetchone()
        total = row[0] if row else 0

    await update.message.reply_text(f"📊 Bot is currently added to <b>{total}</b> groups.", parse_mode="HTML")
