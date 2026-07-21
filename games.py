import asyncio
import random
import time
import logging
from datetime import datetime, timedelta

from telegram import Update, Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from database import get_balance, update_balance, add_earnings, get_conn, db_lock, get_username
from database import is_bot_admin
from mongo_users import mongo_db

global_raid_active = False
raid_log = []


def _append_raid_log(entry):
    raid_log.append(entry)
    if len(raid_log) > _RAID_LOG_MAX:
        del raid_log[:len(raid_log) - _RAID_LOG_MAX]

def start_global_raid():
    global global_raid_active
    global_raid_active = True

def stop_global_raid():
    global global_raid_active
    global_raid_active = False

def is_global_raid():
    return global_raid_active



COMMAND_COOLDOWNS = {
    "flip": 120,
    "roll": 1800,
    "rps": 1800,
    "guess": 60,
    "spin": 21600,
    "fly":    90,
    "enter": 30,
}
_last_times = {}
_COOLDOWN_CACHE_TTL = 86400  # 24 hours — prune entries older than this
_RAID_LOG_MAX = 200

logging.basicConfig(level=logging.DEBUG)

_last_cleanup = 0

def check_cooldown(uid: int, cmd: str) -> int:
    """
    Returns seconds remaining on cooldown, or 0 if ready.
    """
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup > _COOLDOWN_CACHE_TTL:
        stale = [k for k, t in _last_times.items() if now - t > _COOLDOWN_CACHE_TTL]
        for k in stale:
            del _last_times[k]
        _last_cleanup = now
    key = (uid, cmd)
    cd = COMMAND_COOLDOWNS.get(cmd, 1800)
    elapsed = now - _last_times.get(key, 0)
    if elapsed < cd:
        return int(cd - elapsed)
    _last_times[key] = now
    return 0


async def flip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    wait = await asyncio.to_thread(check_cooldown, uid, "flip")
    if wait:
        return await update.message.reply_text(
            f"🕒 Wait {wait}s before flipping again."
        )

    if len(context.args) != 2:
        return await update.message.reply_text("🪙 Usage: /flip <heads|tails> <amount>")

    guess_raw, amt_raw = context.args
    guess = guess_raw.lower()
    if guess not in ("heads", "tails"):
        return await update.message.reply_text("🚫 Guess must be 'heads' or 'tails'.")

    try:
        bet = int(amt_raw)
        if bet <= 0:
            raise ValueError
    except ValueError:
        return await update.message.reply_text("🚫 Bet must be a positive integer.")

    balance = await asyncio.to_thread(get_balance, uid)
    if balance < bet:
        return await update.message.reply_text(
            f"💸 You have {balance} coins—cannot bet {bet}."
        )
    await asyncio.to_thread(update_balance, uid, -bet)

    await update.message.reply_text("🕒 Flipping the coin… check back in 3s.")
    context.job_queue.run_once(
        flip_result,
        when=3,
        data={
            "chat_id": update.effective_chat.id,
            "uid": uid,
            "guess": guess,
            "bet": bet,
        },
    )

