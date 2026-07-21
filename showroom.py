from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from database import get_conn, db_lock, get_balance
from config import ADMIN_IDS
import time
import asyncio


def _init_market_table():
    from database import ensure_market_trades_table
    ensure_market_trades_table()


try:
    _init_market_table()
except Exception:
    pass


async def additem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use /additem.")

    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text("📷 Please reply to a photo message with caption: Name | Type | Price")

    caption = update.message.reply_to_message.caption
    if not caption or "|" not in caption:
        return await update.message.reply_text("⚠️ Caption format must be: Name | Type | Price")

    try:
        name, type_, price = [part.strip() for part in caption.split("|")]
        type_ = type_.lower()
        price = int(price)
    except Exception:
        return await update.message.reply_text("❌ Failed to parse caption. Use: Name | Type | Price")

    photo_id = update.message.reply_to_message.photo[-1].file_id

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                conn.execute("""
                    INSERT INTO showroom_items (name, type, price, photo_id)
                    VALUES (?, ?, ?, ?)
                """, (name, type_, price, photo_id))
                conn.commit()

    await asyncio.to_thread(_db_work)

    await update.message.reply_text(f"✅ Item '{name}' added to showroom.")

async def showroom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _db_work():
        with get_conn() as conn:
            return conn.execute("SELECT item_id, name, type, price, photo_id FROM showroom_items").fetchall()

    items = await asyncio.to_thread(_db_work)

    if not items:
        return await update.message.reply_text("🏬 Showroom is empty.")

    media = []
    for item_id, name, type_, price, photo_id in items:
        caption = f"🚘 <b>{name}</b>\nType: {type_.capitalize()}\nPrice: ₹{price}\n🛒 Use /buy {item_id} to purchase"
        media.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML"))

    if len(media) == 1:
        await update.message.reply_photo(photo=media[0].media, caption=media[0].caption, parse_mode="HTML")
    else:
        await update.message.reply_media_group(media)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /buy <item_id>")

    item_id = int(context.args[0])
    coins = get_balance(uid)

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                item = conn.execute("SELECT name, price FROM showroom_items WHERE item_id = ?", (item_id,)).fetchone()
                if not item:
                    return ("not_found",)
                name, price = item
                if coins < price:
                    return ("no_coins",)
                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (price, uid))
                conn.execute("INSERT INTO user_showroom (uid, item_id, bought_at) VALUES (?, ?, ?)", (uid, item_id, int(time.time())))
                conn.commit()
                return ("ok", name)

    result = await asyncio.to_thread(_db_work)
    if result[0] == "not_found":
        return await update.message.reply_text("❌ Item not found.")
    elif result[0] == "no_coins":
        return await update.message.reply_text("❌ Not enough coins.")

    name = result[1]
    await update.message.reply_text(f"✅ You bought '{name}'! Check /myshowroom")

async def myshowroom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _db_work():
        with get_conn() as conn:
            return conn.execute("""
                SELECT s.name, s.type, s.price, s.photo_id
                FROM showroom_items s
                JOIN user_showroom u ON s.item_id = u.item_id
                WHERE u.uid = ?
            """, (uid,)).fetchall()

    rows = await asyncio.to_thread(_db_work)

    if not rows:
        return await update.message.reply_text("🫥 You don't own any vehicles yet.")

    media = []
    for name, type_, price, photo_id in rows:
        caption = f"🚘 <b>{name}</b>\nType: {type_.capitalize()}\nPrice: ₹{price}"
        media.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML"))

    if len(media) == 1:
        await update.message.reply_photo(photo=media[0].media, caption=media[0].caption, parse_mode="HTML")
    else:
        await update.message.reply_media_group(media)


async def listitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _db_work():
        with get_conn() as conn:
            return conn.execute("SELECT item_id, name, type, price FROM showroom_items").fetchall()

    items = await asyncio.to_thread(_db_work)

    if not items:
        return await update.message.reply_text("🏬 Showroom is empty.")

    msg = "🧾 <b>Showroom Inventory:</b>\n"
    for i, (item_id, name, type_, price) in enumerate(items, start=1):
        msg += f"{i}. {name} — {type_.capitalize()} — ₹{price} (ID: {item_id})\n"

    await update.message.reply_text(msg, parse_mode="HTML")


async def edititem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can edit items.")

    if len(context.args) < 3:
        return await update.message.reply_text("⚠️ Usage: /edititem <index> <field> <new_value>")

    index = int(context.args[0])
    field = context.args[1].lower()
    new_value = " ".join(context.args[2:])

    if field not in ["name", "type", "price"]:
        return await update.message.reply_text("❌ Field must be one of: name, type, price")

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                items = conn.execute("SELECT item_id FROM showroom_items").fetchall()
                if index < 1 or index > len(items):
                    return ("invalid_index",)
                item_id = items[index - 1][0]
                if field == "price":
                    try:
                        new_value_int = int(new_value)
                    except Exception:
                        return ("bad_price",)
                    # field is validated against a whitelist above, so this is safe
                    conn.execute(f"UPDATE showroom_items SET {field} = ? WHERE item_id = ?", (new_value_int, item_id))
                else:
                    # field is validated against a whitelist above, so this is safe
                    conn.execute(f"UPDATE showroom_items SET {field} = ? WHERE item_id = ?", (new_value, item_id))
                conn.commit()
                return ("ok",)

    result = await asyncio.to_thread(_db_work)
    if result[0] == "invalid_index":
        return await update.message.reply_text("❌ Invalid index.")
    elif result[0] == "bad_price":
        return await update.message.reply_text("❌ Price must be a number.")

    await update.message.reply_text(f"✅ Item #{index} updated: {field} → {new_value}")

