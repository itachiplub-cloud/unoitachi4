from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn, db_lock
from config import ADMIN_IDS
from database import get_all_group_ids

async def resetwallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET coins = 0")
            conn.commit()
    await update.message.reply_text("🧹 All user coin balances reset to ₹0.")

async def resetdeposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET bank = 0")
            conn.commit()
    await update.message.reply_text("🏦 All user deposits have been reset.")

async def resetbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE banktax SET coins = 0")
            conn.commit()
    await update.message.reply_text("🏛️ Central bank reserve wiped.")

async def resetinvestments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET locked_savings = 0")
            conn.commit()
    await update.message.reply_text("📉 All investment (locked savings) wiped.")

async def resetassets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM assets") 
            conn.commit()
    
    await update.message.reply_text("🧹 All user assets (from /myassets) have been reset.")

async def resettea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")

    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE user_stats SET coins_earned = 0")
            conn.commit()

    await update.message.reply_text("🧹 All /tea data has been reset.")

async def broadcastgroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    
    msg = " ".join(context.args)
    if not msg:
        return await update.message.reply_text("📝 Usage: /broadcastgroups Your message here")

    sent = 0
    for gid in get_all_group_ids():  # Uses your `get_all_group_ids()` from database.py
        try:
            await context.bot.send_message(gid, msg)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"📡 Sent to {sent} group(s).")

async def broadcastdms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")
    
    msg = " ".join(context.args)
    if not msg:
        return await update.message.reply_text("📝 Usage: /broadcastdms Your message here")

    sent = 0
    for uid in get_all_user_ids():  # Uses `get_all_user_ids()` from database.py
        try:
            await context.bot.send_message(uid, msg)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"📩 Sent to {sent} user(s) in DM.")


dm_links = {}  # uid → admin_id

async def dmchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user.id
    if sender not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")

    if len(context.args) < 2:
        return await update.message.reply_text("📝 Usage: /dmchat <user_id> <your message>")

    try:
        uid = int(context.args[0])
        msg = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=uid, text=f"📬 Message for you:\n{msg}")
        dm_links[uid] = sender  # Store who initiated the chat
        await update.message.reply_text(f"✅ Sent message to UID {uid}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send DM: {e}")

async def dm_reply_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = msg.from_user.id

    if uid not in dm_links:
        return  

    admin_id = dm_links[uid]
    reply_text = msg.text or "<non-text message>"

    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"📨 Reply from UID {uid}:\n{reply_text}"
        )
    except Exception as e:
        print(f"❌ Failed to forward reply: {e}")


from database import get_user_by_username

async def finduid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")

    if not context.args:
        return await update.message.reply_text("📝 Usage: /finduid @username")

    username = context.args[0]
    uid = get_user_by_username(username)

    if uid:
        await update.message.reply_text(f"🔍 UID of {username} is `{uid}`")
    else:
        await update.message.reply_text(f"❌ Username {username} not found in database.")


from games import raid_log
from database import get_username

async def wanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not raid_log:
        return await update.message.reply_text("🚓 No wanted posters yet. Streets are quiet.")

    msg = "🚨 <b>Recent Police Raids:</b>\n"
    for i, entry in enumerate(raid_log[-10:], start=1):  # Last 10 raids
        uid = entry["uid"]
        loss = entry["loss"]
        time = entry["timestamp"]
        username = get_username(uid) or "Unknown"
        msg += f"{i}. @{username} — ₹{loss} stolen at {time}\n"

    await update.message.reply_text(msg, parse_mode="HTML")


from database import get_user_by_username, get_username, get_balance, db_lock, get_conn
from games import set_global_raid, is_global_raid, raid_log
from telegram.constants import ParseMode
from datetime import datetime

from config import ADMIN_IDS  

async def raid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user.id
    if sender not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized to use this command.")

    if context.args and context.args[0].lower() in ["on", "off"]:
        mode = context.args[0].lower()
        set_global_raid(mode == "on")
        status = "activated" if mode == "on" else "deactivated"
        emoji = "🚨" if mode == "on" else "🧹"
        return await update.message.reply_text(
            f"{emoji} Global raid mode <b>{status.upper()}</b>. All players {'will be raided' if mode == 'on' else 'return to random chance'}.",
            parse_mode=ParseMode.HTML
        )

    if context.args and context.args[0].startswith("@"):
        username = context.args[0][1:]
        uid = get_user_by_username(username)
        if not uid:
            return await update.message.reply_text(f"❌ User @{username} not found.")

        bet = get_balance(uid)
        fine = 500
        total_loss = bet + fine

        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (total_loss, uid))
                conn.commit()

        raid_log.append({
            "uid": uid,
            "loss": total_loss,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "manual"
        })

        await context.bot.send_message(
            chat_id=uid,
            text="🚨 You’ve been manually raided by Reverse God Admins.\n💸 ₹500 fine + your wallet emptied.\n🕶️ Stay low — they’re watching you."
        )

        return await update.message.reply_text(f"✅ Manual raid triggered on @{username}. ₹{total_loss} confiscated.")

    return await update.message.reply_text(
        "⚠️ Usage:\n"
        "/raid on — activate global raids (100% chance)\n"
        "/raid off — deactivate raids\n"
        "/raid @username — manual bust\n"
    )

async def unraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user.id
    if sender not in ADMIN_IDS:
        return await update.message.reply_text("🚫 Not authorized.")

    set_global_raid(False)
    await update.message.reply_text("🧹 Global raid mode manually cleared. Streets back to stealth.")


from config import ADMIN_IDS
from database import get_conn, db_lock

async def cleartax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user.id
    if sender not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized to clear tax pool.")

    with db_lock:
        with get_conn() as conn:
            row = conn.execute("SELECT amount FROM tax_pool WHERE id = 1").fetchone()
            pool = row[0] if row else 0
            conn.execute("UPDATE tax_pool SET amount = 0 WHERE id = 1")
            conn.commit()

    return await update.message.reply_text(f"🧹 Tax pool cleared.\n💰 ₹{pool} removed from circulation.")