async def flip_result(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    result = random.choice(["heads", "tails"])
    won = data["guess"] == result
    payout = int(data["bet"] * 1.5) if won else 0
    if won:
        await asyncio.to_thread(update_balance, data["uid"], payout)

    await context.bot.send_message(
        chat_id=data["chat_id"],
        text=(
            f"🪙 <b>Flip Result</b>: {result.upper()}\n"
            f"🎯 Your Guess: {data['guess'].upper()}\n"
            f"{'🏆 You won!' if won else '😢 You lost.'}\n"
            f"{'💰 Payout: ' + str(payout) + ' coins' if won else '💸 Your wager was lost.'}"
        ),
        parse_mode="HTML",
    )


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    wait = await asyncio.to_thread(check_cooldown, uid, "roll")
    if wait:
        return await update.message.reply_text(f"🕒 Wait {wait}s before rolling again.")

    if len(context.args) != 1:
        return await update.message.reply_text("🎲 Usage: /roll <bet>")
    try:
        bet = int(context.args[0])
        if bet <= 0:
            raise ValueError
    except ValueError:
        return await update.message.reply_text("🚫 Invalid bet.")


    bal = await asyncio.to_thread(get_balance, uid)
    if bal < bet:
        return await update.message.reply_text(f"💸 You only have {bal} coins.")
    await asyncio.to_thread(update_balance, uid, -bet)

    THRESHOLD = 10_000
    if bet > THRESHOLD:
        # cheat mode: 60% bot‐win, 40% user‐win
        if random.random() < 0.6:
            # force a bot‐win: pick user in [1..5], then bot in [user+1..6]
            you = random.randint(1, 5)
            bot_roll = random.randint(you + 1, 6)
            outcome = "bot"
        else:
            # force a user‐win: pick bot in [1..5], then you in [bot+1..6]
            bot_roll = random.randint(1, 5)
            you = random.randint(bot_roll + 1, 6)
            outcome = "user"
    else:
        # fair mode
        you      = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        if you > bot_roll:
            outcome = "user"
        elif you < bot_roll:
            outcome = "bot"
        else:
            outcome = "tie"

    if outcome == "user":
        win_amt = bet * 1.5
        await asyncio.to_thread(update_balance, uid, win_amt)
        text = f"🏆 You Rocked! You rolled {you}, bot rolled {bot_roll}. +{win_amt} coins."
    elif outcome == "bot":
        text = f"😢 Haar Gye. You rolled {you}, bot rolled {bot_roll}. Lost {bet} coins."
    else:  # tie
        await asyncio.to_thread(update_balance, uid, bet)
        text = f"🤝 ohh Tie! Both Noob {you}. Bet returned."

    await update.message.reply_text(text)

async def rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    wait = await asyncio.to_thread(check_cooldown, uid, "rps")
    if wait:
        return await update.message.reply_text(f"🕒 Wait {wait}s before playing again.")

    if len(context.args) != 2:
        return await update.message.reply_text(
            "✂️ Usage: /rps <rock|paper|scissors> <bet>"
        )

    choice = context.args[0].lower()
    if choice not in ("rock", "paper", "scissors"):
        return await update.message.reply_text("🚫 Invalid choice.(rock , paper , scissors) .")
    try:
        bet = int(context.args[1])
        if bet <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("🚫 Number Enter krna he (Kyu nahi ho rhi he padhai ?).")

    bal = await asyncio.to_thread(get_balance, uid)
    if bal < bet:
        return await update.message.reply_text(f"💸 Not enough coins (Autat me 🌚). You have {bal}.")

    await asyncio.to_thread(update_balance, uid, -bet)
    bot_choice = random.choice(["rock", "paper", "scissors"])
    wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

    if choice == bot_choice:
        await asyncio.to_thread(update_balance, uid, bet)
        text = f"🤝 Tie! Bot chose {bot_choice}. Bet returned."
    elif wins[choice] == bot_choice:
        payout = bet * 1.5
        await asyncio.to_thread(update_balance, uid, payout)
        text = f"🏆 You win! Bot chose {bot_choice}. +{payout} coins."
    else:
        text = f"😢 You lose! Bot chose {bot_choice}. Lost {bet} coins."

    await update.message.reply_text(text)


async def guessbet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    wait = await asyncio.to_thread(check_cooldown, uid, "guess")
    if wait:
        return await update.message.reply_text(f"🕒 Wait {wait}s before guessing again.")

    if len(context.args) != 2:
        return await update.message.reply_text(
            "🔢 Usage: /guessbet <1-50> <bet>"
        )

    try:
        num = int(context.args[0])
        bet = int(context.args[1])
        if not (1 <= num <= 50) or bet <= 0:
            raise ValueError
    except:
        return await update.message.reply_text(
            "🚫 Invalid input. Use: /guessbet <1-50> <bet>"
        )

    bal = await asyncio.to_thread(get_balance, uid)
    if bal < bet:
        return await update.message.reply_text(
            f"💸 You have {bal}, not enough to bet {bet}."
        )

    await asyncio.to_thread(update_balance, uid, -bet)
    target = random.randint(1, 50)
    diff = abs(num - target)

    if diff == 0:
        reward = bet * 10
    elif diff <= 3:
        reward = bet * 2
    else:
        reward = 0

    if reward:
        await asyncio.to_thread(update_balance, uid, reward)
        msg = f"🎯 The number was {target}. You earned {reward} coins!"
    else:
        msg = f"❌ The number was {target}. You lost your {bet} coins."

    await update.message.reply_text(msg)

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    wait = await asyncio.to_thread(check_cooldown, uid, "spin")
    if wait:
        return await update.message.reply_text(f"🕒 Wait {wait}s before spinning again.")

    if len(context.args) != 1:
        return await update.message.reply_text("🎡 Usage: /spin <bet>")
    try:
        bet = int(context.args[0])
        if bet <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("🚫 Invalid bet.")

    bal = await asyncio.to_thread(get_balance, uid)
    if bal < bet:
        return await update.message.reply_text(
            f"💸 Insufficient coins. You have {bal}."
        )

    await asyncio.to_thread(update_balance, uid, -bet)
    rnd = random.random()
    if rnd < 0.50:
        msg = f"😞 You spun 🟥 — No win. Lost {bet} coins."
    elif rnd < 0.80:
        await asyncio.to_thread(update_balance, uid, bet)
        msg = f"🙂 You spun 🟩 — Bet returned."
    elif rnd < 0.95:
        win = bet * 1.5
        await asyncio.to_thread(update_balance, uid, win)
        msg = f"🎉 You spun 🟦 — +{win} coins!"
    else:
        win = bet * 2
        await asyncio.to_thread(update_balance, uid, win)
        msg = f"💎 JACKPOT! 🟪 +{win} coins!"

    await update.message.reply_text(msg)


raffle_data = {}  # chat_id → {"entries": set(uid), "job": Job}
raffle_global_entries = set()  # Global tracker for all entrants

RAFFLE_ENTRY_COST = 200  # 💸 Cost to join

async def enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    uid = update.effective_user.id

    # ⏳ Optional cooldown check
    wait = await asyncio.to_thread(check_cooldown, uid, "enter")
    if wait:
        return await update.message.reply_text(f"🕒 Wait {wait}s before entering again.")

    # 🔒 Already joined globally
    if uid in raffle_global_entries:
        return await update.message.reply_text("🔔 Kitni baar aaoge.")

    # 💰 Check balance before joining
    balance = await asyncio.to_thread(get_balance, uid)
    if balance < RAFFLE_ENTRY_COST:
        return await update.message.reply_text("❌ You need ₹200 to buy ticket for the raffle.")

    # 🧾 Deduct entry cost
    await asyncio.to_thread(update_balance, uid, -RAFFLE_ENTRY_COST)

    data = raffle_data.get(chat_id)
    if not data:
        # First entry in this chat
        raffle_data[chat_id] = {"entries": {uid}, "job": None}
        raffle_global_entries.add(uid)

        job = context.job_queue.run_once(
            _raffle_draw, when=30, data={"chat_id": chat_id}
        )
        raffle_data[chat_id]["job"] = job

        return await update.message.reply_text("🎟️ Raffle ticket purchased At the cost of ₹200!\n 30s to join with /enter.\n")

    if uid in data["entries"]:
        return await update.message.reply_text("🔔 Kitni baar aaoge.")

    data["entries"].add(uid)
    raffle_global_entries.add(uid)

    await update.message.reply_text(
        f"🎟️ You joined! ₹{RAFFLE_ENTRY_COST} deducted.\nTotal entrants: {len(data['entries'])}."
    )


async def _raffle_draw(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]
    data = raffle_data.pop(chat_id, None)

    if not data or not data["entries"]:
        return await context.bot.send_message(
            chat_id, "❌ No entrants — raffle closed."
        )

    winner = random.choice(list(data["entries"]))
    prize = 1000 * len(data["entries"])
    await asyncio.to_thread(update_balance, winner, prize)

    for uid in data["entries"]:
        raffle_global_entries.discard(uid)

    user: Chat = await context.bot.get_chat(winner)
    if user.username:
        mention_name = f"@{user.username}"
    else:
        mention_name = user.first_name or "User"

    await context.bot.send_message(
        chat_id,
        (
            f"🏆 <a href='tg://user?id={winner}'>{mention_name}</a> won the raffle!\n"
            f"💰 Prize: {prize} coins"
        ),
        parse_mode="HTML"
    )



# ── MongoDB collections for mines (replaces broken SQLite tables) ─────────────
_mines_games_col     = mongo_db["mines_games"]      # active game per user
_mines_cooldowns_col = mongo_db["mines_cooldowns"]  # cooldown per user
_mines_games_col.create_index("uid", unique=True)
_mines_cooldowns_col.create_index("uid", unique=True)
# ─────────────────────────────────────────────────────────────────────────────

COOLDOWN_SECONDS = 180
MINES_TRAP_MODE = False

MINES_MULTIPLIERS = {
    1: 1.25,  2: 1.5,   3: 1.75,  4: 2.0,   5: 2.5,
    6: 3.0,   7: 3.25,  8: 3.5,   9: 3.75, 10: 4.0,
    11: 4.25, 12: 4.5, 13: 4.75, 14: 5.0,  15: 5.25,
    16: 5.5,  17: 5.75, 18: 6.0,  19: 6.25, 20: 6.5,
    21: 6.75, 22: 6.85, 23: 6.95, 24: 7.0
}

def build_mines_grid(uid):
    doc = _mines_games_col.find_one({"uid": uid})
    revealed = set(doc["revealed"]) if doc and doc.get("revealed") else set()

    keyboard = []
    for i in range(5):
        row_buttons = []
        for j in range(5):
            index = i * 5 + j
            label = "🟦" if index not in revealed else "🟩"
            row_buttons.append(InlineKeyboardButton(label, callback_data=f"reveal_{index}"))
        keyboard.append(row_buttons)

    keyboard.append([InlineKeyboardButton("🏃 Exit", callback_data="exitmines")])
    return InlineKeyboardMarkup(keyboard)

async def mines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        return await update.message.reply_text("⚠️ Usage: /mines <bombs> <bet>")

    bombs = int(args[0])
    bet   = int(args[1])
    coins = await asyncio.to_thread(get_balance, uid)

    if bombs < 1 or bombs > 24:
        return await update.message.reply_text("❌ Bombs must be between 1 and 24.")
    if bet <= 0:
        return await update.message.reply_text("❌ Bet must be greater than 0.")
    if coins < bet:
        return await update.message.reply_text("❌ Not enough coins. (Autat me 🌚)")

    now = int(time.time())

    # ── Cooldown check (MongoDB) ──────────────────────────────────────────────
    cd_doc = _mines_cooldowns_col.find_one({"uid": uid})
    if cd_doc:
        last = cd_doc.get("last_played", 0)
        if now - last < COOLDOWN_SECONDS:
            remaining = COOLDOWN_SECONDS - (now - last)
            mins = remaining // 60
            secs = remaining % 60
            return await update.message.reply_text(
                f"⏳ Ruko jara sabar karo✋. Try again in {mins}m {secs}s."
            )

    # ── Global raid check ─────────────────────────────────────────────────────
    if is_global_raid() and not is_bribed(uid):
        fine       = 500
        total_loss = bet + fine
        await asyncio.to_thread(update_balance, uid, -total_loss)

        _append_raid_log({
            "uid": uid,
            "loss": total_loss,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "global"
        })

        username = (await asyncio.to_thread(get_username, uid)) or "Unknown"
        await context.bot.send_message(
            chat_id=uid,
            text=(
                "🚨 <b>RAID CONFIRMED</b>\n"
                f"🧠 @{username}, you were busted trying to plant mines.\n"
                f"💸 ₹{total_loss} wiped — stake + fine.\n"
                "🕶️ Hafta time se diya kro, Bach sakte ho.\n"
            ),
            parse_mode="HTML"
        )
        return await update.message.reply_text(
            "🚨 POLICE RAID! 🚔 You were caught at the minefield.\n"
            "💸 Full stake + ₹500 fine deducted (Agli baar hafta time pe de dena)."
        )

    # ── Deduct bet and start game (MongoDB) ───────────────────────────────────
    positions = random.sample(range(25), bombs)
    await asyncio.to_thread(update_balance, uid, -bet)

    _mines_games_col.update_one(
        {"uid": uid},
        {"$set": {
            "uid": uid,
            "bet": bet,
            "bombs": bombs,
            "revealed": [],
            "bomb_positions": positions,
            "started_at": now
        }},
        upsert=True
    )
    _mines_cooldowns_col.update_one(
        {"uid": uid},
        {"$set": {"uid": uid, "last_played": now}},
        upsert=True
    )

    trap_notice = "BEST OF LUCK ." if MINES_TRAP_MODE else ""
    await update.message.reply_text(
        f"💣 Mines game started with {bombs} bombs.\n💰 Bet: ₹{bet}\n"
        f"Tap tiles to reveal gems or bombs.\n{trap_notice}",
        reply_markup=build_mines_grid(uid)
    )

def calculate_multiplier(bombs: int, safe_count: int) -> float:
    base     = MINES_MULTIPLIERS.get(bombs, 1.0)
    max_safe = 25 - bombs

    if safe_count == 0:
        return 1.0

    progress   = safe_count / max_safe
    multiplier = 1 + (base - 1) * progress

    if safe_count == 3 and multiplier < 1.25:
        multiplier = 1.25

    return round(multiplier, 2)


async def exitmines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.message else update.callback_query.from_user.id

    doc = _mines_games_col.find_one({"uid": uid})
    if not doc:
        return await update.callback_query.edit_message_text("❌ No active mines game.")

    bet        = doc["bet"]
    bombs      = doc["bombs"]
    revealed   = doc.get("revealed", [])
    safe_count = len(revealed)
    multiplier = calculate_multiplier(bombs, safe_count)
    winnings   = int(bet * multiplier)

    await asyncio.to_thread(update_balance, uid, winnings)
    await asyncio.to_thread(add_earnings, uid, winnings)
    _mines_games_col.delete_one({"uid": uid})

    await update.callback_query.edit_message_text(
        f"🏆 Is baar bach gye Agli baar...!\n💰 Winnings: ₹{winnings}\n"
        f"🧠 Safe tiles: {safe_count}\nMultiplier: x{multiplier}"
    )

async def handle_mines_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = query.from_user.id
    data = query.data

    doc = _mines_games_col.find_one({"uid": uid})
    if not doc:
        return

    revealed_list  = doc.get("revealed", [])
    bomb_positions = set(doc.get("bomb_positions", []))
    revealed_set   = set(revealed_list)

    if data == "exitmines":
        safe_count = len(revealed_set)
        if safe_count < 3:
            return await query.answer(
                f"⚠️ 3 baar bachke dikhao or nikal lo paisa 🌝! ({safe_count}/3)",
                show_alert=True
            )
        return await exitmines(update, context)

    if data.startswith("reveal_"):
        tile = int(data.split("_", 1)[1])

        if tile in revealed_set:
            return  # already revealed, ignore

        # Trap mode: first tap always explodes
        if MINES_TRAP_MODE and not revealed_set:
            _mines_games_col.delete_one({"uid": uid})
            return await query.edit_message_text("💥 You hit a bomb! Game over.")

        if tile in bomb_positions:
            _mines_games_col.delete_one({"uid": uid})
            return await query.edit_message_text("💥 You hit a bomb! Game over.")

        # Safe tile — persist updated revealed list
        revealed_set.add(tile)
        _mines_games_col.update_one(
            {"uid": uid},
            {"$set": {"revealed": list(revealed_set)}}
        )

        return await query.edit_message_text(
            f"✅ Safe tile revealed! ({len(revealed_set)} so far)\n"
            f"Reveal more or exit once you have 3+",
            reply_markup=build_mines_grid(uid)
        )

async def minestrap_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("❌ You're not allowed to toggle trap mode.")

    args = context.args
    if len(args) != 1 or args[0] not in ["on", "off"]:
        return await update.message.reply_text("⚠️ Usage: /minestrap <on|off>")

    global MINES_TRAP_MODE
    MINES_TRAP_MODE = args[0] == "on"

    status = "activated" if MINES_TRAP_MODE else "deactivated"
    await update.message.reply_text(
        f"💣 Mines trap mode {status}.\n"
        f"First click will now {'explode' if MINES_TRAP_MODE else 'behave normally'}."
    )


async def dig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /dig <depth>")

    depth = int(context.args[0])
    if depth < 1 or depth > 10:
        return await update.message.reply_text("❌ Depth must be between 1 and 10.")

    remaining = await asyncio.to_thread(check_cooldown, uid, "dig")
    if remaining > 0:
        return await update.message.reply_text(f"⏳ Ruko jara sabar karo✋. Try again in {remaining//60}m {remaining%60}s.")

    cost = depth * 100
    coins = await asyncio.to_thread(get_balance, uid)
    if coins < cost:
        return await update.message.reply_text("❌ Not enough coins (Autat me 🌚).")

    reward = random.randint(depth * 150, depth * 500)
    if random.random() < 0.2:  # 20% chance of failure
        reward = 0

    def _sync_db_op():
        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (cost, uid))
                if reward > 0:
                    conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (reward, uid))
                conn.commit()
                add_earnings(uid, reward)
    await asyncio.to_thread(_sync_db_op)
    await asyncio.to_thread(update_cooldown, uid, "dig")

    if reward > 0:
        await update.message.reply_text(f"⛏️ You dug at depth {depth} and found ₹{reward}!")
    else:
        await update.message.reply_text(f"💥 You hit a rock at depth {depth}. No reward.")


