
from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes

group_messages = {}  # chat_id → {"welcome": "...", "farewell": "..."}

async def greet_chat_members(update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
    old = update.chat_member.old_chat_member.status
    new = update.chat_member.new_chat_member.status
    user = update.chat_member.new_chat_member.user
    chat_id = update.chat_member.chat.id

    name = user.full_name or user.username or str(user.id)
    msg_config = group_messages.get(chat_id, {})

    if old in ("left", "kicked") and new == "member":
        text = msg_config.get("welcome", f"👋 Welcome, <b>{name}</b>! May your journey be legendary.")
        await context.bot.send_message(chat_id, text, parse_mode="HTML")

    elif old in ("member", "administrator", "creator") and new in ("left", "kicked"):
        text = msg_config.get("farewell", f"😢 <b>{name}</b> has left the battlefield. 🪦")
        await context.bot.send_message(chat_id, text, parse_mode="HTML")

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.full_name or update.effective_user.username or str(update.effective_user.id)
    msg = group_messages.get(chat_id, {}).get("welcome", f"👋 Welcome, <b>{name}</b>!")
    await update.message.reply_text(msg, parse_mode="HTML")

async def farewell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.full_name or update.effective_user.username or str(update.effective_user.id)
    msg = group_messages.get(chat_id, {}).get("farewell", f"😢 <b>{name}</b> has left the battlefield.")
    await update.message.reply_text(msg, parse_mode="HTML")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        return await update.message.reply_text("⛔ Only group admins can set welcome messages.")

    text = " ".join(context.args).strip()
    if not text:
        return await update.message.reply_text("📝 Usage: /setwelcome <your message>")

    group_messages.setdefault(chat.id, {})["welcome"] = text
    await update.message.reply_text("✅ Welcome message updated.")

async def setfarewell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        return await update.message.reply_text("⛔ Only group admins can set farewell messages.")

    text = " ".join(context.args).strip()
    if not text:
        return await update.message.reply_text("📝 Usage: /setfarewell <your message>")

    group_messages.setdefault(chat.id, {})["farewell"] = text
    await update.message.reply_text("✅ Farewell message updated.")

async def viewwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        return await update.message.reply_text("⛔ Only group admins can view welcome settings.")

    config = group_messages.get(chat.id, {})
    welcome_msg = config.get("welcome", "👋 Default welcome message will be used.")
    farewell_msg = config.get("farewell", "🪦 Default farewell message will be used.")

    await update.message.reply_text(
        f"📜 <b>Current Welcome Settings</b>\n\n"
        f"👋 <b>Welcome Message:</b>\n{welcome_msg}\n\n"
        f"🪦 <b>Farewell Message:</b>\n{farewell_msg}",
        parse_mode="HTML"
    )
