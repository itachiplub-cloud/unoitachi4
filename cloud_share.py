import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from cloud_db import (
    create_share, get_share, revoke_share, get_user_shares,
    get_user_files, get_user
)
from cloud_config import MAX_SHARE_LINKS
from cloud_rate_limit import check_rate_limit, record_action
from cloud_auth import hash_pin, check_pin


async def genlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    allowed, wait = await check_rate_limit(uid, "genlink")
    if not allowed:
        return await update.message.reply_text(f"⏳ Rate limited. Try again in {wait}s.")

    if not context.args:
        return await update.message.reply_text(
            "Usage: /genlink <file_index> [options]\n\n"
            "Options:\n"
            "• `onetime` — link works once\n"
            "• `expire 3600` — expires in seconds\n"
            "• `pass 1234` — password protected\n\n"
            "Example: `/genlink 1 onetime expire 3600 pass 1234`",
            parse_mode="Markdown"
        )

    try:
        file_index = int(context.args[0]) - 1
    except ValueError:
        return await update.message.reply_text("❌ Invalid file index.")

    files = await get_user_files(uid, file_index, 1)
    if not files:
        return await update.message.reply_text("❌ File not found.")

    shares = await get_user_shares(uid)
    active = [s for s in shares if s.get("is_active")]
    if len(active) >= MAX_SHARE_LINKS:
        return await update.message.reply_text(
            f"❌ Maximum {MAX_SHARE_LINKS} active share links. Revoke some first."
        )

    is_one_time = "onetime" in context.args
    expiry_seconds = None
    password = None

    for i, arg in enumerate(context.args):
        if arg == "expire" and i + 1 < len(context.args):
            try:
                expiry_seconds = int(context.args[i + 1])
            except ValueError:
                pass
        if arg == "pass" and i + 1 < len(context.args):
            password = context.args[i + 1]

    expiry = None
    if expiry_seconds:
        expiry = datetime.utcnow() + timedelta(seconds=expiry_seconds)
    password_hashed = hash_pin(password) if password else None

    share_doc = await create_share(
        uid,
        files[0].get("file_id") or str(files[0].get("_id")),
        is_one_time, expiry, password_hashed
    )
    await record_action(uid, "genlink")

    token = share_doc.get("token", "")
    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start=share_{token}"

    flags = []
    if is_one_time:
        flags.append("🔄 One-time")
    if expiry:
        flags.append(f"⏰ Expires: {expiry_seconds}s")
    if password:
        flags.append("🔒 Password protected")

    flags_text = "\n".join(flags) if flags else "No restrictions"

    await update.message.reply_text(
        f"🔗 *Share Link Created!*\n\n"
        f"📄 File: {files[0].get('file_name', 'unknown')}\n"
        f"🔗 Link: `{link}`\n\n"
        f"*Settings:*\n{flags_text}",
        parse_mode="Markdown"
    )


async def mylinks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    shares = await get_user_shares(uid)
    active = [s for s in shares if s.get("is_active")]

    if not active:
        return await update.message.reply_text("📭 No active share links.")

    lines = ["🔗 *Your Share Links*\n"]
    for i, s in enumerate(active[:10], 1):
        token = s.get("token", "")
        expiry = s.get("expiry")
        is_one_time = s.get("is_one_time", False)
        has_pass = "🔒" if s.get("password_hash") else ""
        expiry_str = ""
        if expiry:
            if isinstance(expiry, datetime):
                expiry_str = f" | ⏰ {expiry.strftime('%Y-%m-%d %H:%M')}"
            elif isinstance(expiry, (int, float)):
                expiry_str = f" | ⏰ {datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M')}"
        flags = " 🔄" if is_one_time else ""
        lines.append(f"`{i}`. `{token[:12]}...`{flags}{has_pass}{expiry_str}")

    lines.append(f"\nTotal: {len(active)} / {MAX_SHARE_LINKS}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def revokelink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    if not context.args:
        return await update.message.reply_text("Usage: /revokelink <token>")

    token = context.args[0]
    result = await revoke_share(token, uid)
    if result:
        await update.message.reply_text("✅ Share link revoked.")
    else:
        await update.message.reply_text("❌ Link not found or not yours.")


async def handle_share_link(update: Update, context: ContextTypes.DEFAULT_TYPE, token):
    share = await get_share(token)
    if not share or not share.get("is_active"):
        return await update.message.reply_text("❌ Share link not found or expired.")

    expiry = share.get("expiry")
    if expiry:
        if isinstance(expiry, datetime):
            if datetime.utcnow() > expiry:
                return await update.message.reply_text("⏰ This share link has expired.")
        elif isinstance(expiry, (int, float)):
            if datetime.utcnow().timestamp() > expiry:
                return await update.message.reply_text("⏰ This share link has expired.")

    if share.get("password_hash"):
        context.user_data["share_token"] = token
        context.user_data["share_needs_password"] = True
        return await update.message.reply_text("🔐 This link is password protected. Enter the password:")

    await _send_shared_file(update, context, share)

    if share.get("is_one_time"):
        from cloud_db import get_cloud_db
        db = get_cloud_db()
        await asyncio.to_thread(
            db.shares.update_one,
            {"token": token},
            {"$set": {"is_active": False}},
        )


async def handle_share_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("share_needs_password"):
        return

    password = update.message.text
    await update.message.delete()
    token = context.user_data.get("share_token")
    if not token:
        return await update.message.reply_text("❌ Session expired. Try the link again.")

    share = await get_share(token)
    if not share:
        return await update.message.reply_text("❌ Share link not found.")

    if not check_pin(password, share.get("password_hash", "")):
        return await update.message.reply_text("❌ Wrong password. Try again:")

    context.user_data.pop("share_needs_password", None)
    context.user_data.pop("share_token", None)

    await _send_shared_file(update, context, share)

    if share.get("is_one_time"):
        from cloud_db import get_cloud_db
        db = get_cloud_db()
        await asyncio.to_thread(
            db.shares.update_one,
            {"token": token},
            {"$set": {"is_active": False}},
        )


async def _send_shared_file(update, context, share):
    from cloud_db import get_cloud_db
    db = get_cloud_db()
    file_doc = await asyncio.to_thread(
        db.files.find_one, {"file_id": share.get("file_id")}
    )
    if not file_doc:
        return await update.message.reply_text("❌ File no longer exists.")

    file_id = file_doc.get("file_id")
    file_type = file_doc.get("file_type", "document")

    try:
        if file_type == "photo":
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file_id)
        elif file_type == "video":
            await context.bot.send_video(chat_id=update.effective_chat.id, video=file_id)
        elif file_type == "audio":
            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=file_id)
        else:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send file: {e}")
