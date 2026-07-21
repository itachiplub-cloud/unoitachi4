import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from cloud_db import get_cloud_db
from cloud_config import OWNER_ID

async def addchannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    from database import is_bot_admin
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text(
            "Usage: /addchannel <chat_id> <title>\n"
            "Example: /addchannel -1001234567890 MyChannel"
        )

    try:
        chat_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid chat ID.")

    title = " ".join(context.args[1:]) if len(context.args) > 1 else "Channel"

    db = get_cloud_db()

    invite_link = None
    try:
        chat = await context.bot.get_chat(chat_id)
        if chat.invite_link:
            invite_link = chat.invite_link
        else:
            link = await context.bot.export_chat_invite_link(chat_id)
            invite_link = link
    except Exception:
        pass

    db.bot_config.update_one(
        {"key": "must_join_version"},
        {"$inc": {"value": 1}},
        upsert=True
    )
    version = db.bot_config.find_one({"key": "must_join_version"})["value"]

    db.channels.insert_one({
        "chat_id": chat_id,
        "title": title,
        "invite_link": invite_link,
        "version": version
    })

    await update.message.reply_text(
        f"✅ Channel added: {title}\n"
        f"🆔 `{chat_id}`\n"
        f"📋 Version: {version}\n\n"
        "⚠️ All users must re-verify.",
        parse_mode="Markdown"
    )

async def removechannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    from database import is_bot_admin
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /removechannel <chat_id>")

    try:
        chat_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid chat ID.")

    db = get_cloud_db()
    result = db.channels.delete_one({"chat_id": chat_id})

    if result.deleted_count:
        db.bot_config.update_one(
            {"key": "must_join_version"},
            {"$inc": {"value": 1}},
            upsert=True
        )
        await update.message.reply_text(f"✅ Channel removed. Users must re-verify.")
    else:
        await update.message.reply_text("❌ Channel not found.")

async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    from database import is_bot_admin
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Admins only.")

    db = get_cloud_db()
    channels = list(db.channels.find())

    if not channels:
        return await update.message.reply_text("📭 No required channels configured.")

    lines = ["📋 *Required Channels*\n"]
    for ch in channels:
        link = ch.get("invite_link", "N/A")
        lines.append(f"• {ch.get('title', 'Unknown')} (`{ch['chat_id']}`)")
        lines.append(f"  Link: {link}")

    version = db.bot_config.find_one({"key": "must_join_version"})
    lines.append(f"\n📋 Version: {version['value'] if version else 0}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    channels = await get_required_channels()
    must_join_version = await get_must_join_version()

    all_joined = True
    not_joined = []

    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["chat_id"], uid)
            if member.status in ["left", "kicked"]:
                all_joined = False
                not_joined.append(ch)
        except Exception:
            pass

    if all_joined:
        db = get_cloud_db()
        db.user_verification.update_one(
            {"user_id": uid},
            {"$set": {"verified_version": must_join_version}},
            upsert=True
        )
        await query.edit_message_text(
            "✅ *Verification Complete!*\n\nYou can now use the bot.",
            parse_mode="Markdown"
        )
    else:
        buttons = []
        for ch in not_joined:
            buttons.append([InlineKeyboardButton(
                f"➕ {ch['title']}",
                url=ch.get("invite_link", "https://t.me/")
            )])
        buttons.append([InlineKeyboardButton("🔄 Verify", callback_data="cloud_verify")])
        await query.edit_message_text(
            "❌ You haven't joined all channels yet.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def get_required_channels():
    db = get_cloud_db()
    return list(db.channels.find())

async def get_must_join_version():
    db = get_cloud_db()
    doc = db.bot_config.find_one({"key": "must_join_version"})
    return doc["value"] if doc else 0
