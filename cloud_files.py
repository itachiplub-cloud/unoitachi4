import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from cloud_db import (
    save_file, get_user_files, delete_file, search_files,
    get_user, get_user_usage, get_file_by_id
)
from cloud_config import MAX_FILE_SIZE, UPLOAD_COOLDOWN
from cloud_rate_limit import check_rate_limit, record_action

_upload_timestamps = {}


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    user = await get_user(uid)
    if not user or user.get("is_banned"):
        return await update.message.reply_text("🚫 Your account is banned.")

    msg = update.message
    doc = msg.document
    if not doc and msg.photo:
        doc = msg.photo[-1]
    if not doc:
        doc = msg.video or msg.audio or msg.voice or msg.video_note
    if not doc:
        return

    file_size = doc.file_size
    if file_size > MAX_FILE_SIZE:
        return await update.message.reply_text(
            f"❌ Maximum allowed file size is 1 GB.\n"
            f"Your file: {file_size / (1024*1024):.1f} MB"
        )

    usage = await get_user_usage(uid)
    quota = user.get("storage_quota", 20*1024*1024*1024)
    if usage.get("storage_used", 0) + file_size > quota:
        return await update.message.reply_text("❌ Storage quota exceeded. Clean up some files.")

    now = time.time()
    last_upload = _upload_timestamps.get(uid, 0)
    if now - last_upload < UPLOAD_COOLDOWN:
        remaining = int(UPLOAD_COOLDOWN - (now - last_upload))
        return await update.message.reply_text(f"⏳ Please wait {remaining}s before uploading another file.")

    allowed, wait = await check_rate_limit(uid, "upload")
    if not allowed:
        return await update.message.reply_text(f"⏳ Rate limited. Try again in {wait}s.")

    file_name = doc.file_name or f"{doc.file_id[:8]}"
    file_type = "document"
    if msg.photo:
        file_type = "photo"
        file_name = f"photo_{doc.file_id[:8]}.jpg"
    elif msg.video:
        file_type = "video"
    elif msg.audio:
        file_type = "audio"

    caption = msg.caption or ""

    await save_file(uid, doc.file_id, file_name, file_type, file_size, caption, [], "")
    await record_action(uid, "upload")
    _upload_timestamps[uid] = now

    size_str = _format_size(file_size)
    await update.message.reply_text(
        f"✅ *File Saved!*\n\n"
        f"📄 {file_name}\n"
        f"💾 Size: {size_str}\n"
        f"📁 Type: {file_type}",
        parse_mode="Markdown"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_document(update, context)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_document(update, context)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_document(update, context)


async def saved_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    allowed, wait = await check_rate_limit(uid, "saved")
    if not allowed:
        return await update.message.reply_text(f"⏳ Rate limited. Try again in {wait}s.")

    page = int(context.args[0]) if context.args else 0
    files = await get_user_files(uid, page * 5, 5)
    usage = await get_user_usage(uid)
    total = usage.get("file_count", 0)
    total_pages = (total + 4) // 5

    if not files:
        return await update.message.reply_text("📭 No files saved yet. Send me a file!")

    lines = [f"📁 *Your Files* (Page {page+1}/{total_pages})\n"]
    for i, f in enumerate(files, start=page * 5 + 1):
        size = _format_size(f.get("file_size", 0))
        lines.append(f"`{i}`. 📄 {f.get('file_name', 'unknown')} ({size})")

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cloud_page_{page-1}"))
    if (page + 1) * 5 < total:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"cloud_page_{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    allowed, wait = await check_rate_limit(uid, "search")
    if not allowed:
        return await update.message.reply_text(f"⏳ Rate limited. Try again in {wait}s.")

    query = " ".join(context.args) if context.args else ""
    if not query:
        return await update.message.reply_text("Usage: /search <filename>")

    files = await search_files(uid, query)
    if not files:
        return await update.message.reply_text("📭 No files found.")

    lines = [f"🔍 *Search Results for \"{query}\"*\n"]
    for i, f in enumerate(files[:10], 1):
        size = _format_size(f.get("file_size", 0))
        lines.append(f"`{i}`. 📄 {f.get('file_name', 'unknown')} ({size})")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    if not context.args:
        return await update.message.reply_text("Usage: /delete <file_index>")

    try:
        index = int(context.args[0]) - 1
    except ValueError:
        return await update.message.reply_text("❌ Invalid index.")

    files = await get_user_files(uid, index, 1)
    if not files:
        return await update.message.reply_text("❌ File not found.")

    file = files[0]
    file_id_str = file.get("file_id", "")
    result = await delete_file(file_id_str, uid)
    if result:
        await update.message.reply_text(f"🗑️ Deleted: {file.get('file_name', 'unknown')}")
    else:
        await update.message.reply_text("❌ Failed to delete file.")


async def storage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    user = await get_user(uid)
    usage = await get_user_usage(uid)

    quota = user.get("storage_quota", 20*1024*1024*1024)
    used = usage.get("storage_used", 0)
    free = quota - used

    used_gb = used / (1024*1024*1024)
    quota_gb = quota / (1024*1024*1024)
    free_gb = free / (1024*1024*1024)

    bar_len = 20
    filled = int(bar_len * used / quota) if quota > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    await update.message.reply_text(
        f"💾 *Storage Usage*\n\n"
        f"`{bar}`\n"
        f"Used: {used_gb:.2f} GB / {quota_gb:.0f} GB\n"
        f"Free: {free_gb:.2f} GB\n"
        f"📄 Files: {usage.get('file_count', 0)}",
        parse_mode="Markdown"
    )


async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.user_data.get("logged_in"):
        return await update.message.reply_text("🔐 Please /login first.")

    allowed, wait = await check_rate_limit(uid, "get")
    if not allowed:
        return await update.message.reply_text(f"⏳ Rate limited. Try again in {wait}s.")

    if not context.args:
        return await update.message.reply_text("Usage: /get <file_index>")

    try:
        index = int(context.args[0]) - 1
    except ValueError:
        return await update.message.reply_text("❌ Invalid index.")

    files = await get_user_files(uid, index, 1)
    if not files:
        return await update.message.reply_text("❌ File not found.")

    file = files[0]
    await update.message.reply_text("📤 Sending your file...")

    file_id = file.get("file_id")
    file_type = file.get("file_type", "document")

    try:
        if file_type == "photo":
            await context.bot.send_photo(chat_id=uid, photo=file_id, caption=file.get("caption", ""))
        elif file_type == "video":
            await context.bot.send_video(chat_id=uid, video=file_id, caption=file.get("caption", ""))
        elif file_type == "audio":
            await context.bot.send_audio(chat_id=uid, audio=file_id)
        else:
            await context.bot.send_document(chat_id=uid, document=file_id, caption=file.get("caption", ""))
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send file: {e}")


async def show_my_files(query, context):
    uid = query.from_user.id
    files = await get_user_files(uid, 0, 5)
    usage = await get_user_usage(uid)
    total = usage.get("file_count", 0)

    if not files:
        return await query.edit_message_text("📭 No files saved yet. Send me a file!")

    lines = [f"📁 *Your Files* (Page 1/{(total + 4) // 5})\n"]
    for i, f in enumerate(files, start=1):
        size = _format_size(f.get("file_size", 0))
        lines.append(f"`{i}`. 📄 {f.get('file_name', 'unknown')} ({size})")

    buttons = []
    if total > 5:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data="cloud_page_1"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup
    )


async def handle_cloud_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if not data.startswith("cloud_page_"):
        return

    try:
        page = int(data.split("_")[-1])
    except ValueError:
        return

    files = await get_user_files(uid, page * 5, 5)
    usage = await get_user_usage(uid)
    total = usage.get("file_count", 0)
    total_pages = (total + 4) // 5

    if not files:
        return await query.edit_message_text("📭 No files on this page.")

    lines = [f"📁 *Your Files* (Page {page+1}/{total_pages})\n"]
    for i, f in enumerate(files, start=page * 5 + 1):
        size = _format_size(f.get("file_size", 0))
        lines.append(f"`{i}`. 📄 {f.get('file_name', 'unknown')} ({size})")

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cloud_page_{page-1}"))
    if (page + 1) * 5 < total:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"cloud_page_{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup
    )


def _format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
