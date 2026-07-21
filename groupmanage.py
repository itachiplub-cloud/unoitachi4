from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler
from datetime import datetime, timedelta
from database import is_bot_admin

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return (
            member.status in ["administrator", "creator"]
            or is_bot_admin(user_id)
        )
    except:
        return False

async def handle_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can mute.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to mute them.")

    until_date = datetime.utcnow() + timedelta(hours=1)
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.from_user.id,
        ChatPermissions(can_send_messages=False),
        until_date=until_date
    )
    await update.message.reply_text(f"🔇 {target.from_user.full_name} has been muted for 1 hour.")

async def handle_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can unmute.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to unmute them.")

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.from_user.id,
        ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"🔊 {target.from_user.full_name} has been unmuted.")


async def handle_bam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can bam.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to bam them.")

    await update.message.reply_text(f"💥 {target.from_user.full_name} has been *BAMMED* here🫡 ... just kidding 🙂")

async def handle_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can kick.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to kick them.")

    await context.bot.ban_chat_member(update.effective_chat.id, target.from_user.id)
    await context.bot.unban_chat_member(update.effective_chat.id, target.from_user.id)
    await update.message.reply_text(f"👢 {target.from_user.full_name} has been kicked.")

warns = {}

async def handle_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can warn.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to warn them.")

    uid = target.from_user.id
    warns[uid] = warns.get(uid, 0) + 1

    if warns[uid] >= 3:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"🚨 {target.from_user.full_name} has been banned after 3 warnings.")
        warns[uid] = 0
    else:
        await update.message.reply_text(f"⚠️ Warning {warns[uid]} for {target.from_user.full_name}. 3 warnings = ban.")

async def handle_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can promote.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to promote them.")

    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            target.from_user.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        await update.message.reply_text(f"🛡️ {target.from_user.full_name} has been promoted to admin.")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Couldn't promote {target.from_user.full_name}.\n"
            f"Make sure I have 'Add New Admins' permission in this group.\n"
            f"Error: {e}"
        )

async def handle_demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can demote.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to demote them.")

    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            target.from_user.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        await update.message.reply_text(f"🧹 {target.from_user.full_name} has been demoted.")
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn't demote {target.from_user.full_name}. Error: {e}")

async def handle_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can pin messages.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a message to pin it.")

    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=target.message_id,
            disable_notification=True  # Set to False if you want to notify everyone
        )
        await update.message.reply_text("📌 Message has been pinned.")
    except:
        await update.message.reply_text("⚠️ Failed to pin the message.")

async def handle_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can unpin messages.")

    try:
        await context.bot.unpin_chat_message(chat_id=update.effective_chat.id)
        await update.message.reply_text("📍 The pinned message has been unpinned.")
    except:
        await update.message.reply_text("⚠️ Failed to unpin the message.")

async def handle_adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        names = [f"• {admin.user.full_name}" for admin in admins]
        await update.message.reply_text("🧙 Admins of this group:\n" + "\n".join(names))
    except:
        await update.message.reply_text("⚠️ Could not fetch admin list.")

async def handle_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can unban.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to unban them.")

    await context.bot.unban_chat_member(update.effective_chat.id, target.from_user.id)
    await update.message.reply_text(f"🔓 {target.from_user.full_name} has been unbanned.")

async def handle_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can unwarn.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to unwarn them.")

    uid = target.from_user.id
    if warns.get(uid, 0) > 0:
        warns[uid] = 0
        await update.message.reply_text(f"🧼 Warnings cleared for {target.from_user.full_name}.")
    else:
        await update.message.reply_text(f"✅ {target.from_user.full_name} has no warnings.")

async def handle_warnlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can view the warn list.")

    if not warns:
        return await update.message.reply_text("✅ No warnings issued yet.")

    lines = []
    for uid, count in warns.items():
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, uid)
            name = member.user.full_name
        except:
            name = str(uid)
        lines.append(f"• {name}: {count} warning(s)")

    await update.message.reply_text("⚠️ Warning Scroll:\n" + "\n".join(lines))

ban_log = []
_BAN_LOG_MAX = 100

async def handle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can ban.")

    target = update.message.reply_to_message
    if not target:
        return await update.message.reply_text("⚠️ Reply to a user to ban them.")

    await context.bot.ban_chat_member(update.effective_chat.id, target.from_user.id)
    ban_log.append((target.from_user.full_name, datetime.utcnow()))
    if len(ban_log) > _BAN_LOG_MAX:
        del ban_log[:len(ban_log) - _BAN_LOG_MAX]
    await update.message.reply_text(f"🚫 {target.from_user.full_name} has been banned.")

async def handle_banlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("⛔ Only admins can view the ban log.")

    if not ban_log:
        return await update.message.reply_text("✅ No bans recorded yet.")

    lines = [f"• {name} – {time.strftime('%Y-%m-%d %H:%M UTC')}" for name, time in ban_log]
    await update.message.reply_text("📕 Ban Ledger:\n" + "\n".join(lines))

def get_groupmanage_handlers():
    return [
        CommandHandler("slap", handle_mute),
        CommandHandler("unmute", handle_unmute),
        CommandHandler("kill", handle_ban),
        CommandHandler("unban", handle_unban), 
        CommandHandler("bam", handle_bam),
        CommandHandler("kick", handle_kick),
        CommandHandler("warn", handle_warn),
        CommandHandler("unwarn", handle_unwarn),
        CommandHandler("promote", handle_promote),
        CommandHandler("demote", handle_demote),
        CommandHandler("adminlist", handle_adminlist),
        CommandHandler("warnlist", handle_warnlist),
        CommandHandler("banlog", handle_banlog),
        CommandHandler("pin", handle_pin),
        CommandHandler("unpin", handle_unpin),


    ]