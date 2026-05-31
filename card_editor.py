import json
import time
from telegram import Update
from telegram.ext import ContextTypes
from database import get_conn
from telegram.ext import CommandHandler, CallbackQueryHandler
with open("config.json", "r") as f:
    config = json.load(f)
admin_ids = config.get("ADMIN_IDS", [])

bulk_upload_sessions = set()
admin_card_cache = {}  


import json
from database import get_conn

async def uploadcard(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    reply = update.message.reply_to_message
    if not reply or not reply.photo or not reply.caption:
        return await update.message.reply_text("📸 Reply to a photo with caption.\n📝 Format:\nname | power | value | rarity | cost")

    file_id = reply.photo[-1].file_id
    parts = [p.strip() for p in reply.caption.split("|")]

    if len(parts) != 5:
        return await update.message.reply_text("⚠️ Invalid format.\nUse: name | power | value | rarity | cost")

    name, power, value, rarity, cost = parts

    try:
        card_json = json.dumps({
            "name": name,
            "power": power,
            "value": int(value),
            "rarity": rarity.lower(),
            "cost": int(cost),
            "file_id": file_id
        })
    except:
        return await update.message.reply_text("🚫 Invalid values. Power, value, and cost must be numbers.")

    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO deck (file_id, json) VALUES (?, ?)", (file_id, card_json))
        conn.commit()

    await update.message.reply_text(f"✅ Card '{name}' uploaded to deck for drawing.")


from database import get_conn
import json, time
from telegram import Update
from telegram.ext import ContextTypes
from card_utils import draw_card

async def draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    with get_conn() as conn:
        row = conn.execute("SELECT coins FROM users WHERE id = ?", (uid,)).fetchone()
        coins = row[0] if row else 0

    cost = 100
    if coins < cost:
        return await update.message.reply_text("💸 Not enough coins to draw a card.")

    card = draw_card()

    if not card["file_id"] or card["file_id"] == "None" or len(card["file_id"]) < 10:
        return await update.message.reply_text("⚠️ This card has a broken image. Please contact admin or use /deckclean.")

    now = int(time.time())
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_cards (uid, file_id, name, power, value, rarity, drawn_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            card["file_id"],
            card["name"],
            card["power"],
            card["value"],
            card["rarity"],
            now
        ))

        conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (cost, uid))

        # Auto-sync to deck
        exists = conn.execute("SELECT 1 FROM deck WHERE file_id = ?", (card["file_id"],)).fetchone()
        if not exists:
            conn.execute("INSERT INTO deck (file_id, json) VALUES (?, ?)", (card["file_id"], json.dumps(card)))

        conn.commit()

    with get_conn() as conn:
        row = conn.execute("SELECT coins FROM users WHERE id = ?", (uid,)).fetchone()
        new_balance = row[0] if row else 0

    caption = (
        f"🎴 Card Drawn by <b>{name}</b>\n"
        f"🪄 Name: <b>{card['name']}</b>\n"
        f"🔥 Power: {card['power']}\n"
        f"💥 Value: {card['value']} coins\n"
        f"💠 Rarity: {card['rarity'].title()}\n"
        f"💸 Cost: {cost}\n"
        f"💰 Remaining: {new_balance}"
    )

    await update.message.reply_photo(photo=card["file_id"], caption=caption, parse_mode="HTML")



from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from database import get_conn
import json

def build_card_keyboard(index, total):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"card_prev"),
            InlineKeyboardButton("Next ▶️", callback_data=f"card_next")
        ],
        [
            InlineKeyboardButton("📜 View Collection", callback_data="card_collection"),
            InlineKeyboardButton("🆔 Card ID", callback_data="card_id")
        ]
    ])

from telegram import Update, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

