import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import get_balance, update_balance

duel_sessions = {}

async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    challenger = update.effective_user.id

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚔️ Reply to someone’s message to challenge them!")

    opponent = update.message.reply_to_message.from_user.id
    if opponent == challenger:
        return await update.message.reply_text("🫣 You can’t duel yourself.")

    if get_balance(challenger) < 500:
        return await update.message.reply_text("🚫 You need 500 coins to challenge someone.")
    if get_balance(opponent) < 500:
        return await update.message.reply_text("🚫 Opponent doesn’t have enough coins to accept the challenge.")

    update_balance(challenger, -500)
    update_balance(opponent, -500)

    duel_sessions[challenger] = {"pending": opponent}

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept:{challenger}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{challenger}")
        ]
    ])

    await update.message.reply_text(
        f"🗡️ <a href='tg://user?id={challenger}'>You</a> challenged "
        f"<a href='tg://user?id={opponent}'>Opponent</a> to a Friendly Battle!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def start_combat(chat_id, context: ContextTypes.DEFAULT_TYPE):
    buttons = [[
        InlineKeyboardButton("🥊 Punch", callback_data="punch"),
        InlineKeyboardButton("👋 Slap", callback_data="slap"),
        InlineKeyboardButton("🦵 Kick", callback_data="kick")
    ]]
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔥 <b>The battle begins!</b>\nEach player starts with 💖💖💖💖💖 (100 HP).",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    if data.startswith("reject:"):
        challenger_id = int(data.split(":")[1])
        if user.id == duel_sessions.get(challenger_id, {}).get("pending"):
            # 💸 Refund entry fee
            update_balance(challenger_id, 500)
            update_balance(user.id, 500)
            del duel_sessions[challenger_id]
            await query.edit_message_text("❌ Duel rejected. Entry fee refunded.")
        else:
            await query.answer("🚫 You are not the challenged user.", show_alert=True)
        return

    if data.startswith("accept:"):
        challenger_id = int(data.split(":")[1])
        opponent_id = user.id

        if opponent_id != duel_sessions.get(challenger_id, {}).get("pending"):
            return await query.answer("🚫 You're not the challenged user.", show_alert=True)

        # Initialize combat session
        duel_sessions[challenger_id] = {"opponent": opponent_id, "hp": 100}
        duel_sessions[opponent_id] = {"opponent": challenger_id, "hp": 100}

        await query.edit_message_text("✅ Challenge accepted! Duel begins!")
        await start_combat(update.effective_chat.id, context)

async def fight_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    uid = user.id
    action = query.data
    await query.answer()

    session = duel_sessions.get(uid)
    if not session:
        return await query.answer("❌ You're not in an active duel.", show_alert=True)

    opponent_id = session.get("opponent")
    opponent = duel_sessions.get(opponent_id)
    if not opponent or "hp" not in opponent:
        return await query.answer("⚠️ Opponent data missing.", show_alert=True)

    moves = {
        "punch": (10, 20),
        "slap":  (5, 25),
        "kick":  (15, 30)
    }

    if action not in moves:
        return await query.answer("🚫 Invalid move.", show_alert=True)

    damage = random.randint(*moves[action])
    opponent["hp"] -= damage
    opponent["hp"] = max(0, opponent["hp"])

    def hp_bar(hp):
        return "❤️" * (hp // 20) + "💔" * (5 - (hp // 20))

    if opponent["hp"] == 0:
        prize = 2000
        tax = 500
        net_gain = prize - tax
        update_balance(uid, net_gain)
        del duel_sessions[uid]
        del duel_sessions[opponent_id]

        return await query.edit_message_text(
            f"🏆 <a href='tg://user?id={uid}'>You</a> used <b>{action.upper()}</b> and KO’d your opponent!\n\n"
            f"💰 Prize: {prize} coins\n💸 Tax: {tax} coins\n🎖 Net Gain: {net_gain} coins",
            parse_mode="HTML"
        )

    await query.edit_message_text(
        f"🥷 <a href='tg://user?id={uid}'>You</a> used <b>{action.upper()}</b> — dealt {damage} damage!\n\n"
        f"💖 HP Status:\n• You: {hp_bar(session['hp'])}\n• Opponent: {hp_bar(opponent['hp'])}",
        reply_markup=InlineKeyboardMarkup([[ 
            InlineKeyboardButton("🥊 Punch", callback_data="punch"),
            InlineKeyboardButton("👋 Slap", callback_data="slap"),
            InlineKeyboardButton("🦵 Kick", callback_data="kick")
        ]]),
        parse_mode="HTML"
    )
