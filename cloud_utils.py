import asyncio
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from cloud_db import get_user, get_user_usage, get_cloud_db
from cloud_config import OWNER_ID
from database import is_bot_admin


def _admin_check(uid):
    return is_bot_admin(uid) or uid == OWNER_ID


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_timestamp(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M")
    return str(ts)


async def is_logged_in(context):
    return context.user_data.get("logged_in", False)


async def require_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("logged_in"):
        await update.message.reply_text("🔐 Please /login first.")
        return False
    return True


async def get_user_or_none(uid):
    return await get_user(uid)


async def get_user_storage_info(uid):
    user = await get_user(uid)
    usage = await get_user_usage(uid)
    if not user:
        return None
    return {
        "user": user,
        "usage": usage,
        "quota": user.get("storage_quota", 20*1024*1024*1024),
        "used": usage.get("storage_used", 0),
        "free": user.get("storage_quota", 20*1024*1024*1024) - usage.get("storage_used", 0),
        "file_count": usage.get("file_count", 0),
        "share_count": usage.get("share_count", 0),
    }


async def purge_user_data(uid):
    db = get_cloud_db()
    files = await asyncio.to_thread(
        lambda: list(db.files.find({"owner_id": uid}))
    )
    total_size = sum(f.get("file_size", 0) for f in files)

    await asyncio.to_thread(db.files.delete_many, {"owner_id": uid})
    await asyncio.to_thread(db.shares.delete_many, {"owner_id": uid})
    await asyncio.to_thread(db.sessions.delete_many, {"user_id": uid})
    await asyncio.to_thread(db.rate_limits.delete_many, {"user_id": uid})
    await asyncio.to_thread(db.security.delete_many, {"user_id": uid})
    await asyncio.to_thread(db.pin_locks.delete_many, {"user_id": uid})
    await asyncio.to_thread(db.login_locks.delete_many, {"user_id": uid})
    await asyncio.to_thread(db.user_verification.delete_many, {"user_id": uid})
    await asyncio.to_thread(db.users.delete_one, {"unique_id": uid})

    return {
        "files_deleted": len(files),
        "storage_freed": total_size,
    }


async def health_check():
    try:
        db = get_cloud_db()
        await asyncio.to_thread(db.command, "ping")
        return True
    except Exception:
        return False
