import asyncio
import time
from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn
from config import ADMIN_IDS

def setup_giveaway_card_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                rarity TEXT,
                value INTEGER,
                description TEXT,
                image_file_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_giveaway_cards (
                uid INTEGER,
                card_id INTEGER,
                assigned_at INTEGER,
                PRIMARY KEY (uid, card_id)
            )
        """)

def migrate_giveaway_card_table():
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE giveaway_cards ADD COLUMN value INTEGER DEFAULT 0")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Migration error: {e}")

def add_giveaway_card(name, rarity, value, description, image_file_id):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO giveaway_cards (name, rarity, value, description, image_file_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, rarity, value, description, image_file_id))
        conn.commit()

def assign_card_to_user(uid, card_id):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO user_giveaway_cards (uid, card_id, assigned_at)
            VALUES (?, ?, ?)
        """, (uid, card_id, int(time.time())))
        conn.commit()

def get_user_giveaway_cards(uid):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT g.name, g.rarity, g.value, g.description, u.assigned_at
            FROM giveaway_cards g
            JOIN user_giveaway_cards u ON g.card_id = u.card_id
            WHERE u.uid = ?
            ORDER BY u.assigned_at DESC
        """, (uid,)).fetchall()
    return rows

def get_all_giveaway_cards():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT card_id, name, rarity, value, description
            FROM giveaway_cards
            ORDER BY card_id DESC
        """).fetchall()
    return rows

def remove_giveaway_card(uid, card_id):
    with get_conn() as conn:
        conn.execute("""
            DELETE FROM user_giveaway_cards
            WHERE uid = ? AND card_id = ?
        """, (uid, card_id))
        conn.commit()

def delete_giveaway_card(card_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM giveaway_cards WHERE card_id = ?", (card_id,))
        conn.execute("DELETE FROM user_giveaway_cards WHERE card_id = ?", (card_id,))
        conn.commit()


def migrate_giveaway_card_table():
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE giveaway_cards ADD COLUMN image_file_id TEXT")
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Migration error: {e}")


async def uploadgiveawaycard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized.")

    replied = update.message.reply_to_message
    if not replied or not replied.photo:
        return await update.message.reply_text(
            "⚠️ Reply to a photo and use caption:\n<name> | <rarity> | <value> | <description>"
        )

    try:
        caption = replied.caption or replied.text or ""
        name, rarity, value, description = map(str.strip, caption.split("|"))
        value = int(value)
        description += " — SPECIAL EDITION (Not available from draw)"
        image_file_id = replied.photo[-1].file_id

        add_giveaway_card(name, rarity, value, description, image_file_id)
        await update.message.reply_text(
            f"✅ <b>{name}</b> added as a SPECIAL EDITION card with value <b>{value}</b>.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Failed to upload card. Make sure your caption is formatted like:\n<name> | <rarity> | <value> | <description>\n\nError: {e}"
        )


async def editgiveawaycardbyindex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized.")
    try:
        raw = " ".join(context.args)
        index, name, rarity, value, description = map(str.strip, raw.split("|"))
        index = int(index)
        value = int(value)
        card = get_all_giveaway_cards()[index - 1]
        card_id = card[0]
        with get_conn() as conn:
            conn.execute("""
                UPDATE giveaway_cards
                SET name = ?, rarity = ?, value = ?, description = ?
                WHERE card_id = ?
            """, (name, rarity, value, description, card_id))
            conn.commit()
        await update.message.reply_text(f"✅ Card ID {card_id} updated.")
    except:
        await update.message.reply_text(
            "⚠️ Usage:\n/editgiveawaycardbyindex <index> | <name> | <rarity> | <value> | <description>"
        )

async def givecard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized.")
    try:
        card_index = int(context.args[0])
        card_id = get_all_giveaway_cards()[card_index - 1][0]

        if update.message.reply_to_message:
            target_uid = update.message.reply_to_message.from_user.id
        else:
            username = context.args[1].lstrip("@")
            user = await context.bot.get_chat(username)
            target_uid = user.id

        assign_card_to_user(target_uid, card_id)
        await update.message.reply_text(f"✅ Card ID {card_id} given to user {target_uid}.")
    except:
        await update.message.reply_text("⚠️ Usage:\n/givecard <card_index> [@username or reply]")

async def mygiveaways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    def _db_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT g.name, g.rarity, g.value, g.description, g.image_file_id
                FROM giveaway_cards g
                JOIN user_giveaway_cards u ON g.card_id = u.card_id
                WHERE u.uid = ?
                ORDER BY u.assigned_at DESC
            """, (uid,)).fetchall()
    rows = await asyncio.to_thread(_db_op)

    if not rows:
        return await update.message.reply_text("🎁 You don’t have any giveaway cards yet.")

    for name, rarity, value, desc, image_file_id in rows:
        caption = f"<b>{name}</b> ({rarity}) — 💰 {value} coins\n{desc}"
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_file_id,
            caption=caption,
            parse_mode="HTML"
        )

async def giveawaylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You're not authorized.")
    def _db_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT u.uid, g.name, g.rarity, g.value
                FROM user_giveaway_cards u
                JOIN giveaway_cards g ON u.card_id = g.card_id
                ORDER BY u.assigned_at DESC
            """).fetchall()
    rows = await asyncio.to_thread(_db_op)
    if not rows:
        return await update.message.reply_text("📭 No cards assigned yet.")
    lines = ["📋 <b>Assigned Giveaway Cards</b>"]
    for uid, name, rarity, value in rows:
        lines.append(f"• <b>{name}</b> ({rarity}) — 💰 {value} → <a href='tg://user?id={uid}'>User</a>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def removegivecard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized.")
    try:
        card_index = int(context.args[0])
        card_id = get_all_giveaway_cards()[card_index - 1][0]

        if update.message.reply_to_message:
            target_uid = update.message.reply_to_message.from_user.id
        else:
            username = context.args[1].lstrip("@")
            user = await context.bot.get_chat(username)
            target_uid = user.id

        remove_giveaway_card(target_uid, card_id)
        await update.message.reply_text(f"❌ Card ID {card_id} removed from user {target_uid}.")
    except:
        await update.message.reply_text("⚠️ Usage:\n/removegivecard <card_index> [@username or reply]")

async def giveawaycards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = get_all_giveaway_cards()
    if not cards:
        return await update.message.reply_text("📭 No giveaway cards available.")

    lines = ["🎁 <b>Available Giveaway Cards</b>"]
    for i, (card_id, name, rarity, value, desc) in enumerate(cards, 1):
        lines.append(f"{i}. <b>{name}</b> ({rarity}) — 💰 {value} coins\n{desc}")

    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")

async def deletegiveawaycard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You’re not authorized.")
    try:
        index = int(context.args[0])
        cards = get_all_giveaway_cards()
        if index < 1 or index > len(cards):
            return await update.message.reply_text("⚠️ Invalid card index.")

        card_id = cards[index - 1][0]
        delete_giveaway_card(card_id)
        await update.message.reply_text(f"🗑️ Card ID {card_id} deleted from system.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Usage:\n/deletegiveawaycard <card_index>\nError: {e}")

