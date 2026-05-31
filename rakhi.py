import datetime
import json
import os
import random
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ApplicationBuilder

import config

rakhi_bonds = {}       # {(sender_id, target_id): {vow, timestamp}}
rakhi_archive = {}     # {(sender_id, target_id): {vow, tied_at, untied_at}}

RAKHI_WALL_FILE = "rakhi_wall.json"

poetic_wishes = [
    "🪔 May your bond be a thread of fire and faith.",
    "🧵 May your silence be guarded and your chaos honored.",
    "🌙 May your name be safe in someone else's ritual.",
    "🕊️ May your Rakhi carry memory, meaning, and magic.",
    "💫 May your bond echo even when words fall away."
]

def load_rakhi_wall():
    if os.path.exists(RAKHI_WALL_FILE):
        try:
            with open(RAKHI_WALL_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and all(isinstance(entry, dict) for entry in data):
                    return data
        except Exception as e:
            print(f"⚠️ Error loading Rakhi Wall: {e}")
    return []

def save_rakhi_wall(wall):
    with open(RAKHI_WALL_FILE, "w") as f:
        json.dump(wall, f, indent=2)

def format_bond(vow, timestamp):
    time_str = timestamp.strftime("%b %d, %Y at %I:%M %p")
    vow_text = f"💬 Vow: \"{vow}\"" if vow else "💬 Vow: None"
    time_text = f"🕰️ Tied on {time_str}"
    return vow_text, time_text

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE, args: str):
    message = update.message

    if message.reply_to_message:
        return message.reply_to_message.from_user

    elif args:
        for entity in message.entities:
            if entity.type == "mention":
                username = message.text[entity.offset:entity.offset + entity.length]
                try:
                    return await context.bot.get_chat(username)
                except Exception:
                    await message.reply_text("⚠️ I can't access that user. Please reply to their message instead.")
                    return None

    await message.reply_text("🧵 Please reply to someone's message or mention a known user.")
    return None

async def handle_rakhi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.replace('/rakhi', '').strip()
    sender = update.message.from_user
    target = await get_target_user(update, context, args)

    if not target:
        return

    vow = None
    if '|' in args:
        parts = args.split('|')
        if len(parts) > 1:
            vow = parts[1].strip()

    timestamp = datetime.datetime.now()
    rakhi_bonds[(sender.id, target.id)] = {
        'vow': vow,
        'timestamp': timestamp
    }

    wall = load_rakhi_wall()
    wall.append({
        "from_id": sender.id,
        "from_name": sender.full_name,
        "to_id": target.id,
        "to_name": target.full_name,
        "vow": vow,
        "timestamp": timestamp.isoformat()
    })
    save_rakhi_wall(wall)

    vow_text, time_text = format_bond(vow, timestamp)
    response = (
        f"🧵 {sender.full_name} has tied a Rakhi to {target.full_name}.\n"
        f"{vow_text}\n"
        f"{time_text}\n"
        f"🎁 Perk unlocked: Reverse Immunity (1 day)"
    )
    await update.message.reply_text(response)

async def handle_rakhibond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.message.from_user.id
    bonds = [((s, t), data) for ((s, t), data) in rakhi_bonds.items() if s == sender_id]

    if not bonds:
        await update.message.reply_text("🧵 You haven’t tied any Rakhis yet.")
        return

    lines = ["🧵 Your Rakhi Bonds:\n"]
    for (s, t), data in bonds:
        user = await context.bot.get_chat(t)
        vow_text, time_text = format_bond(data['vow'], data['timestamp'])
        lines.append(f"{user.full_name} — {time_text}\n{vow_text}\n")

    await update.message.reply_text("\n".join(lines))

async def handle_rakhiuntie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.replace('/rakhiuntie', '').strip()
    sender = update.message.from_user
    target = await get_target_user(update, context, args)

    if not target:
        return

    key = (sender.id, target.id)
    if key in rakhi_bonds:
        bond = rakhi_bonds.pop(key)
        rakhi_archive[key] = {
            'vow': bond['vow'],
            'tied_at': bond['timestamp'],
            'untied_at': datetime.datetime.now()
        }
        await update.message.reply_text(f"🧵 {sender.full_name} has untied the Rakhi from {target.full_name}.\n🕊️ May the bond rest in memory.")
    else:
        await update.message.reply_text("🧵 No Rakhi bond found to untie.")

async def handle_rakhiwrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.replace('/rakhiwrite', '').strip()
    sender = update.message.from_user
    target = await get_target_user(update, context, args)

    if not target or '|' not in args:
        await update.message.reply_text("🧵 Use /rakhiwrite @username | Your vow here.")
        return

    parts = args.split('|')
    if len(parts) < 2:
        await update.message.reply_text("🧵 Please include a vow after '|'.")
        return

    vow = parts[1].strip()
    key = (sender.id, target.id)
    if key in rakhi_bonds:
        rakhi_bonds[key]['vow'] = vow
        await update.message.reply_text(f"🧵 Vow updated for Rakhi to {target.full_name}:\n💬 \"{vow}\"")
    else:
        await update.message.reply_text("🧵 No Rakhi bond found. Tie one first using /rakhi.")

