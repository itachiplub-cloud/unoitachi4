import random
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS
from sdb import add_file_id, list_file_ids, remove_file_id

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def add_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, user = update.effective_message, update.effective_user
    if not is_admin(user.id):
        return await msg.reply_text("🚫 You’re not an admin.")
    tgt = msg.reply_to_message
    if not tgt or (not tgt.sticker and not tgt.animation):
        return await msg.reply_text("Reply to a sticker or GIF with /addsticker.")
    fid = tgt.sticker.file_id if tgt.sticker else tgt.animation.file_id
    add_file_id(fid)
    await msg.reply_text("✅ Added to the sticker pool.")

async def list_stickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, user = update.effective_message, update.effective_user
    if not is_admin(user.id):
        return await msg.reply_text("🚫 You’re not an admin.")
    pool = list_file_ids()
    if not pool:
        return await msg.reply_text("❌ Pool is empty.")
    lines = [f"{i+1}. {fid}" for i, fid in enumerate(pool)]
    await msg.reply_text("🎟️ Current Sticker Pool:\n" + "\n".join(lines))

async def remove_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, user = update.effective_message, update.effective_user
    if not is_admin(user.id):
        return await msg.reply_text("🚫 You’re not an admin.")
    if not context.args:
        return await msg.reply_text("Usage: /removesticker <file_id>")
    remove_file_id(context.args[0])
    await msg.reply_text("🗑️ Removed (if present).")

async def react_with_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    # 1) Must reply to one of the bot’s messages
    if not msg.reply_to_message or msg.reply_to_message.from_user.id != context.bot.id:
        return

    # 2) Only proceed if it’s a sticker or animation
    if not (msg.sticker or msg.animation):
        return

    # 3) Choose & send a random sticker from pool
    pool = list_file_ids()
    if not pool:
        return

    choice = random.choice(pool)
    logger.info("Replying to %s with sticker %s", msg.from_user.id, choice)
    await msg.reply_sticker(choice)

admin_handlers = [
    CommandHandler("addsticker",    add_sticker),
    CommandHandler("liststickers",  list_stickers),
    CommandHandler("removesticker", remove_sticker),
]

reaction_handler = MessageHandler(
    filters.REPLY & ~filters.TEXT & ~filters.COMMAND,
    react_with_random
)
