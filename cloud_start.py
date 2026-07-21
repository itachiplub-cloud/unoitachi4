import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from cloud_db import get_user, get_user_usage, get_active_session, get_cloud_db
from cloud_channels import get_required_channels, is_user_verified, get_must_join_version

async def cloud_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    from cloud_config import _load_maintenance, OWNER_ID
    if _load_maintenance() and uid != OWNER_ID:
        return await update.message.reply_text("🔧 Bot is under maintenance. Try later.")

    must_join_version = await get_must_join_version()
    if must_join_version > 0:
        verified_version = await _get_verified_version(uid)
        if verified_version < must_join_version:
            return await show_must_join(update, context, uid)
    
    user = await asyncio.to_thread(get_user, uid)
    
    if not user:
        # Not registered
        keyboard = [
            [InlineKeyboardButton("➕ Create Account", callback_data="cloud_register")],
            [InlineKeyboardButton("🔐 Login Account", callback_data="cloud_login")],
            [InlineKeyboardButton("❓ Help", callback_data="cloud_help")],
            [InlineKeyboardButton("📊 Stats", callback_data="cloud_stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return await update.message.reply_text(
            "☁️ *Welcome to Personal Cloud Saver Bot*\n\n"
            "Securely save:\n"
            "• 📁 Files\n"
            "• 🖼️ Photos\n"
            "• 🎬 Videos\n"
            "• 📄 Documents\n"
            "• 💬 Messages\n\n"
            "Create an account or login to start!",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    # Check if logged in
    session = context.user_data.get("session")
    logged_in = context.user_data.get("logged_in", False)
    
    if not logged_in or not session:
        keyboard = [
            [InlineKeyboardButton("🔐 Login Account", callback_data="cloud_login")],
            [InlineKeyboardButton("➕ Create Account", callback_data="cloud_register")],
            [InlineKeyboardButton("❓ Help", callback_data="cloud_help")],
            [InlineKeyboardButton("📊 Stats", callback_data="cloud_stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return await update.message.reply_text(
            f"☁️ *Welcome back, {update.effective_user.first_name}!*\n\n"
            "Login to access your cloud storage.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    # Logged in
    usage = await asyncio.to_thread(get_user_usage, uid)
    quota_gb = user.get("storage_quota", 20*1024*1024*1024) / (1024*1024*1024)
    used_gb = usage.get("storage_used", 0) / (1024*1024*1024)
    
    keyboard = [
        [InlineKeyboardButton("📁 My Files", callback_data="cloud_myfiles"),
         InlineKeyboardButton("👤 Profile", callback_data="cloud_profile")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="cloud_settings"),
         InlineKeyboardButton("🚪 Logout", callback_data="cloud_logout")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"☁️ *Cloud Dashboard*\n\n"
        f"👤 {update.effective_user.first_name}\n"
        f"💾 {used_gb:.2f} / {quota_gb:.0f} GB used\n"
        f"📄 {usage.get('file_count', 0)} files\n"
        f"🔗 {usage.get('share_count', 0)} share links\n\n"
        "Send me any file to save it!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def cloud_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cloud_register":
        await query.message.reply_text("Send /cloudregister to create an account.")
    elif data == "cloud_login":
        await query.message.reply_text("Send /cloudlogin to access your account.")
    elif data == "cloud_help":
        await show_cloud_help(query.message, context)
    elif data == "cloud_stats":
        await show_cloud_stats(query.message, context)
    elif data == "cloud_myfiles":
        from cloud_files import show_my_files
        await show_my_files(query, context)
    elif data == "cloud_profile":
        await show_profile(query, context)
    elif data == "cloud_settings":
        await show_settings(query, context)
    elif data == "cloud_logout":
        context.user_data.clear()
        await query.edit_message_text("✅ Logged out. Send /cloudstart to continue.")
    elif data == "cloud_chpass":
        await query.message.reply_text("Send /cloudstart then go to Settings to change password.")
    elif data == "cloud_chpin":
        await query.message.reply_text("Send /cloudstart then go to Settings to change PIN.")
    elif data == "cloud_back":
        await show_settings(query, context)

async def show_cloud_help(message, context):
    await message.reply_text(
        "☁️ *Cloud Saver Bot Help*\n\n"
        "📋 *Commands:*\n"
        "/start — Main menu\n"
        "/register — Create account\n"
        "/login — Login to account\n"
        "/logout — Logout\n"
        "/saved — View saved files\n"
        "/search <query> — Search files\n"
        "/genlink <file_index> — Generate share link\n"
        "/mylinks — View share links\n"
        "/profile — View profile\n"
        "/storage — Storage usage\n\n"
        "📤 *Upload:*\n"
        "Send any file, photo, video, or document to save it.\n"
        "Max size: 1 GB per file\n"
        "Cooldown: 5 seconds between uploads\n\n"
        "📊 *Limits:*\n"
        "• 30 uploads/hour\n"
        "• 300 uploads/day\n"
        "• 50 active share links\n"
        "• 20 GB storage",
        parse_mode="Markdown"
    )

async def show_cloud_stats(message, context):
    from cloud_db import get_user_count, get_total_storage
    user_count = await asyncio.to_thread(get_user_count)
    total_storage = await asyncio.to_thread(get_total_storage)
    total_gb = total_storage / (1024*1024*1024)
    await message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Users: {user_count}\n"
        f"💾 Total Storage: {total_gb:.2f} GB",
        parse_mode="Markdown"
    )

async def show_profile(query, context):
    uid = query.from_user.id
    user = await asyncio.to_thread(get_user, uid)
    if not user:
        return await query.edit_message_text("ℹ️ No account found.")
    usage = await asyncio.to_thread(get_user_usage, uid)
    from datetime import datetime
    created = user.get("created_at", "")
    if isinstance(created, datetime):
        created = created.strftime("%Y-%m-%d")
    quota_gb = user.get("storage_quota", 20*1024*1024*1024) / (1024*1024*1024)
    used_gb = usage.get("storage_used", 0) / (1024*1024*1024)
    await query.edit_message_text(
        f"👤 *Your Profile*\n\n"
        f"🆔 ID: `{uid}`\n"
        f"📛 Username: @{user.get('username', 'N/A')}\n"
        f"📅 Joined: {created}\n"
        f"💾 Storage: {used_gb:.2f} / {quota_gb:.0f} GB\n"
        f"📄 Files: {usage.get('file_count', 0)}\n"
        f"🔗 Shares: {usage.get('share_count', 0)}",
        parse_mode="Markdown"
    )

async def show_settings(query, context):
    keyboard = [
        [InlineKeyboardButton("🔑 Change Password", callback_data="cloud_chpass")],
        [InlineKeyboardButton("🔐 Change PIN", callback_data="cloud_chpin")],
        [InlineKeyboardButton("🔙 Back", callback_data="cloud_back")],
    ]
    await query.edit_message_text(
        "⚙️ *Settings*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def _get_verified_version(uid):
    db = get_cloud_db()
    doc = await asyncio.to_thread(db.user_verification.find_one, {"user_id": uid})
    return doc.get("verified_version", 0) if doc else 0

async def show_must_join(update: Update, context: ContextTypes.DEFAULT_TYPE, uid):
    channels = await get_required_channels()
    if not channels:
        return
    
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(
            f"➕ {ch['title']}", 
            url=ch.get("invite_link", f"https://t.me/{ch['title']}")
        )])
    buttons.append([InlineKeyboardButton("✅ Verify", callback_data="cloud_verify")])
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="cloud_verify")])
    
    await update.message.reply_text(
        "👋 *Welcome to Personal Cloud Saver Bot*\n\n"
        "Please join all required channels to continue.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
