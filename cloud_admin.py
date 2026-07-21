import asyncio
import time
from telegram import Update
from telegram.ext import ContextTypes

from cloud_db import (
    get_all_users, get_user_count, get_total_storage,
    get_cloud_db, log_audit, update_user
)
from cloud_config import OWNER_ID, set_maintenance, _load_maintenance
from cloud_security import reset_all_locks, is_muted, is_banned
from database import is_bot_admin


def _admin_check(uid):
    return is_bot_admin(uid) or uid == OWNER_ID


async def cloud_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    user_count = await get_user_count()
    total_storage = await get_total_storage()
    total_gb = total_storage / (1024*1024*1024)

    db = get_cloud_db()
    file_count = await asyncio.to_thread(db.files.count_documents, {})
    share_count = await asyncio.to_thread(db.shares.count_documents, {"is_active": True})
    session_count = await asyncio.to_thread(db.sessions.count_documents, {"is_active": True})

    muted = 0
    banned = 0
    all_users = await get_all_users(0, 0)
    for u in all_users:
        uid_check = u.get("unique_id")
        if uid_check:
            if await is_muted(uid_check):
                muted += 1
            if await is_banned(uid_check):
                banned += 1

    await update.message.reply_text(
        f"📊 *Cloud Bot Statistics*\n\n"
        f"👥 Users: {user_count}\n"
        f"📄 Files: {file_count}\n"
        f"🔗 Active shares: {share_count}\n"
        f"🔑 Active sessions: {session_count}\n"
        f"💾 Total storage: {total_gb:.2f} GB\n"
        f"🚫 Muted: {muted}\n"
        f"⛔ Banned: {banned}",
        parse_mode="Markdown"
    )


async def cloud_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    page = int(context.args[0]) - 1 if context.args else 0
    users = await get_all_users(page * 10, 10)
    total = await get_user_count()
    total_pages = (total + 9) // 10

    if not users:
        return await update.message.reply_text("📭 No users on this page.")

    lines = [f"👥 *Users* (Page {page+1}/{total_pages})\n"]
    for u in users:
        uid_str = u.get("unique_id", "?")
        uname = u.get("username", "N/A")
        storage = u.get("storage_used", 0) / (1024*1024*1024)
        files_count = await asyncio.to_thread(
            get_cloud_db().files.count_documents, {"owner_id": uid_str}
        )
        status = "⛔" if u.get("is_banned") else "✅"
        lines.append(f"{status} `{uid_str}` | @{uname} | {storage:.2f} GB | {files_count} files")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cloud_admin_userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /cloud_userinfo <user_id>")

    try:
        target = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    from cloud_db import get_user
    user = await get_user(target)
    if not user:
        return await update.message.reply_text("❌ User not found in cloud DB.")

    from cloud_db import get_user_usage
    usage = await get_user_usage(target)

    storage_gb = usage.get("storage_used", 0) / (1024*1024*1024)
    quota_gb = user.get("storage_quota", 0) / (1024*1024*1024)
    created = user.get("created_at", "")
    if isinstance(created, (int, float)):
        from datetime import datetime
        created = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"👤 *User Info*\n",
        f"🆔 ID: `{target}`",
        f"📛 Username: @{user.get('username', 'N/A')}",
        f"📅 Joined: {created}",
        f"💾 Storage: {storage_gb:.2f} / {quota_gb:.0f} GB",
        f"📄 Files: {usage.get('file_count', 0)}",
        f"🔗 Shares: {usage.get('share_count', 0)}",
        f"📤 Uploads: {user.get('upload_count', 0)}",
        f"🚫 Banned: {'Yes' if user.get('is_banned') else 'No'}",
        f"🔒 Locked: {'Yes' if user.get('is_locked') else 'No'}",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cloud_admin_tempban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /cloud_tempban <user_id> <hours> [reason]")

    try:
        target = int(context.args[0])
        hours = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ Invalid args.")

    reason = " ".join(context.args[2:]) if len(context.args) > 2 else "No reason"

    ban_until = time.time() + hours * 3600
    await update_user(target, is_banned=True, ban_reason=reason, ban_until=ban_until)
    await log_audit(uid, target, "tempban", f"{hours}h: {reason}")

    await update.message.reply_text(
        f"⛔ User `{target}` banned for {hours}h.\nReason: {reason}",
        parse_mode="Markdown"
    )


async def cloud_admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /cloud_ban <user_id> [reason]")

    try:
        target = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason"

    await update_user(target, is_banned=True, ban_reason=reason, ban_until=None)
    await log_audit(uid, target, "ban", reason)

    await update.message.reply_text(
        f"⛔ User `{target}` permanently banned.\nReason: {reason}",
        parse_mode="Markdown"
    )


async def cloud_admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /cloud_unban <user_id>")

    try:
        target = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await update_user(target, is_banned=False, ban_reason=None, ban_until=None)
    await reset_all_locks(target)
    await log_audit(uid, target, "unban", "")

    await update.message.reply_text(f"✅ User `{target}` unbanned.", parse_mode="Markdown")


async def cloud_admin_resetlimits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /cloud_resetlimits <user_id>")

    try:
        target = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Invalid user ID.")

    await reset_all_locks(target)
    await log_audit(uid, target, "resetlimits", "")

    await update.message.reply_text(
        f"✅ All locks reset for `{target}`.", parse_mode="Markdown"
    )


async def cloud_admin_setquota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /cloud_setquota <user_id> <gb>")

    try:
        target = int(context.args[0])
        gb = float(context.args[1])
    except ValueError:
        return await update.message.reply_text("❌ Invalid args.")

    quota_bytes = int(gb * 1024 * 1024 * 1024)
    await update_user(target, storage_quota=quota_bytes)
    await log_audit(uid, target, "setquota", f"{gb} GB")

    await update.message.reply_text(
        f"✅ Storage quota for `{target}` set to {gb} GB.",
        parse_mode="Markdown"
    )


async def cloud_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if not context.args:
        return await update.message.reply_text("Usage: /cloud_broadcast <message>")

    message = " ".join(context.args)
    users = await get_all_users(0, 0)
    sent = 0
    failed = 0

    for u in users:
        target_uid = u.get("unique_id")
        if not target_uid:
            continue
        try:
            await context.bot.send_message(target_uid, f"📢 *Broadcast*\n\n{message}", parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await update.message.reply_text(
        f"📢 Broadcast complete.\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )


async def cloud_admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        return await update.message.reply_text("🚫 Owner only.")

    if not context.args or context.args[0] not in ("on", "off"):
        return await update.message.reply_text("Usage: /cloud_maintenance <on|off>")

    enabled = context.args[0] == "on"
    set_maintenance(enabled)
    status = "ON" if enabled else "OFF"
    await update.message.reply_text(f"🔧 Maintenance mode: {status}")


async def cloud_admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _admin_check(uid):
        return await update.message.reply_text("🚫 Admins only.")

    db = get_cloud_db()
    logs = await asyncio.to_thread(
        lambda: list(db.audit_logs.find().sort("timestamp", -1).limit(20))
    )

    if not logs:
        return await update.message.reply_text("📭 No audit logs yet.")

    lines = ["📋 *Recent Audit Logs*\n"]
    for log in logs:
        ts = log.get("timestamp", 0)
        if isinstance(ts, (int, float)):
            from datetime import datetime
            ts_str = datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
        else:
            ts_str = str(ts)
        lines.append(
            f"[{ts_str}] Admin `{log.get('admin_id')}` → "
            f"User `{log.get('target_user')}`: {log.get('action')} "
            f"| {log.get('reason', '')}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
