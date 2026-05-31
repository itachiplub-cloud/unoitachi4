from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes, CommandHandler, ChatMemberHandler
from database import get_group_config, set_group_config  # You’ll need to define these

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return

    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.reply_text("🚫 Only admins can set the welcome message.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /welcomeset Welcome {name} to our group!")
        return

    set_group_config(update.effective_chat.id, "welcome_msg", text)
    await update.message.reply_text("✅ Welcome message set.")

async def set_farewell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return

    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.reply_text("🚫 Only admins can set the farewell message.")
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /setfarewell Goodbye {name}, we’ll miss you!")
        return

    set_group_config(update.effective_chat.id, "farewell_msg", text)
    await update.message.reply_text("✅ Farewell message set.")

async def member_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return

    status_change = update.chat_member.difference().get("status")
    chat_id = update.chat_member.chat.id

    if status_change == "joined":
        user = update.chat_member.new_chat_member.user
        msg_template = get_group_config(chat_id, "welcome_msg") or "👋 Welcome {name}!"
        msg = msg_template.format(name=user.full_name, username=user.username or "")
        await context.bot.send_message(chat_id=chat_id, text=msg)

    elif status_change == "left":
        user = update.chat_member.old_chat_member.user
        msg_template = get_group_config(chat_id, "farewell_msg") or "👻 Goodbye {name}!"
        msg = msg_template.format(name=user.full_name, username=user.username or "")
        await context.bot.send_message(chat_id=chat_id, text=msg)

def add_handlers(application):
    application.add_handler(CommandHandler("welcomeset", set_welcome))
    application.add_handler(CommandHandler("setfarewell", set_farewell))
    application.add_handler(ChatMemberHandler(member_update_handler, ChatMemberHandler.CHAT_MEMBER))