from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.helpers import mention_html
from card_utils import get_username  

import json
import os

CIRCLE_FILE = "circle.json"
circle_of_presence = {}

def load_circle():
    global circle_of_presence
    if os.path.exists(CIRCLE_FILE):
        try:
            with open(CIRCLE_FILE, "r") as f:
                data = json.load(f)
                circle_of_presence = {int(k): set(v) for k, v in data.items()}
        except Exception as e:
            print(f"⚠️ Failed to load circle: {e}")

def save_circle():
    try:
        with open(CIRCLE_FILE, "w") as f:
            json.dump({str(k): list(v) for k, v in circle_of_presence.items()}, f)
    except Exception as e:
        print(f"⚠️ Failed to save circle: {e}")

async def track_group_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type in ["group", "supergroup"] and not user.is_bot:
        circle_of_presence.setdefault(chat.id, set()).add(user.id)
        save_circle()

from config import ADMIN_IDS 

async def handle_sab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.message
    user = update.effective_user
    uid = user.id

    is_group_admin = False
    try:
        member = await context.bot.get_chat_member(chat.id, uid)
        is_group_admin = member.status in ("administrator", "creator")
    except:
        pass

    if not is_group_admin and uid not in ADMIN_IDS:
        return await message.reply_text("⛔ Only group admins or bot admins can use /sab.")

    text = message.reply_to_message.text if message.reply_to_message else message.text.replace("/sab", "").strip()
    if not text:
        text = "🫵"

    members = circle_of_presence.get(str(chat.id), set())
    if not members:
        await message.reply_text("⚠️ No known members in this group yet.")
        return

    chunk_size = 6
    for i in range(0, len(members), chunk_size):
        chunk = list(members)[i:i + chunk_size]
        mentions = []

        for uid in chunk:
            try:
                member = await context.bot.get_chat_member(chat.id, uid)
                user = member.user
                display = user.username and f"@{user.username}" or user.full_name or str(uid)
            except:
                display = str(uid)

            mentions.append(mention_html(uid, display))

        formatted_mentions = "\n".join(mentions)
        await message.reply_html(f"{text}\n\n{formatted_mentions}")

async def handle_sahab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.message

    text = message.reply_to_message.text if message.reply_to_message else message.text.replace("/sahab", "").strip()
    if not text:
        text = "🫡"

    try:
        admins = await context.bot.get_chat_administrators(chat.id)
    except:
        return await message.reply_text("⚠️ Could not fetch admins.")

    if not admins:
        return await message.reply_text("📭 No admins found in this group.")

    chunk_size = 6
    admin_ids = [admin.user.id for admin in admins]

    for i in range(0, len(admin_ids), chunk_size):
        chunk = admin_ids[i:i + chunk_size]
        mentions = []

        for uid in chunk:
            try:
                member = await context.bot.get_chat_member(chat.id, uid)
                user = member.user
                display = user.username and f"@{user.username}" or user.full_name or str(uid)
            except:
                display = str(uid)

            mentions.append(mention_html(uid, display))

        await message.reply_html(f"{text}\n\n{' '.join(mentions)}")

async def handle_circle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not circle_of_presence:
        await update.message.reply_text("🌀 The circle is currently empty.")
        return

    user_lines = []
    for user_id in circle_of_presence:
        try:
            user = await context.bot.get_chat(user_id)
            name = user.full_name if user.full_name else str(user_id)
            link = f"https://t.me/{user.username}" if user.username else "(no link)"
            user_lines.append(f"🔗 [{name}]({link})")
        except Exception:
            user_lines.append(f"❓ Unknown user ({user_id})")

    response = "\n".join(user_lines)
    await update.message.reply_text(
        f"🌟 Circle of Presence:\n{response}",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_circle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    circle_of_presence.pop(chat_id, None)
    save_circle()
    await update.message.reply_text("🧹 Circle cleared.")



def load_circle():
    global circle_of_presence
    try:
        with open("circle.json", "r") as f:
            circle_of_presence = json.load(f)
            # Convert sets from JSON lists
            for gid in circle_of_presence:
                circle_of_presence[gid] = set(circle_of_presence[gid])
    except FileNotFoundError:
        circle_of_presence = {}

def save_circle():
    with open("circle.json", "w") as f:
        json.dump({gid: list(uids) for gid, uids in circle_of_presence.items()}, f)

async def track_group_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user or not chat.type in ["group", "supergroup"]:
        return

    group_id = str(chat.id)
    user_id = user.id

    if group_id not in circle_of_presence:
        circle_of_presence[group_id] = set()

    circle_of_presence[group_id].add(user_id)
    save_circle()