async def deleteitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can delete items.")

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /deleteitem <index>")

    index = int(context.args[0])

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                items = conn.execute("SELECT item_id, name FROM showroom_items").fetchall()
                if index < 1 or index > len(items):
                    return ("invalid_index",)
                item_id, name = items[index - 1]
                conn.execute("DELETE FROM showroom_items WHERE item_id = ?", (item_id,))
                conn.commit()
                return ("ok", name)

    result = await asyncio.to_thread(_db_work)
    if result[0] == "invalid_index":
        return await update.message.reply_text("❌ Invalid index.")

    name = result[1]
    await update.message.reply_text(f"🗑️ Item '{name}' deleted from showroom.")




async def sellitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        return await update.message.reply_text("⚠️ Usage: /sellitem <item_id> <price>")

    item_id = int(context.args[0])
    price = int(context.args[1])

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                owned = conn.execute("SELECT 1 FROM user_showroom WHERE uid = ? AND item_id = ?", (uid, item_id)).fetchone()
                if not owned:
                    return ("not_owned",)
                conn.execute("INSERT INTO user_listings (seller_id, item_id, price, listed_at) VALUES (?, ?, ?, ?)",
                             (uid, item_id, price, int(time.time())))
                conn.commit()
                return ("ok",)

    result = await asyncio.to_thread(_db_work)
    if result[0] == "not_owned":
        return await update.message.reply_text("❌ You don't own this item.")

    await update.message.reply_text(f"✅ Item #{item_id} listed for ₹{price}. Use /market to view.")


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _db_work():
        with get_conn() as conn:
            return conn.execute("""
                SELECT l.listing_id, s.name, s.type, l.price, u.username
                FROM user_listings l
                JOIN showroom_items s ON s.item_id = l.item_id
                JOIN users u ON u.id = l.seller_id
            """).fetchall()

    rows = await asyncio.to_thread(_db_work)

    if not rows:
        return await update.message.reply_text("🛒 No items listed for sale.")

    msg = "🛒 <b>Marketplace Listings:</b>\n"
    for listing_id, name, type_, price, seller in rows:
        msg += f"{listing_id}. {name} ({type_}) — ₹{price} by @{seller}\n"

    msg += "\n🧾 <i>Use</i> <code>/buymitem &lt;index&gt;</code> <i>to purchase from the market.</i>"

    await update.message.reply_text(msg, parse_mode="HTML")

async def buymitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /buymitem <listing_id>")

    listing_id = int(context.args[0])

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                listing = conn.execute("""
                    SELECT seller_id, item_id, price FROM user_listings WHERE listing_id = ?
                """, (listing_id,)).fetchone()

                if not listing:
                    return ("not_found",)

                seller_id, item_id, price = listing
                coins = get_balance(uid)
                if coins < price:
                    return ("no_coins",)

                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (price, uid))
                conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (price, seller_id))
                conn.execute("""
                    INSERT INTO user_showroom (uid, item_id, bought_at)
                    VALUES (?, ?, ?)
                """, (uid, item_id, int(time.time())))

                conn.execute("DELETE FROM user_listings WHERE listing_id = ?", (listing_id,))

                conn.execute("""
                    INSERT INTO market_trades (buyer_id, seller_id, item_id, price, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (uid, seller_id, item_id, price, int(time.time())))

                conn.commit()
                return ("ok", item_id, price)

    result = await asyncio.to_thread(_db_work)
    if result[0] == "not_found":
        return await update.message.reply_text("❌ Listing not found or already sold.")
    elif result[0] == "no_coins":
        return await update.message.reply_text("❌ Not enough coins.")

    item_id, price = result[1], result[2]
    await update.message.reply_text(
        f"✅ You bought item #{item_id} for ₹{price}.\n"
        f"🪞 It now lives in your /myshowroom — a legacy marked in time."
    )

async def mylistings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _db_work():
        with get_conn() as conn:
            return conn.execute("""
                SELECT listing_id, item_id, price FROM user_listings WHERE seller_id = ?
            """, (uid,)).fetchall()

    rows = await asyncio.to_thread(_db_work)

    if not rows:
        return await update.message.reply_text("🫥 You have no active listings.")

    msg = "📦 <b>Your Listings:</b>\n"
    for listing_id, item_id, price in rows:
        msg += f"{listing_id}. Item #{item_id} — ₹{price}\n"

    await update.message.reply_text(msg, parse_mode="HTML")

async def cancelitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /cancelitem <listing_id>")

    listing_id = int(context.args[0])

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                listing = conn.execute("SELECT seller_id FROM user_listings WHERE listing_id = ?", (listing_id,)).fetchone()
                if not listing or listing[0] != uid:
                    return ("not_owned",)
                conn.execute("DELETE FROM user_listings WHERE listing_id = ?", (listing_id,))
                conn.commit()
                return ("ok",)

    result = await asyncio.to_thread(_db_work)
    if result[0] == "not_owned":
        return await update.message.reply_text("❌ You don't own this listing.")

    await update.message.reply_text(f"🗑️ Listing #{listing_id} cancelled.")


async def require_admin(update: Update) -> bool:
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("⛔ Only admins can use this.")
        return False
    return True

async def admin_showroom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /admin_showroom <user_id>")

    target_uid = int(context.args[0])

    def _db_work():
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT s.name, s.type, s.price, s.photo_id
                  FROM showroom_items s
                  JOIN user_showroom u ON s.item_id = u.item_id
                 WHERE u.uid = ?
                """,
                (target_uid,)
            ).fetchall()

    rows = await asyncio.to_thread(_db_work)

    if not rows:
        return await update.message.reply_text("🫥 No items for that user.")

    media = [
        InputMediaPhoto(
            media=photo_id,
            caption=f"🚘 <b>{name}</b>\nType: {type_.capitalize()}\nPrice: ₹{price}",
            parse_mode="HTML"
        )
        for name, type_, price, photo_id in rows
    ]

    if len(media) == 1:
        await update.message.reply_photo(media[0].media, caption=media[0].caption, parse_mode="HTML")
    else:
        await update.message.reply_media_group(media)