async def handle_rakhiwish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.replace('/rakhiwish', '').strip()
    target = await get_target_user(update, context, args)

    if not target:
        return

    wish = random.choice(poetic_wishes)
    await update.message.reply_text(f"🪔 Raksha Bandhan wish to {target.full_name}:\n{wish}")

async def handle_rakhiwall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wall = load_rakhi_wall()
    if not wall:
        await update.message.reply_text("🧱 No Rakhi bonds yet.")
        return

    lines = ["🧱 Rakhi Wall — Threads of Bond:\n"]
    for entry in wall:
        dt = datetime.datetime.fromisoformat(entry["timestamp"])
        time_str = dt.strftime("%b %d, %Y at %I:%M %p")
        vow_text = f"💬 Vow: \"{entry['vow']}\"" if entry["vow"] else "💬 Vow: None"
        to_link = f"[{entry['to_name']}](tg://user?id={entry['to_id']})"
        from_link = f"[{entry['from_name']}](tg://user?id={entry['from_id']})"
        lines.append(f"{from_link} → {to_link}\n{vow_text}\n🕰️ Tied on {time_str}\n")

    await update.message.reply_markdown("\n".join(lines))

async def handle_rakhiarchive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rakhi_archive:
        await update.message.reply_text("📚 No archived Rakhi bonds yet.")
        return

    lines = ["📚 Rakhi Archive — Bonds Remembered:\n"]
    for (s, t), data in rakhi_archive.items():
        sender = await context.bot.get_chat(s)
        target = await context.bot.get_chat(t)
        tied_str = data['tied_at'].strftime("%b %d, %Y at %I:%M %p")
        untied_str = data['untied_at'].strftime("%b %d, %Y at %I:%M %p")
        vow_text = f"💬 Vow: \"{data['vow']}\"" if data['vow'] else "💬 Vow: None"
        from_link = f"[{sender.full_name}](tg://user?id={sender.id})"
        to_link = f"[{target.full_name}](tg://user?id={target.id})"
        lines.append(
            f"{from_link} → {to_link}\n"
            f"{vow_text}\n"
            f"🕰️ Tied: {tied_str} | Untied: {untied_str}\n"
        )

    await update.message.reply_markdown("\n".join(lines))


async def handle_rakhitop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wall = load_rakhi_wall()
    if not wall:
        await update.message.reply_text("🏆 No Rakhi bonds yet.")
        return

    tally = {}
    for entry in wall:
        to_id = entry["to_id"]
        to_name = entry["to_name"]
        tally[to_id] = tally.get(to_id, {"name": to_name, "count": 0})
        tally[to_id]["count"] += 1

    max_count = max(user["count"] for user in tally.values())
    top_users = [user for user in tally.values() if user["count"] == max_count]

    now = datetime.datetime.now()
    end_of_day = now.replace(hour=23, minute=59, second=59)

    lines = [f"🏆 Rakhi Leaderboard — {now.strftime('%b %d')}"]

    if now >= end_of_day:
        for user in top_users:
            lines.append(
                f"👑 {user['name']} received {user['count']} Rakhis.\n"
                f"🎖️ Awarded: 100,000 Itachi Coins\n"
                f"🪔 May their bond be remembered in tomorrow’s thread."
            )
    else:
        sorted_users = sorted(tally.values(), key=lambda u: u["count"], reverse=True)
        for user in sorted_users:
            lines.append(f"🧵 {user['name']} — {user['count']} Rakhis")

        lines.append("\n🌅 Final winner will be crowned at midnight.\n🎖️ Reward: 100,000 Itachi Coins")

    await update.message.reply_text("\n".join(lines))


def main():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("rakhi", handle_rakhi))
    app.add_handler(CommandHandler("rakhibond", handle_rakhibond))
    app.add_handler(CommandHandler("rakhiuntie", handle_rakhiuntie))
    app.add_handler(CommandHandler("rakhiwrite", handle_rakhiwrite))
    app.add_handler(CommandHandler("rakhiwish", handle_rakhiwish))
    app.add_handler(CommandHandler("rakhiwall", handle_rakhiwall))
    app.add_handler(CommandHandler("rakhiarchive", handle_rakhiarchive))
    app.add_handler(CommandHandler("rakhitop", handle_rakhitop))

    print("🧵 Rakhi bot is now weaving bonds...")
    app.run_polling()

if __name__ == "__main__":
    main()
