import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn
from config import ADMIN_IDS as admin_ids

async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        chat_id = chat.id
        title = chat.title or "Unnamed"

        def _db_op():
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

        await asyncio.to_thread(_db_op)


async def mygroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("⛔ Only admins can view group list.")

    def _db_op():
        with get_conn() as conn:
            return conn.execute("SELECT chat_id, title FROM known_groups ORDER BY title ASC").fetchall()
    rows = await asyncio.to_thread(_db_op)

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

    def _db_op():
        with get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM known_groups").fetchone()
            return row[0] if row else 0
    total = await asyncio.to_thread(_db_op)

    await update.message.reply_text(f"📊 Bot is currently added to <b>{total}</b> groups.", parse_mode="HTML")