async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /blackjack <bet>")

    bet = int(context.args[0])
    coins = await asyncio.to_thread(get_balance, uid)
    if bet <= 0 or coins < bet:
        return await update.message.reply_text("❌ Invalid or insufficient coin amount.")

    remaining = await asyncio.to_thread(check_cooldown, uid, "blackjack")
    if remaining > 0:
        return await update.message.reply_text(
            f"⏳ Ruko jara sabar karo✋. Try again in {remaining//60}m {remaining%60}s."
        )

    if police_check(uid, bet, context.bot):
        return await update.message.reply_text(
            "🚨 POLICE RAID! 🚔 You were caught at the blackjack table.\n💸 Lost your full stake + ₹500 fine."
        )

    await asyncio.to_thread(update_cooldown, uid, "blackjack")

    def draw_card():
        return random.randint(2, 11)

    user_total = draw_card() + draw_card()
    bot_total = draw_card() + draw_card()

    if user_total > bot_total:
        result = f"🏆 You win! +₹{bet}"
        def _sync_win():
            with db_lock:
                with get_conn() as conn:
                    conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (bet, uid))
                    conn.commit()
                add_earnings(uid, bet)
        await asyncio.to_thread(_sync_win)

    elif user_total < bot_total:
        result = f"💔 You lose! -₹{bet}"
        def _sync_lose():
            with db_lock:
                with get_conn() as conn:
                    conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (bet, uid))
                    conn.commit()
        await asyncio.to_thread(_sync_lose)

    else:
        result = "🤝 It's a tie! No coins lost."

    await update.message.reply_text(
        f"🃏 Your total: {user_total}\n🤖 Bot total: {bot_total}\n{result}"
    )



