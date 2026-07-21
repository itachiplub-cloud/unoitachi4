import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from database import get_conn, db_lock, get_balance, add_earnings
from utils import check_cooldown, update_cooldown
import random



async def adoptpet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _adopt():
        with get_conn() as conn:
            existing = conn.execute("SELECT 1 FROM user_pets WHERE uid = ?", (uid,)).fetchone()
            if existing:
                return None

            names = ["Shadow", "Bolt", "Mochi", "Nova", "Luna", "Echo"]
            types = ["Dog", "Cat", "Fox", "Penguin", "Dragon"]
            name = random.choice(names)
            type_ = random.choice(types)

            conn.execute("INSERT INTO user_pets (uid, pet_name, pet_type) VALUES (?, ?, ?)", (uid, name, type_))
            conn.execute("INSERT INTO pet_battles (uid) VALUES (?)", (uid,))
            conn.commit()

            return name, type_

    result = await asyncio.to_thread(_adopt)
    if result is None:
        return await update.message.reply_text("🐾 You already have a pet! Use /mypet to view it.")

    name, type_ = result
    await update.message.reply_text(f"🎉 You adopted a {type_} named {name}!\nUse /feedpet and /petbattle to train it.")

async def feedpet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    remaining = check_cooldown(uid, "feedpet")
    if remaining > 0:
        return await update.message.reply_text(f"⏳ You can feed your pet again in {remaining//60}m {remaining%60}s.")

    def _feed():
        with db_lock:
            with get_conn() as conn:
                pet = conn.execute("SELECT hunger FROM user_pets WHERE uid = ?", (uid,)).fetchone()
                if not pet:
                    return None

                new_hunger = min(100, pet[0] + 20)
                conn.execute("UPDATE user_pets SET hunger = ? WHERE uid = ?", (new_hunger, uid))
                conn.execute("UPDATE users SET coins = coins + 100 WHERE id = ?", (uid,))
                conn.commit()

        add_earnings(uid, 100)
        return True

    result = await asyncio.to_thread(_feed)
    if result is None:
        return await update.message.reply_text("❌ You don't have a pet. Use /adoptpet.")

    update_cooldown(uid, "feedpet")
    await update.message.reply_text("🍖 Your pet feels loved! You earned ₹100.")

async def mypet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _mypet():
        with get_conn() as conn:
            return conn.execute("""
                SELECT pet_name, pet_type, level, hunger
                FROM user_pets WHERE uid = ?
            """, (uid,)).fetchone()

    pet = await asyncio.to_thread(_mypet)

    if not pet:
        return await update.message.reply_text("🫥 You have no pet. Use /adoptpet to find a companion.")

    name, type_, level, hunger = pet
    mood = "😊 Happy" if hunger > 60 else "😐 Okay" if hunger > 30 else "😢 Hungry"
    await update.message.reply_text(
        f"🐾 <b>Your Pet:</b>\nName: {name}\nType: {type_}\nLevel: {level}\nHunger: {hunger}/100 ({mood})",
        parse_mode="HTML"
    )

async def petbattle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ You must reply to someone's message to challenge them.")

    challenger_id = update.effective_user.id
    target_user = update.message.reply_to_message.from_user
    target_id = target_user.id

    def _get_pets():
        with get_conn() as conn:
            challenger_pet = conn.execute("SELECT pet_name, pet_type FROM user_pets WHERE uid = ?", (challenger_id,)).fetchone()
            target_pet = conn.execute("SELECT pet_name, pet_type FROM user_pets WHERE uid = ?", (target_id,)).fetchone()
            return challenger_pet, target_pet

    challenger_pet, target_pet = await asyncio.to_thread(_get_pets)

    if not challenger_pet or not target_pet:
        return await update.message.reply_text("❌ Both players must have a pet to battle.")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"accept_battle:{challenger_id}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"decline_battle:{challenger_id}")]
    ])

    await update.message.reply_text(
        f"⚔️ <b>Pet Battle Request</b>\n@{target_user.username}, do you accept the challenge?\n\n"
        f"{challenger_pet[0]} ({challenger_pet[1]}) vs {target_pet[0]} ({target_pet[1]})",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

async def handle_battle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    data = query.data
    action, challenger_id = data.split(":")
    challenger_id = int(challenger_id)

    if uid != update.effective_user.id:
        return await query.edit_message_text("🚫 Only the challenged user can respond.")

    if action == "decline_battle":
        return await query.edit_message_text("❌ Battle declined.")

    # Battle logic
    winner = random.choice([uid, challenger_id])

    def _battle():
        nonlocal msg
        with db_lock:
            with get_conn() as conn:
                if winner == uid:
                    conn.execute("UPDATE pet_battles SET wins = wins + 1 WHERE uid = ?", (uid,))
                    conn.execute("UPDATE users SET coins = coins + 200 WHERE id = ?", (uid,))
                    add_earnings(uid, 200)
                    msg = "🏆 You won the pet battle! +₹200"
                else:
                    conn.execute("UPDATE pet_battles SET losses = losses + 1 WHERE uid = ?", (uid,))
                    msg = "😿 You lost the pet battle."

                conn.commit()

    msg = ""
    await asyncio.to_thread(_battle)

    await query.edit_message_text(msg)
