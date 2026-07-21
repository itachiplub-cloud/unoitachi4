import asyncio
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import (
    is_bot_admin, is_owner, OWNER_ID,
    add_sudo_admin, remove_sudo_admin,
    get_sudo_admin_ids, get_sudo_admin_details,
    get_all_admin_ids, get_username,
    setup_admin_tables
)

setup_admin_tables()


async def addsudo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return await update.message.reply_text("🚫 Only the bot owner can add sudo admins.")

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
    else:
        if not context.args:
            return await update.message.reply_text(
                "Usage: /addsudo <user_id> [reason]\nor reply to a user's message with /addsudo"
            )
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")
        target_name = f"UID {target_id}"

    if is_bot_admin(target_id) and not is_owner(target_id):
        return await update.message.reply_text(f"⚠️ User {target_id} is already a sudo admin.")

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else None
    await asyncio.to_thread(add_sudo_admin, target_id, uid, reason)

    reason_text = f"\n📝 Reason: {reason}" if reason else ""
    await update.message.reply_text(
        f"✅ <b>Sudo Admin Added</b>\n"
        f"👤 {target_name}\n"
        f"🆔 <code>{target_id}</code>{reason_text}",
        parse_mode="HTML"
    )


async def rmsudo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return await update.message.reply_text("🚫 Only the bot owner can remove sudo admins.")

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        if not context.args:
            return await update.message.reply_text(
                "Usage: /rmsudo <user_id>\nor reply to a user's message with /rmsudo"
            )
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")

    if target_id == OWNER_ID:
        return await update.message.reply_text("🚫 Cannot remove the bot owner.")

    from config import ADMIN_IDS
    if target_id in ADMIN_IDS:
        return await update.message.reply_text(
            "⚠️ This user is a static admin (ADMIN_IDS env).\n"
            "Remove them from the ADMIN_IDS environment variable instead."
        )

    sudo_ids = await asyncio.to_thread(get_sudo_admin_ids)
    if target_id not in sudo_ids:
        return await update.message.reply_text(f"ℹ️ User {target_id} is not a sudo admin.")

    await asyncio.to_thread(remove_sudo_admin, target_id)
    await update.message.reply_text(f"✅ User {target_id} removed from sudo admins.")


async def sudolist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Admins only.")

    sudo_details = await asyncio.to_thread(get_sudo_admin_details)

    lines = ["🛡 <b>Bot Admin System</b>\n"]
    lines.append(f"👑 <b>Owner:</b> <code>{OWNER_ID}</code>\n")

    from config import ADMIN_IDS
    if ADMIN_IDS:
        lines.append(f"📋 <b>Static Admins (ADMIN_IDS env):</b>")
        for aid in sorted(ADMIN_IDS):
            role = "👑 Owner" if aid == OWNER_ID else "📋 Static"
            lines.append(f"  • <code>{aid}</code> — {role}")
        lines.append("")

    if sudo_details:
        lines.append(f"🔧 <b>Sudo Admins (dynamic):</b>")
        for user_id, added_by, added_at, reason in sudo_details:
            from datetime import datetime as _dt
            time_str = _dt.fromtimestamp(added_at).strftime("%Y-%m-%d") if added_at else "Unknown"
            reason_text = f" — {reason}" if reason else ""
            lines.append(f"  • <code>{user_id}</code> — Added {time_str}{reason_text}")
    else:
        lines.append("🔧 <b>Sudo Admins:</b> None")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def makeadmin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Admins only.")

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
    else:
        if not context.args:
            return await update.message.reply_text(
                "Usage: /makeadmin <user_id>\nor reply to a user's message with /makeadmin"
            )
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")
        target_name = f"UID {target_id}"

    from config import ADMIN_IDS
    all_admins = set(ADMIN_IDS) | set(await asyncio.to_thread(get_sudo_admin_ids))
    if target_id in all_admins:
        return await update.message.reply_text(f"ℹ️ User {target_id} is already an admin.")

    if not is_owner(uid):
        return await update.message.reply_text(
            "🚫 Only the bot owner can add sudo admins.\n"
            "Ask the owner to use /addsudo"
        )

    await asyncio.to_thread(add_sudo_admin, target_id, uid, "added via /makeadmin")
    await update.message.reply_text(
        f"✅ <b>{target_name}</b> is now a sudo admin!",
        parse_mode="HTML"
    )


async def demoteadmin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return await update.message.reply_text("🚫 Only the bot owner can demote admins.")

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        if not context.args:
            return await update.message.reply_text("Usage: /demoteadmin <user_id>")
        try:
            target_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")

    if target_id == OWNER_ID:
        return await update.message.reply_text("🚫 Cannot demote the bot owner.")

    from config import ADMIN_IDS
    if target_id in ADMIN_IDS:
        return await update.message.reply_text(
            "⚠️ This is a static admin (ADMIN_IDS env).\n"
            "Remove from ADMIN_IDS environment variable to revoke."
        )

    sudo_ids = await asyncio.to_thread(get_sudo_admin_ids)
    if target_id not in sudo_ids:
        return await update.message.reply_text(f"ℹ️ User {target_id} is not a sudo admin.")

    await asyncio.to_thread(remove_sudo_admin, target_id)
    await update.message.reply_text(f"✅ User {target_id} demoted from sudo admin.")


def get_admin_sudo_handlers():
    return [
        CommandHandler("addsudo", addsudo_handler),
        CommandHandler("rmsudo", rmsudo_handler),
        CommandHandler("sudolist", sudolist_handler),
        CommandHandler("makeadmin", makeadmin_handler),
        CommandHandler("demoteadmin", demoteadmin_handler),
    ]