def police_check(uid: int, bet: int, bot: Bot = None) -> bool:
    if is_bribed(uid):
        return False  # 🛡️ Bribe blocks raid

    chance = 1.0 if is_global_raid() else 0.07
    if not is_global_raid() and bet > 10000:
        chance += 0.03

    if random.random() < chance:
        fine = 500
        total_loss = bet + fine

        # 💸 Wipe coins
        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (total_loss, uid))
                conn.commit()

        _append_raid_log({
            "uid": uid,
            "loss": total_loss,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "global" if is_global_raid() else "random"
        })

        if bot:
            username = get_username(uid) or "Unknown"
            msg = (
                "🚨 <b>RAID CONFIRMED</b>\n"
                f"🎯 @{username}, Reverse God cops caught you mid-play.\n"
                f"💸 ₹{total_loss} lost — bet & fine wiped clean.\n"
                "🕶️ Bribe next time... or face the streets again."
            )
            bot.send_message(chat_id=uid, text=msg, parse_mode=ParseMode.HTML)

        return True

    return False  

async def heist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /heist <location>\nAvailable: bank, museum, vault")

    location = context.args[0].lower()
    if location not in ["bank", "museum", "vault"]:
        return await update.message.reply_text("❌ Invalid location. Choose: bank, museum, vault")

    remaining = await asyncio.to_thread(check_cooldown, uid, "heist")
    if remaining > 0:
        return await update.message.reply_text(f"⏳ Ruko jara sabar karo✋. Try again in {remaining//60}m {remaining%60}s.")

    cost = 500
    coins = await asyncio.to_thread(get_balance, uid)
    if coins < cost:
        return await update.message.reply_text("❌ Not enough coins (Autat me 🌚).")

    if police_check(uid, cost):
        return await update.message.reply_text("🚨 POLICE RAID! 🚔 You were caught near the scene.\n💸 Lost ₹500 and your gear!")

    success = random.random() < 0.6
    reward = random.randint(1000, 5000) if success else 0

    def _sync_heist():
        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (cost, uid))
                if success:
                    conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (reward, uid))
                conn.commit()
    await asyncio.to_thread(_sync_heist)

    if success:
        try:
            def _sync_add_earnings():
                with db_lock:
                    add_earnings(uid, reward)
            await asyncio.to_thread(_sync_add_earnings)
        except Exception as e:
            print(f"⚠️ Failed to track earnings: {e}")

    await asyncio.to_thread(update_cooldown, uid, "heist")

    await update.message.reply_text(
        f"{'🕵️ Heist successful!' if success else '🚨 Heist failed!'}\n"
        f"{'💰 You stole ₹' + str(reward) if success else '💸 You lost ₹500'}"
    )