async def admin_additem_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return

    if len(context.args) != 2 or not all(arg.isdigit() for arg in context.args):
        return await update.message.reply_text("⚠️ Usage: /admin_additem_to <user_id> <item_id>")

    target_uid, item_id = map(int, context.args)
    timestamp = int(time.time())

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO user_showroom (uid, item_id, bought_at) VALUES (?, ?, ?)",
                    (target_uid, item_id, timestamp)
                )
                conn.commit()

    await asyncio.to_thread(_db_work)

    await update.message.reply_text(f"✅ Added item #{item_id} to user {target_uid}.")

async def admin_removeitem_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return

    if len(context.args) != 2 or not all(arg.isdigit() for arg in context.args):
        return await update.message.reply_text("⚠️ Usage: /admin_removeitem_from <user_id> <item_id>")

    target_uid, item_id = map(int, context.args)

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                deleted = conn.execute(
                    "DELETE FROM user_showroom WHERE uid = ? AND item_id = ?",
                    (target_uid, item_id)
                ).rowcount
                conn.commit()
                return deleted

    deleted = await asyncio.to_thread(_db_work)

    if deleted:
        await update.message.reply_text(f"🗑️ Removed item #{item_id} from user {target_uid}.")
    else:
        await update.message.reply_text("❌ That user didn't own that item.")


async def admin_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return

    def _db_work():
        with get_conn() as conn:
            return conn.execute("""
                SELECT l.listing_id, s.name, s.type, l.price, u.username
                  FROM user_listings l
                  JOIN showroom_items s ON s.item_id = l.item_id
                  JOIN users u ON u.id = l.seller_id
            """).fetchall()

    rows = await asyncio.to_thread(_db_work)

    if not rows:
        return await update.message.reply_text("🛒 No active listings.")

    msg = "🛒 <b>All Marketplace Listings:</b>\n"
    for lid, name, type_, price, seller in rows:
        msg += f"{lid}. {name} ({type_}) — ₹{price} by @{seller}\n"

    await update.message.reply_text(msg, parse_mode="HTML")

async def admin_removelisting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /admin_removelisting <listing_id>")

    lid = int(context.args[0])

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                deleted = conn.execute(
                    "DELETE FROM user_listings WHERE listing_id = ?",
                    (lid,)
                ).rowcount
                conn.commit()
                return deleted

    deleted = await asyncio.to_thread(_db_work)

    if deleted:
        await update.message.reply_text(f"🗑️ Listing #{lid} removed.")
    else:
        await update.message.reply_text("❌ Listing not found.")

async def admin_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return

    filter_type = None
    if context.args and context.args[0].lower() in ("car", "bike"):
        filter_type = context.args[0].lower()

    sql = """
        SELECT DISTINCT u.id, u.username
          FROM users u
          JOIN user_showroom us ON us.uid = u.id
          JOIN showroom_items s ON s.item_id = us.item_id
    """
    params = ()
    if filter_type:
        sql += " WHERE s.type = ?"
        params = (filter_type,)

    def _db_work():
        with get_conn() as conn:
            return conn.execute(sql, params).fetchall()

    rows = await asyncio.to_thread(_db_work)

    if not rows:
        return await update.message.reply_text("🫥 No owners found.")

    msg = "👥 <b>Owners List:</b>\n"
    for uid, username in rows:
        msg += f"{uid} — @{username}\n"

    await update.message.reply_text(msg, parse_mode="HTML")