async def mycards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT uc.file_id, d.json
            FROM user_cards uc
            JOIN deck d ON uc.file_id = d.file_id
            WHERE uc.uid = ?
            ORDER BY uc.drawn_at DESC
            LIMIT 5
        """, (uid,)).fetchall()

    if not rows:
        return await update.message.reply_text("📭 You have no cards.")

    cards = []
    for file_id, raw_json in rows:
        if not file_id or file_id == "None" or len(file_id) < 10:
            continue
        try:
            card = json.loads(raw_json)
            cards.append({
                "file_id": file_id,
                "name": card.get("name", "Unknown"),
                "power": card.get("power", "None"),
                "rarity": card.get("rarity", "Common").title(),
                "value": card.get("value", 0),
                "id": card.get("id", "Unknown")
            })
        except Exception as e:
            print(f"⚠️ Failed to load card: {e}")
            continue

    if not cards:
        return await update.message.reply_text("📭 You have no valid cards.")

    context.user_data["cards"] = cards
    context.user_data["card_index"] = 0

    card = cards[0]
    caption = (
        f"🃏 <b>{card['name']}</b>\n"
        f"🔮 Power: {card['power']}\n"
        f"🎴 Rarity: {card['rarity']}\n"
        f"💰 Value: {card['value']}"
    )
    keyboard = build_card_keyboard(0, len(cards))

    try:
        await update.message.reply_photo(
            photo=card["file_id"],
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"⚠️ Failed to send card photo: {e}")
        await update.message.reply_text(
            f"{caption}\n\n⚠️ Image not available.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

from telegram import Update, InputMediaPhoto, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

async def card_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    cards = context.user_data.get("cards", [])
    index = context.user_data.get("card_index", 0)

    if not cards:
        try:
            await query.edit_message_caption("📭 No cards loaded.")
        except Exception:
            await query.edit_message_text("📭 No cards loaded.")
        return

    data = query.data
    if data == "card_next":
        index = (index + 1) % len(cards)
    elif data == "card_prev":
        index = (index - 1) % len(cards)
    elif data == "card_collection":
        collection_text = "\n\n".join([
            f"🃏 <b>{c['name']}</b>\n🔮 Power: {c['power']}\n🎴 Rarity: {c['rarity']}\n💰 Value: {c['value']}"
            for c in cards
        ])
        return await query.edit_message_text(collection_text, parse_mode=ParseMode.HTML)
    elif data == "card_id":
        card = cards[index]
        return await query.edit_message_text(
            f"🆔 Card ID: <code>{card['id']}</code>",
            parse_mode=ParseMode.HTML
        )

    context.user_data["card_index"] = index
    card = cards[index]
    caption = (
        f"🃏 <b>{card['name']}</b>\n"
        f"🔮 Power: {card['power']}\n"
        f"🎴 Rarity: {card['rarity']}\n"
        f"💰 Value: {card['value']}"
    )
    keyboard = build_card_keyboard(index, len(cards))

    try:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=card["file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"⚠️ Failed to update card media: {e}")
        try:
            await query.edit_message_caption(
                caption=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e2:
            print(f"⚠️ Failed to update caption fallback: {e2}")
            try:
                await query.edit_message_text("❌ Failed to display card.")
            except Exception as e3:
                print(f"🧨 Final fallback failed: {e3}")

def get_card_handlers():
    return [
        CommandHandler("mycards", mycards),
        CallbackQueryHandler(card_callback, pattern="^card_")
    ]

async def mycardstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT d.json
            FROM user_cards uc
            JOIN deck d ON uc.file_id = d.file_id
            WHERE uc.uid = ?
        """, (uid,)).fetchall()

    if not rows:
        return await update.message.reply_text("📭 You have no cards.")

    rarity_count = {}
    total = 0

    for (raw_json,) in rows:
        try:
            card = json.loads(raw_json)
            rarity = card.get("rarity", "common").lower()
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            total += 1
        except:
            continue

    lines = [f"📊 <b>Your Card Stats:</b>\nTotal Cards: {total}"]
    for rarity, count in sorted(rarity_count.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"🎴 {rarity.title()}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


admin_card_cache = {}  

async def admincards(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    from database import get_conn
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()

    admin_card_cache[uid] = rows  

    messages = []
    for i, (file_id, raw_json) in enumerate(rows):
        try:
            card = json.loads(raw_json)
            messages.append(
                f"{i+1}. 🃏 <b>{card.get('name', 'Unknown')}</b>\n"
                f"🔥 Power: {card.get('power')}, 💰 Value: {card.get('value')}, 💠 Rarity: {card.get('rarity')}, 💸 Cost: {card.get('cost')}"
            )
        except:
            continue

    await update.message.reply_text("\n\n".join(messages), parse_mode="HTML")

async def purgecard(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("⛔ Only admins can purge cards.")

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("🗑️ Usage: /purgecard <index_number>")

    index = int(context.args[0]) - 1

    if uid not in admin_card_cache or index >= len(admin_card_cache[uid]):
        return await update.message.reply_text("❌ Invalid index. Use /admincards first.")

    file_id, raw_json = admin_card_cache[uid][index]
    try:
        card = json.loads(raw_json)
        name = card.get("name", "Unknown")
    except:
        return await update.message.reply_text("⚠️ Failed to parse card.")

    with get_conn() as conn:
        conn.execute("DELETE FROM deck WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM user_cards WHERE LOWER(name) = ?", (name.lower(),))
        conn.execute("DELETE FROM tomb WHERE LOWER(name) = ?", (name.lower(),))
        conn.commit()

    await update.message.reply_text(
        f"🧨 Card <b>{name}</b> purged from all known bot tables.",
        parse_mode="HTML"
    )


async def editcard(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    args = context.args
    if len(args) < 3:
        return await update.message.reply_text("📝 Format: /editcard <index> <field> <new_value>")

    try:
        index = int(args[0]) - 1
        field = args[1].lower()
        new_value = " ".join(args[2:])
    except:
        return await update.message.reply_text("⚠️ Invalid input format.")

    if uid not in admin_card_cache or index >= len(admin_card_cache[uid]):
        return await update.message.reply_text("❌ Invalid index. Use /admincards first.")

    file_id, raw_json = admin_card_cache[uid][index]
    try:
        card = json.loads(raw_json)
        if field not in card:
            return await update.message.reply_text(f"⚠️ Field '{field}' not found in card.")

        if field in ["power", "value", "cost"]:
            new_value = int(new_value)

        card[field] = new_value

        from database import get_conn
        with get_conn() as conn:
            conn.execute("UPDATE deck SET json = ? WHERE file_id = ?", (json.dumps(card), file_id))
            conn.commit()

        await update.message.reply_text(f"✅ Updated card '{card['name']}' → {field} = {new_value}")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        await update.message.reply_text("❌ Failed to update card.")




import json
from database import get_conn

async def editcardbyindex(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    if len(context.args) < 3:
        return await update.message.reply_text("✏️ Usage: /editcardbyindex <index> <field> <new_value>")

    index = context.args[0]
    field = context.args[1].lower()
    new_value = " ".join(context.args[2:])
    allowed_fields = ["name", "power", "value", "rarity", "cost"]

    if field not in allowed_fields:
        return await update.message.reply_text(f"⚠️ Invalid field. Allowed: {', '.join(allowed_fields)}")

    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck ORDER BY rowid").fetchall()
        if not rows or not index.isdigit() or int(index) < 1 or int(index) > len(rows):
            return await update.message.reply_text("❌ Invalid index. Use /admincards to see valid indexes.")

        file_id, raw_json = rows[int(index) - 1]
        try:
            card = json.loads(raw_json)
            if field in ["value", "cost"]:
                new_value = int(new_value)
            card[field] = new_value
            updated_json = json.dumps(card)
            conn.execute("UPDATE deck SET json = ? WHERE file_id = ?", (updated_json, file_id))
            conn.commit()
            await update.message.reply_text(f"✅ Updated card #{index}: {field} → {new_value}")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to update card: {e}")


import json
from database import get_conn

async def decksync(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, name, power, value, rarity FROM user_cards").fetchall()
        deck_ids = {row[0] for row in conn.execute("SELECT file_id FROM deck").fetchall()}

    added = 0
    for file_id, name, power, value, rarity in rows:
        if file_id and file_id not in deck_ids:
            card = {
                "name": name,
                "power": power,
                "value": value,
                "rarity": rarity,
                "cost": 100,
                "file_id": file_id
            }
            with get_conn() as conn:
                conn.execute("INSERT INTO deck (file_id, json) VALUES (?, ?)", (file_id, json.dumps(card)))
                conn.commit()
            added += 1

    await update.message.reply_text(f"✅ Synced {added} missing cards into deck.")


import time
from database import get_conn
from card_utils import draw_card_by_rarity

COOLDOWN_SECONDS = 300  
DRAW_COST = 1000

async def draw(update, context):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    now = int(time.time())

    with get_conn() as conn:
        user = conn.execute("SELECT coins, last_draw_time FROM users WHERE id = ?", (uid,)).fetchone()
        coins = user[0] if user else 0
        last_draw = user[1] if user and user[1] else 0

        if now - last_draw < COOLDOWN_SECONDS:
            remaining = COOLDOWN_SECONDS - (now - last_draw)
            return await update.message.reply_text(f"⏳ Please wait {remaining} seconds before drawing again.")

        if coins < DRAW_COST:
            return await update.message.reply_text("💸 Not enough coins to draw a card.")

    card = draw_card_by_rarity()

    if not card["file_id"] or card["file_id"] == "None" or len(card["file_id"]) < 10:
        return await update.message.reply_text("⚠️ This card has a broken image. Please contact admin or use /deckclean.")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_cards (uid, file_id, name, power, value, rarity, drawn_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            card["file_id"],
            card["name"],
            card["power"],
            card["value"],
            card["rarity"],
            now
        ))

        conn.execute("UPDATE users SET coins = coins - ?, last_draw_time = ? WHERE id = ?", (DRAW_COST, now, uid))

        exists = conn.execute("SELECT 1 FROM deck WHERE file_id = ?", (card["file_id"],)).fetchone()
        if not exists:
            conn.execute("INSERT INTO deck (file_id, json) VALUES (?, ?)", (card["file_id"], json.dumps(card)))

        conn.commit()

    with get_conn() as conn:
        row = conn.execute("SELECT coins FROM users WHERE id = ?", (uid,)).fetchone()
        new_balance = row[0] if row else 0

    caption = (
        f"🎴 Card Drawn by <b>{name}</b>\n"
        f"🪄 Name: <b>{card['name']}</b>\n"
        f"🔥 Power: {card['power']}\n"
        f"💥 Value: {card['value']} coins\n"
        f"💠 Rarity: {card['rarity'].title()}\n"
        f"💸 Cost: {DRAW_COST}\n"
        f"💰 Remaining: {new_balance}"
    )

    await update.message.reply_photo(photo=card["file_id"], caption=caption, parse_mode="HTML")


from database import get_conn

async def deckclean(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()

    removed = 0
    seen = set()
    for file_id, raw_json in rows:
        if not file_id or file_id in seen:
            with get_conn() as conn:
                conn.execute("DELETE FROM deck WHERE file_id = ?", (file_id,))
                conn.commit()
            removed += 1
        else:
            seen.add(file_id)

    await update.message.reply_text(f"🧹 Removed {removed} broken or duplicate cards from deck.")

from database import get_conn
import json

async def drawpreview(update, context):
    uid = update.effective_user.id
    with get_conn() as conn:
        row = conn.execute("""
            SELECT uc.file_id, d.json
            FROM user_cards uc
            JOIN deck d ON uc.file_id = d.file_id
            WHERE uc.uid = ?
            ORDER BY uc.drawn_at DESC
            LIMIT 1
        """, (uid,)).fetchone()

    if not row:
        return await update.message.reply_text("📭 You haven’t drawn any cards yet.")

    file_id, raw_json = row
    try:
        card = json.loads(raw_json)
        caption = (
            f"🎴 <b>Last Drawn Card</b>\n"
            f"🪄 Name: <b>{card.get('name', 'Unknown')}</b>\n"
            f"🔥 Power: {card.get('power', 'None')}\n"
            f"💥 Value: {card.get('value', 0)} coins\n"
            f"🎴 Rarity: {card.get('rarity', 'Common').title()}"
        )
        await update.message.reply_photo(photo=file_id, caption=caption, parse_mode="HTML")
    except:
        await update.message.reply_text("⚠️ Failed to load card preview.")

from database import get_conn
import json

async def mycards_preview(update, context):
    uid = update.effective_user.id

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT uc.file_id, d.json
            FROM user_cards uc
            JOIN deck d ON uc.file_id = d.file_id
            WHERE uc.uid = ?
            ORDER BY uc.drawn_at DESC
            LIMIT 3
        """, (uid,)).fetchall()

    if not rows:
        return await update.message.reply_text("📭 You have no cards.")

    for file_id, raw_json in rows:
        if not file_id or file_id == "None" or len(file_id) < 10:
            continue

        try:
            card = json.loads(raw_json)
            caption = (
                f"🃏 <b>{card.get('name', 'Unknown')}</b>\n"
                f"🔮 Power: {card.get('power', 'None')}\n"
                f"🎴 Rarity: {card.get('rarity', 'Common').title()}\n"
                f"💰 Value: {card.get('value', 0)}"
            )
            await update.message.reply_photo(photo=file_id, caption=caption, parse_mode="HTML")
        except:
            continue



from database import get_conn

async def fixcards(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    with get_conn() as conn:
        broken = conn.execute("""
            SELECT file_id FROM user_cards
            WHERE file_id IS NULL OR file_id = '' OR file_id = 'None'
        """).fetchall()

        for row in broken:
            conn.execute("DELETE FROM user_cards WHERE file_id = ?", (row[0],))
        conn.commit()

    await update.message.reply_text(f"🧹 Removed {len(broken)} broken card entries.")


async def uploadbulk(update, context):
    uid = update.effective_user.id
    if uid not in admin_ids:
        return await update.message.reply_text("🚫 Admins only.")

    bulk_upload_sessions.add(uid)
    await update.message.reply_text("📸 Bulk upload started. Send card images with captions like:\n\n<name> | <power> | <value> | <rarity>\n\nType /endbulk when done.")


async def endbulk(update, context):
    uid = update.effective_user.id
    if uid in bulk_upload_sessions:
        bulk_upload_sessions.remove(uid)
        await update.message.reply_text("✅ Bulk upload ended.")
    else:
        await update.message.reply_text("ℹ️ You’re not in bulk upload mode.")


async def handle_bulk_photo(update, context):
    uid = update.effective_user.id
    if uid not in bulk_upload_sessions:
        return  # Ignore if not in session

    photo = update.message.photo[-1]
    file_id = photo.file_id
    caption = update.message.caption

    if not caption or caption.count("|") != 4:
        return await update.message.reply_text(
            "❌ Failed to add card.\n\n📝 Caption must be in format:\n<name> | <power> | <value> | <rarity> | <cost>"
        )

    try:
        name, power, value, rarity, cost = [x.strip() for x in caption.split("|")]
        card = {
            "name": name,
            "power": int(power),
            "value": int(value),
            "rarity": rarity.lower(),
            "cost": int(cost),
            "file_id": file_id
        }

        from database import get_conn
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO deck (file_id, json) VALUES (?, ?)", (
                file_id,
                json.dumps(card)
            ))
            conn.commit()

        await update.message.reply_text(f"✅ Card '{name}' added.")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        await update.message.reply_text(
            "❌ Failed to add card. Make sure all values are correct numbers and format is:\n<name> | <power> | <value> | <rarity> | <cost>"
        )