fly_storm_mode = False

async def flystorm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_bot_admin(user_id):
        return await update.message.reply_text("🚫 You’re not authorized to toggle storm mode.")
    
    if not context.args or context.args[0].lower() not in ["on", "off"]:
        return await update.message.reply_text("⚠️ Usage: /flystorm <on|off>")
    
    global fly_storm_mode
    fly_storm_mode = context.args[0].lower() == "on"

    status = (
        "🌪️ Storm Mode Activated — All flights will crash!" 
        if fly_storm_mode 
        else "🌤️ Storm Mode Deactivated — Flights are safe again."
    )
    await update.message.reply_text(status)


fly_shield_admins = set()  

async def flyshield(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 You’re not authorized to toggle fly shield.")

    if not context.args or context.args[0].lower() not in ["on", "off"]:
        return await update.message.reply_text("⚠️ Usage: /flyshield <on|off>")

    global fly_shield_admins
    if context.args[0].lower() == "on":
        fly_shield_admins.add(uid)
        status = "🛡️ Fly Shield Activated — You are now protected from crashes."
    else:
        fly_shield_admins.discard(uid)
        status = "☁️ Fly Shield Deactivated — You may crash again."

    await update.message.reply_text(status)


def update_cooldown(uid: int, cmd: str):
    """
    Mark this command as just used.
    """
    _last_times[(uid, cmd)] = time.time()



async def fly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # 1. Arg validation
    if len(context.args) != 2 or not context.args[0].isdigit():
        return await update.message.reply_text(
            "⚠️ Usage: /fly <coins> <risk>\nRisk: low, medium, high\nExample:- /fly 1000 high"
        )

    bet  = int(context.args[0])
    risk = context.args[1].lower()
    if risk not in ("low", "medium", "high"):
        return await update.message.reply_text(
            "❌ Invalid risk level. Choose: low, medium, high"
        )

    balance = await asyncio.to_thread(get_balance, uid)
    if bet <= 0 or balance < bet:
        return await update.message.reply_text("❌ Invalid or insufficient coins.")

    wait = await asyncio.to_thread(check_cooldown, uid, "fly")
    if wait:
        mins, secs = divmod(wait, 60)
        return await update.message.reply_text(
            f"⏳ Ruko jara sabar karo✋. Try again in {mins}m {secs}s."
        )

    if police_check(uid, bet, context.bot):
        return await update.message.reply_text(
            "🚨 POLICE RAID! 🚔 You were caught at the runway.\n"
            "💸 Lost your full stake + ₹500 fine."
        )

    await asyncio.to_thread(update_cooldown, uid, "fly")

    settings = {
        "low":    {"crash": 0.1, "min": 1.1, "max": 2.0},
        "medium": {"crash": 0.3, "min": 1.5, "max": 4.0},
        "high":   {"crash": 0.6, "min": 2.5, "max": 6.5},
    }
    cfg = settings[risk]
    crash_chance, min_mult, max_mult = cfg["crash"], cfg["min"], cfg["max"]

    crashed = (
        uid not in fly_shield_admins
        and (fly_storm_mode or random.random() < crash_chance)
    )
    if crashed:
        def _sync_crash():
            with db_lock, get_conn() as conn:
                conn.execute(
                    "UPDATE users SET coins = coins - ? WHERE id = ?",
                    (bet, uid),
                )
                conn.commit()
        await asyncio.to_thread(_sync_crash)
        return await update.message.reply_text(
            "💥 The plane hit turbulence and crashed!\n"
            "You lost your full stake."
        )

    multiplier = round(random.uniform(min_mult, max_mult), 2)
    profit     = int(bet * multiplier) - bet

    def _sync_profit():
        with db_lock, get_conn() as conn:
            conn.execute(
                "UPDATE users SET coins = coins + ? WHERE id = ?",
                (profit, uid),
            )
            conn.commit()
            add_earnings(uid, profit)
    await asyncio.to_thread(_sync_profit)

    flight_visual = "🛫" + "➖" * random.randint(4, 10) + "✈️"
    await update.message.reply_text(
        f"{flight_visual}\n\n"
        f"🧠 Risk: <b>{risk.capitalize()}</b>\n"
        f"📈 Multiplier: x<b>{multiplier}</b>\n"
        f"💰 Winnings: ₹{profit}",
        parse_mode="HTML",
    )

async def tea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_query():
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT u.username, s.coins_earned
                FROM user_stats s
                JOIN users u ON u.id = s.uid
                ORDER BY s.coins_earned DESC
                LIMIT 10
            """).fetchall()
            return rows
    rows = await asyncio.to_thread(_sync_query)

    if not rows:
        return await update.message.reply_text("📉 No tea yet. Nobody’s earned anything.")

    msg = "☕ <b>Top Earners:</b>\n"
    for i, (username, coins) in enumerate(rows, start=1):
        msg += f"{i}. @{username} — ₹{coins}\n"

    await update.message.reply_text(msg, parse_mode="HTML")


wire_options = ["🔴", "🔵", "🟢", "🟡", "⚫"]

async def defuse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if len(args) != 2 or args[0] not in ["low", "medium", "high"] or not args[1].isdigit():
        return await update.message.reply_text("⚠️ Usage: /defuse <low|medium|high> <coins>")

    risk = args[0]
    bet = int(args[1])
    coins = await asyncio.to_thread(get_balance, uid)
    if bet <= 0 or coins < bet:
        return await update.message.reply_text("❌ Invalid or insufficient coin amount.")

    remaining = await asyncio.to_thread(check_cooldown, uid, "defuse", cooldown_seconds=90)
    if remaining > 0:
        return await update.message.reply_text(f"⏳ Cooldown: {remaining//60}m {remaining%60}s.")

    settings = {
        "low":    {"mult": 1.5, "cut": 0.5},
        "medium": {"mult": 2.5, "cut": 1.0},
        "high":   {"mult": 4.0, "cut": 1.5}
    }

    chosen = random.choice(wire_options)
    context.user_data["defuse"] = {
        "correct": chosen,
        "mult": settings[risk]["mult"],
        "loss": int(bet * settings[risk]["cut"]),
        "bet": bet
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(w, callback_data=f"wire:{w}") for w in wire_options]
    ])

    await update.message.reply_text(
        f"💣 <b>Defuse Challenge</b>\nChoose the right wire to disarm the bomb!\n\n"
        f"Risk Level: <b>{risk.capitalize()}</b>\nBet: ₹{bet}\n\n"
        f"🧨 One wrong move and it's over.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await asyncio.to_thread(update_cooldown, uid, "defuse")

async def handle_wire_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    info = context.user_data.get("defuse")
    if not info:
        return await query.edit_message_text("❌ No active defuse game found.")

    selected = query.data.split(":")[1]
    context.user_data.pop("defuse", None)

    def _sync_wire():
        with db_lock:
            with get_conn() as conn:
                if selected == info["correct"]:
                    reward = int(info["bet"] * info["mult"])
                    conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (reward, uid))
                    add_earnings(uid, reward)
                    conn.commit()
                    return True, reward
                else:
                    loss = info["loss"]
                    conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (loss, uid))
                    conn.commit()
                    return False, loss
    won, amount = await asyncio.to_thread(_sync_wire)

    if won:
        msg = f"✅ Correct wire ({selected})!\n🎉 You earned ₹{amount}!"
    else:
        msg = f"💥 Wrong wire ({selected})!\n❌ You lost ₹{amount}."

    await query.edit_message_text(msg)


active_raids = {}  # uid → {"by": admin_id, "timestamp": ...}

def start_manual_raid(uid, admin_id):
    active_raids[uid] = {
        "by": admin_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def stop_manual_raid(uid):
    active_raids.pop(uid, None)

def is_raided(uid):
    return uid in active_raids

bribe_status = {}

def is_bribed(uid: int) -> bool:
    return datetime.now() < bribe_status.get(uid, datetime.min)

async def bribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    coins = await asyncio.to_thread(get_balance, uid)

    if coins < 2000:
        return await update.message.reply_text("❌ You need at least ₹2,000 to bribe the system.")

    fee = 2000
    if coins >= 10000:
        fee = int(coins * 0.35)

    expiry = datetime.now() + timedelta(minutes=10)
    bribe_status[uid] = expiry

    def _sync_bribe():
        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (fee, uid))
                conn.commit()
    await asyncio.to_thread(_sync_bribe)

    return await update.message.reply_text(
        f"🕶️ You bribed Reverse God for ₹{fee}.\n"
        f"🚫 Raid protection activated for 10 minutes.\n"
        f"⏳ Expires at <b>{expiry.strftime('%H:%M:%S')}</b>\n"
        "Stay quiet, stay safe.",
        parse_mode=ParseMode.HTML
    )


