import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
# Functions to manage admins are assumed to exist in database module
from database import add_admin, remove_admin, get_admin_list
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Bot owner ID (only owner can add/remove sudo admins)
OWNER_ID = 8055084559

def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

async def add_sudo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a user as bot admin. Only the bot owner can use this command.
    Usage: reply to a user's message with /addsudo or provide user ID as argument.
    """
    requester = update.effective_user.id
    if not _is_owner(requester):
        return await update.message.reply_text("⚠️ Only the bot owner can add sudo admins.")
    # Determine target user ID
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        if not context.args:
            return await update.message.reply_text("⚠️ Provide a user ID or reply to a user's message.")
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")
    # Add admin (owner is already in ADMIN_IDS)
    add_admin(target_id)
    await update.message.reply_text(f"✅ User {target_id} added to bot admins.")

async def rm_sudo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from bot admins. Only the bot owner can use this command.
    Usage similar to /addsudo.
    """
    requester = update.effective_user.id
    if not _is_owner(requester):
        return await update.message.reply_text("⚠️ Only the bot owner can remove sudo admins.")
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        if not context.args:
            return await update.message.reply_text("⚠️ Provide a user ID or reply to a user's message.")
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")
    # Prevent removing the owner
    if target_id == OWNER_ID:
        return await update.message.reply_text("🚫 Cannot remove the bot owner from admins.")
    remove_admin(target_id)
    await update.message.reply_text(f"✅ User {target_id} removed from bot admins.")

async def sudo_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List current bot admins (including owner)."""
    admins = get_admin_list()
    if not admins:
        return await update.message.reply_text("⚠️ No admins configured.")
    lines = ["🛡 <b>Bot Admins:</b>"]
    for uid in sorted(admins):
        lines.append(f"• ID: <code>{uid}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

def get_admin_sudo_handlers():
    """Return CommandHandler objects for registration in the main application."""
    return [
        CommandHandler("addsudo", add_sudo_handler),
        CommandHandler("rmsudo", rm_sudo_handler),
        CommandHandler("sudolist", sudo_list_handler),
    ]
