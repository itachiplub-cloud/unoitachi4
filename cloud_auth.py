import asyncio
import bcrypt
import secrets
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler

from cloud_db import (
    get_user, create_user, update_user,
    create_session, get_active_session, invalidate_session
)
from cloud_security import (
    check_pin_lock, record_pin_failure, reset_pin_lock,
    check_login_lock, record_login_failure, reset_login_lock
)
from cloud_config import DEFAULT_STORAGE_QUOTA

# Conversation states
WAITING_REG_PASSWORD = 1
WAITING_REG_PIN = 2
WAITING_LOGIN_PASSWORD = 3
WAITING_LOGIN_PIN = 4
WAITING_SEARCH = 5

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def hash_pin(pin):
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

def check_pin(pin, hashed):
    return bcrypt.checkpw(pin.encode(), hashed.encode())

def generate_session_token():
    return secrets.token_urlsafe(32)

# Registration flow
async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration - ask for password"""
    # Check if already registered
    uid = update.effective_user.id
    user = await asyncio.to_thread(get_user, uid)
    if user:
        return await update.message.reply_text("ℹ️ You already have an account. Use /login.")
    await update.message.reply_text(
        "📝 *Registration*\n\n"
        "Create a password for your cloud account.\n"
        "Requirements: at least 6 characters\n\n"
        "Send your password now (it will be hidden):",
        parse_mode="Markdown"
    )
    return WAITING_REG_PASSWORD

async def reg_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    if len(password) < 6:
        return await update.message.reply_text("❌ Password too short. Min 6 chars. Try again:")
    
    context.user_data["reg_password"] = hash_password(password)
    await update.message.delete()
    await update.message.reply_text(
        "🔐 Now set a 4-digit PIN for quick access.\n"
        "Send your PIN (4 digits):"
    )
    return WAITING_REG_PIN

async def reg_pin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text
    if not pin.isdigit() or len(pin) != 4:
        return await update.message.reply_text("❌ PIN must be exactly 4 digits. Try again:")
    
    context.user_data["reg_pin"] = hash_pin(pin)
    await update.message.delete()
    
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(uid)
    
    password_hash = context.user_data["reg_password"]
    doc = await asyncio.to_thread(create_user, uid, username, password_hash)
    
    await asyncio.to_thread(
        update_user, uid,
        pin_hash=context.user_data["reg_pin"],
        storage_quota=DEFAULT_STORAGE_QUOTA,
    )
    
    token = generate_session_token()
    await asyncio.to_thread(create_session, uid, token)
    context.user_data["session"] = token
    context.user_data["logged_in"] = True
    
    await update.message.reply_text(
        "✅ *Registration Complete!*\n\n"
        "Your cloud account is ready.\n"
        "💾 Storage: 20 GB\n\n"
        "Send me any file to save it!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Login flow
async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = await asyncio.to_thread(get_user, uid)
    if not user:
        return await update.message.reply_text("ℹ️ No account found. Use /register first.")
    
    if context.user_data.get("logged_in"):
        return await update.message.reply_text("ℹ️ You're already logged in. Use /logout first.")
    
    locked, remaining = await check_login_lock(uid)
    if locked:
        mins = remaining // 60
        return await update.message.reply_text(f"🔒 Account locked. Try again in {mins} min.")
    
    await update.message.reply_text(
        "🔐 *Login*\n\nSend your password:",
        parse_mode="Markdown"
    )
    return WAITING_LOGIN_PASSWORD

async def login_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    await update.message.delete()
    uid = update.effective_user.id
    
    user = await asyncio.to_thread(get_user, uid)
    if not user or not check_password(password, user.get("password_hash", "")):
        locked, duration = await record_login_failure(uid)
        if locked:
            mins = duration // 60
            return await update.message.reply_text(
                f"🔒 Too many failed attempts. Locked for {mins} min."
            )
        return await update.message.reply_text("❌ Wrong password. Try again:")
    
    await reset_login_lock(uid)
    await update.message.reply_text("🔐 Now send your 4-digit PIN:")
    return WAITING_LOGIN_PIN

async def login_pin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text
    await update.message.delete()
    uid = update.effective_user.id
    
    locked, remaining = await check_pin_lock(uid)
    if locked:
        mins = remaining // 60
        return await update.message.reply_text(f"🔒 PIN locked. Try again in {mins} min.")
    
    user = await asyncio.to_thread(get_user, uid)
    if not user or not check_pin(pin, user.get("pin_hash", "")):
        locked, duration = await record_pin_failure(uid)
        if locked:
            mins = duration // 60
            return await update.message.reply_text(
                f"🔒 Too many wrong PINs. Locked for {mins} min."
            )
        return await update.message.reply_text("❌ Wrong PIN. Try again:")
    
    await reset_pin_lock(uid)
    token = generate_session_token()
    await asyncio.to_thread(create_session, uid, token)
    context.user_data["session"] = token
    context.user_data["logged_in"] = True
    await update.message.reply_text(
        "✅ *Logged In!*\n\nSend me any file to save it!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = context.user_data.get("session")
    if session:
        await asyncio.to_thread(invalidate_session, uid)
    context.user_data.clear()
    await update.message.reply_text("✅ Logged out. Use /start to continue.")

def get_auth_conversation():
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("register", start_register),
            CommandHandler("login", start_login),
        ],
        states={
            WAITING_REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password_received)],
            WAITING_REG_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_pin_received)],
            WAITING_LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password_received)],
            WAITING_LOGIN_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_pin_received)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Cancelled."))],
    )
    return conv
