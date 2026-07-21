import logging
import json
import random
import time
import sqlite3
import io
import sys
import signal
import asyncio
import re
from datetime import datetime

import telebot
from acommands import register_admin_commands
from database import initialize_database, start_backup_scheduler, backup_database

initialize_database()

from acommands import (
    bot_restart,
    bot_status,
    bot_health,
    status_callback_handler
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from logger import (
    send_alive_logger, send_shutdown_logger, send_start_logger,
    send_group_logger, send_command_logger, send_error_logger,
    send_bank_transaction_logger, send_trade_logger, configure_logger
)

from database import auto_fix_users_table
auto_fix_users_table()

with open("config.json", "r") as f:
    config = json.load(f)

ADMIN_IDS = config["ADMIN_IDS"]

import os

import logging

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

pending_heart = {}
pending_proposal = {}
last_itachi_reward = {}

# ── In-memory stores ──────────────────────────────────────────────────────────
adjust_log = []          # FIX: was referenced but never defined
scheduled_messages = []  # FIX: defined once here, removed duplicate below
flash_sales = {}

print("🚀 Main file started.")

from database import setup_clan_tables
setup_clan_tables()

from database import ensure_market_trades_table
ensure_market_trades_table()

from telegram import ChatMemberUpdated
from telegram.ext import ChatMemberHandler
from telegram.ext import ContextTypes
from welcome_farewell import add_handlers

from database import setup_bank_tables, setup_banktax_table, ensure_system_account

setup_bank_tables()
setup_banktax_table()
ensure_system_account()

from database import add_bribed_column
add_bribed_column()

from database import migrate_users_table
migrate_users_table()

from reply_engine import get_ai_reply

from loan import loan, repay_loan, my_loan, top_loans, deduct_command
from loan import resetloan
from loan import resetallloans

from database import ensure_loans_table
ensure_loans_table()

from giveaway_cards import setup_giveaway_card_tables, migrate_giveaway_card_table
from giveaway_cards import deletegiveawaycard

setup_giveaway_card_tables()
migrate_giveaway_card_table()

from database import setup_game_cooldowns
setup_game_cooldowns()

from database import setup_mines_table, setup_mines_cooldown_table
setup_mines_table()
setup_mines_cooldown_table()

from database import setup_user_stats
setup_user_stats()

from database import setup_pet_system
setup_pet_system()

from database import setup_showroom_tables
setup_showroom_tables()

from database import setup_marketplace
setup_marketplace()

from showroom import additem, showroom, buy, myshowroom
from showroom import listitems, edititem, deleteitem
from showroom import sellitem, market, buymitem, mylistings, cancelitem

from showroom import (
    admin_showroom,
    admin_additem_to,
    admin_removeitem_from,
    admin_market,
    admin_removelisting,
    admin_owners
)

from database import (
    ensure_market_trades_table,
    ensure_user_showroom_table,
    ensure_user_listings_table,
)

ensure_market_trades_table()
ensure_user_showroom_table()
ensure_user_listings_table()

from tnd import (
    start_tnd, join_tnd, ready_tnd, truth_tnd, dare_tnd,
    complete_tnd, leavetnd, endtnd, toptnd, tndstats
)

from games import handle_mines_button
from games import mines
from games import exitmines, minestrap_toggle
from games import tea

from sab import (
    load_circle,
    handle_sab,
    handle_sahab,
    handle_circle_list,
    handle_circle_clear,
    track_group_user
)

load_circle()

from groupmanage import get_groupmanage_handlers

from rakhi import (
    handle_rakhi,
    handle_rakhibond,
    handle_rakhiuntie,
    handle_rakhiwrite,
    handle_rakhiwish,
    handle_rakhiwall,
    handle_rakhiarchive,
    handle_rakhitop
)

from games import dig, blackjack, heist
from games import fly, flystorm, flyshield
from games import tea, bribe
from games import defuse, handle_wire_choice
from pets import adoptpet, feedpet, mypet, petbattle
from pets import handle_battle_response

from admin_cmds import resetwallets, resetdeposit, resetbank, resetinvestments, resetassets, resettea, cleartax
from telegram.ext import CommandHandler
from admin_cmds import broadcastgroups, broadcastdms, dmchat, dm_reply_listener, finduid
from admin_cmds import wanted, raid, unraid

from listeners import itachi_listener, nitho_listener
from telegram.ext import MessageHandler, filters

from database import add_user, update_balance, get_balance

from economy_commands import (
    mybank, bankinfo, bankdeposit, bankwithdraw, bankrank, bankdashboard,
    transferbank, bankmembers, deletebank, banklog, bankstats, bankinvite, bankaudit,
    createbank, joinbank, banklist, leavebank, confirmleavebank,
    myreferrals, referrank, setrefreward,
    taxbank, taxtop, stats, daily, leaderboard,
    invite, referrals, referralscore, referralmap,
    bank, deposit, withdraw, topbank, claiminterest
)

from database import get_ref_reward

from card_utils import get_tax_pool, init_tax_pool
from card_utils import get_user_inventory
from card_utils import save_card_to_user
from card_utils import track_user
from card_utils import get_username

from bank_utils import remove_flash_discount
from card_utils import get_random_card, apply_rarity_bonus

from database import setup_word_scores
setup_word_scores()

from games import flip, roll, rps, guessbet, spin, enter
from word_game import startwordgame, guess, hint, wordscore, wordtop

from group_tools import track_group, mygroups, groupcount

from sdb import init_db
from shandlers import admin_handlers, reaction_handler

from card_editor import uploadcard, draw
from card_editor import decksync, drawpreview, mycards_preview, deckclean
from card_editor import fixcards, mycards, drawpreview
from card_editor import uploadbulk, endbulk, handle_bulk_photo
from card_editor import admincards, purgecard, editcard
from card_editor import get_card_handlers
from card_editor import card_callback

from duel_engine import challenge, button_handler, fight_action
from duel_engine import duel_sessions
from duel_engine import start_combat

from quests import get_all_quests, get_quest_by_name

from giveaway_cards import (
    setup_giveaway_card_tables,
    uploadgiveawaycard, giveawaycards, editgiveawaycardbyindex,
    givecard, mygiveaways, giveawaylist, removegivecard
)
setup_giveaway_card_tables()

from clan_utils import (
    createclan,
    joinclan,
    clangoal,
    voteleader,
    clanrank,
    myclan,
    leaveclan,
    settitle
)

from welcome_manager import (
    greet_chat_members,
    welcome,
    farewell,
    setwelcome,
    setfarewell,
    viewwelcome
)

from card_utils import setup_tax_bank, deposit_tax, distribute_tax_rewards

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
    JobQueue
)

from database import (
    get_conn,
    add_user,
    get_balance,
    update_balance,
    set_balance,
    get_all_user_ids,
    get_user_by_username,
    get_all_users,
    remove_user_by_id,
    remove_user_by_username,
    transfer_coins,
    get_leaderboard,
    purge_users,
    get_low_balance_users,
    add_admin,
    remove_admin,
    get_admin_list,
    get_all_group_ids,   # FIX: was missing from import
)

from card_utils import (
    get_username,
    can_earn,
    update_earn_time,
    get_conn,
    init_db,
    create_duel_table,
    setup_tables,
    ensure_last_active_column,
    ensure_karma_column,
    track_user,
    track_group,
    log_transfer,
    get_card_by_index,
    remove_card_by_name,
    list_all_cards,
    get_deck_size,
    get_random_card,
    apply_rarity_bonus,
    get_recent_users,
    get_duel_rank,
    get_karma,
    format_karma,
    get_user_relics,
    get_user_artefacts,
    add_card,
    remove_card,
    get_transfer_logs
)

create_duel_table()
init_db()

with get_conn() as conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS earn_times (
        uid INTEGER PRIMARY KEY,
        last_claimed INTEGER
    )
    """)
    conn.commit()

setup_tables()
ensure_last_active_column()
ensure_karma_column()

setup_tax_bank()

from bank_utils import (
    setup_bank_tables,
    setup_dynamic_prices,
    seed_asset_prices,
    setup_badge_table,
    setup_achievements_table,
    setup_quest_table,
    setup_group_goals_table,
    ASSET_LORE,
    get_asset_market,
    buy_asset,
    get_user_assets,
    fluctuate_asset_prices,
    assign_investor_badge,
    update_achievements
)

setup_bank_tables()
setup_dynamic_prices()
seed_asset_prices()
setup_badge_table()
setup_achievements_table()
setup_quest_table()
setup_group_goals_table()

from duel_utils import run_duel, update_duel_stats

BOT_TOKEN = config.get("BOT_TOKEN")
ADMIN_IDS = config.get("ADMIN_IDS", [])

logging.basicConfig(level=logging.INFO)

configure_logger(logger_id=-1003964165574, enable_debug=False)


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🧭 <b>Welcome PLAYER!</b>\nHere are your available commands, grouped by category:\n\n"

        "💰 <b>Economy</b>\n"
        "• /earn — Claim daily coins\n"
        "• /balance — Check your coin balance\n"
        "• /give @user &lt;amount&gt; — Gift coins\n"
        "• /send @user &lt;amount&gt; — Send coins\n"
        "• /transfer @user &lt;amount&gt; — Transfer coins\n"
        "• /top — View group leaderboard\n"
        "• /btop — View bot leaderboard\n"
        "• /request &lt;amount&gt; — Request coins\n"
        "• /bankstats — View global asset stats\n"

        "\n🎴 <b>Cards & Spells</b>\n"
        "• /draw — Draw a spell card\n"
        "• /mycards — View your cards\n"
        "• /steal — Attempt to steal a card\n"
        "• /cardlist — List all available cards\n"
        "• /vault — View your relics & artefacts\n"
        "• /cardvault — View card vault\n"
        "• /prestigevault — View prestige cards\n"

        "\n⚔️ <b>Combat</b>\n"
        "• /challenge — Challenge someone to a duel\n"
        "• /duelrank — View your duel stats\n"
        "• /duelbadge — View your duel badge\n"
        "• /bossfight — Fight a boss\n"

        "\n🌟 <b>Karma & Tasks</b>\n"
        "• /karma — View your karma\n"
        "• /karmaquiz — Test your karma\n"
        "• /karmahall — View karma leaderboard\n"
        "• /dailymission — Get your daily mission\n"
        "• /claimstreak — Claim streak reward\n"
        "• /achievements — View your achievements\n"

        "\n🏪 <b>Market & Assets</b>\n"
        "• /assetmarket — Browse investment assets\n"
        "• /buyasset &lt;name&gt; — Purchase asset\n"
        "• /myassets — View your assets\n"
        "• /collectincome — Collect passive income\n"
        "• /sellasset &lt;name&gt; — Sell an asset\n"
        "• /assetinfo &lt;name&gt; — Info about an asset\n"
        "• /investrank — View top investors\n"
        "• /assetcompare A | B — Compare two assets\n"
        "• /assettrend &lt;name&gt; — View price trend\n"
        "• /assetlore &lt;name&gt; — View lore\n"
        "• /assettitle — Your asset-based title\n"

        "\n📖 <b>Progress & Quests</b>\n"
        "• /profilecard — View your profile\n"
        "• /shinobirank — Prestige leaderboard\n"
        "• /shinobititle — Your shinobi title\n"
        "• /shinobibadge — View your badge\n"
        "• /shinobilegacy — Your legacy stats\n"
        "• /questbook — View your quests\n"
        "• /groupgoal — View group goal\n"
        "• /clangoal — View clan-wide goal\n"

        "\n🔮 <b>Gambling & Luck</b>\n"
        "• /fly &lt;coins&gt; — Risk coins in flight\n"
        "• /mines &lt;bombs&gt; &lt;coins&gt; — Dodge bombs, win coins\n"
        "• /blackjack &lt;coins&gt; — Play blackjack\n"
        "• /dig &lt;1-10&gt; — Dig for random rewards\n"

        "\n🏎️ <b>Vehicles & Showroom</b>\n"
        "• /showroom — View all cars and bikes in the showroom\n"
        "• /myshowroom — View your personal showroom\n"
        "• /buy &lt;id&gt; — Buy a vehicle from the showroom\n"
        "• /sellitem — Sell your cars or bikes\n"
        "• /market — View vehicles listed by other users\n"
        "• /buyitem — Buy a vehicle from the market\n"
        "• /mylistings — View your active listings\n"
        "• /cancelitem — Cancel a listed item\n"

        "\n🛠️ <b>Utilities</b>\n"
        "• /start — Begin your journey\n"
        "• /help — Show this command list\n"

        "\n🩷 <i>Use 'Itachi' and 'best' in one sentence once every 4 Hours to earn coins</i>\n"
        "\n🌸 May your journey be guided by honor and wisdom."

        "\n\n<b>📘 Itachi Bot Help Guide</b>\n"
        "📩 If you have any problem or query about the bot,\n"
        "please reach out to our masters:\n"
        "👤 <b>@Itachiplub2</b>\n"
        "👤 <b>@Avalon_18</b>\n"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def allcards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # FIX: allow in private too — only enforce admin check in groups
    if chat.type in ("group", "supergroup"):
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            return await update.message.reply_text("🔒 You must be an admin to use this.")

    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT file_id, json FROM deck").fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("📭 Deck is empty.")

    media_group = []
    for file_id, raw in rows:
        try:
            card = json.loads(raw)
            caption = (
                f"🎴 <b>{card.get('name')}</b>\n"
                f"🪄 {card.get('power')}\n"
                f"💠 {card.get('rarity').title()}"
            )
        except Exception:
            caption = None

        if file_id:
            media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"))

        if len(media_group) == 10:
            await update.message.reply_media_group(media=media_group)
            media_group = []

    if media_group:
        await update.message.reply_media_group(media=media_group)


async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user
    sender_id = sender.id
    args = context.args or []

    if update.message.reply_to_message:
        recipient_id = update.message.reply_to_message.from_user.id
        card_name = " ".join(args).strip()
    else:
        if len(args) < 2:
            return await update.message.reply_text("📦 Usage: /gift <card name> @username")
        *name_parts, target = args
        card_name = " ".join(name_parts).strip()
        if not target.startswith("@"):
            return await update.message.reply_text("🚫 Tag the recipient with @username.")
        username = target[1:]
        def _sync_op():
            with get_conn() as conn:
                return conn.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
        row = await asyncio.to_thread(_sync_op)
        if not row:
            return await update.message.reply_text(f"❌ User @{username} not found.")
        recipient_id = row[0]

    if recipient_id == sender_id:
        return await update.message.reply_text("🫣 You can't gift a card to yourself.")

    if not card_name:
        return await update.message.reply_text("❌ You must specify the card name to gift.")

    def _sync_op():
        with get_conn() as conn:
            row = conn.execute("""
                SELECT rowid, file_id, name, power, value, rarity
                FROM user_cards
                WHERE uid=? AND LOWER(name)=?
                LIMIT 1
            """, (sender_id, card_name.lower())).fetchone()

            if not row:
                return None

            rowid, file_id, name, power, value, rarity = row
            conn.execute("DELETE FROM user_cards WHERE rowid=?", (rowid,))
            conn.execute("""
                INSERT INTO user_cards (user_id, file_id, name, power, value, rarity, drawn_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipient_id, file_id, name, power, value, rarity, int(time.time())))
            conn.commit()
            return (file_id, name)
    result = await asyncio.to_thread(_sync_op)
    if result is None:
        return await update.message.reply_text(f"🔍 No card named '{card_name}' in your vault.")
    file_id, name = result

    recipient_tag = await resolve_name(update.effective_chat.id, recipient_id, context)
    await update.message.reply_text(
        f"🎁 You sent '<b>{name}</b>' to {recipient_tag}.",
        parse_mode="HTML"
    )
    try:
        await context.bot.send_message(
            chat_id=recipient_id,
            text=f"💝 You received '<b>{name}</b>' from <b>{sender.username or sender.first_name}</b>!",
            parse_mode="HTML"
        )
    except Exception:
        pass


EXCHANGE_TAX_RATE = 0.05

async def exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user
    sender_id = sender.id
    args = context.args or []

    if update.message.reply_to_message:
        recipient = update.message.reply_to_message.from_user
        recipient_id = recipient.id
        if len(args) < 2:
            return await update.message.reply_text(
                "📦 Usage (reply): `/exchange <your_card> <their_card>`",
                parse_mode="Markdown"
            )
        your_name, their_name = args[0], args[1]
    else:
        if len(args) < 3 or not args[1].startswith("@"):
            return await update.message.reply_text(
                "📦 Usage: `/exchange <your_card> @username <their_card>`",
                parse_mode="Markdown"
            )
        your_name = args[0]
        their_name = args[2]
        username = args[1][1:]
        def _sync_op():
            with get_conn() as conn:
                return conn.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
        row = await asyncio.to_thread(_sync_op)
        if not row:
            return await update.message.reply_text(f"❌ User @{username} not found.")
        recipient_id = row[0]

    if recipient_id == sender_id:
        return await update.message.reply_text("🫣 You can't exchange with yourself.")

    now = int(time.time())
    def _sync_op():
        with get_conn() as conn:
            row1 = conn.execute("""
                SELECT rowid, file_id, name, power, value, rarity
                FROM user_cards WHERE uid=? AND LOWER(name)=? LIMIT 1
            """, (sender_id, your_name.lower())).fetchone()
            row2 = conn.execute("""
                SELECT rowid, file_id, name, power, value, rarity
                FROM user_cards WHERE uid=? AND LOWER(name)=? LIMIT 1
            """, (recipient_id, their_name.lower())).fetchone()

            if not row1:
                return ("no_yours",)
            if not row2:
                return ("no_theirs",)

            id1, fid1, nm1, pw1, val1, rar1 = row1
            id2, fid2, nm2, pw2, val2, rar2 = row2

            conn.execute("DELETE FROM user_cards WHERE rowid=?", (id1,))
            conn.execute("DELETE FROM user_cards WHERE rowid=?", (id2,))
            conn.commit()

            conn.execute("""
                INSERT INTO user_cards (uid, file_id, name, power, value, rarity, drawn_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipient_id, fid1, nm1, pw1, val1, rar1, now))
            conn.execute("""
                INSERT INTO user_cards (uid, file_id, name, power, value, rarity, drawn_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sender_id, fid2, nm2, pw2, val2, rar2, now))
            conn.commit()
            return ("ok", nm1, val1, nm2, val2)
    result = await asyncio.to_thread(_sync_op)
    if result[0] == "no_yours":
        return await update.message.reply_text(f"🔍 You don't own '{your_name}'.")
    if result[0] == "no_theirs":
        return await update.message.reply_text(f"🔍 Recipient doesn't own '{their_name}'.")
    _, nm1, val1, nm2, val2 = result

    tax1 = int(val1 * EXCHANGE_TAX_RATE)
    tax2 = int(val2 * EXCHANGE_TAX_RATE)
    await asyncio.to_thread(deposit_tax, tax1 + tax2)

    await update.message.reply_text(
        f"🔄 Swapped:\n"
        f" • You gave '{nm1}' and received '{nm2}'.\n"
        f"💸 Tax charged: {tax1 + tax2} coins.",
        parse_mode="HTML"
    )
    try:
        await context.bot.send_message(
            chat_id=recipient_id,
            text=(
                f"💱 You received '{nm1}' from {sender.username or sender.first_name}!\n"
                f"🔄 Exchanged for your '{nm2}'."
            )
        )
    except Exception:
        pass


async def assetmarket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assets = get_asset_market()
    if not assets:
        return await update.message.reply_text("📭 No assets available in ITACHI'S SECURE BANK.")

    lines = ["🏦 <b>ITACHI'S SECURE BANK — Asset Market</b>:"]
    for name, type_, cost, yield_, risk in assets:
        lines.append(
            f"🔹 <b>{name}</b> ({type_})\n"
            f"💰 Cost: {cost} coins\n"
            f"📈 Yield: {yield_}/day\n"
            f"⚠️ Risk: {risk}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def buyasset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    if not context.args:
        return await update.message.reply_text("🛒 Usage: /buyasset <asset_name> [quantity]")

    args = context.args
    quantity = 1

    if args and args[-1].isdigit():
        quantity = int(args[-1])
        asset_name = " ".join(args[:-1])
    else:
        asset_name = " ".join(args)

    if quantity <= 0:
        return await update.message.reply_text("🚫 Quantity must be a positive number.")

    assets = get_asset_market()
    asset = next((a for a in assets if a[0].lower() == asset_name.lower()), None)
    if not asset:
        return await update.message.reply_text(f"❌ Asset '{asset_name}' not found in ITACHI'S SECURE BANK.")

    name, type_, _, yield_, risk = asset

    def _sync_op():
        with get_conn() as conn:
            return conn.execute(
                "SELECT price FROM asset_prices WHERE name=? ORDER BY timestamp DESC LIMIT 1",
                (name,)
            ).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text("❌ No price data available for this asset.")
    cost = row[0]

    total_cost = cost * quantity
    coins = await asyncio.to_thread(get_balance, uid)
    if coins < total_cost:
        return await update.message.reply_text(
            f"🚫 You need {total_cost} coins to buy <b>{quantity}x {name}</b>. You only have {coins}.",
            parse_mode="HTML"
        )

    await asyncio.to_thread(update_balance, uid, -total_cost)
    await asyncio.to_thread(buy_asset, uid, name, quantity)
    await asyncio.to_thread(assign_investor_badge, uid)
    await asyncio.to_thread(update_achievements, uid)

    await update.message.reply_text(
        f"✅ <b>{username}</b> purchased <b>{quantity}x {name}</b> from ITACHI'S SECURE BANK!\n"
        f"💰 Total Cost: {total_cost} coins\n📈 Daily Yield: {yield_ * quantity} coins\n⚠️ Risk Level: {risk}",
        parse_mode="HTML"
    )


async def myassets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    assets = get_user_assets(uid)
    if not assets:
        return await update.message.reply_text(f"📭 <b>{username}</b>, you don't own any assets yet.", parse_mode="HTML")

    lines = [f"💼 <b>{username}'s Portfolio — ITACHI'S SECURE BANK</b>:"]
    total_yield = 0

    for name, type_, cost, yield_, risk, qty in assets:
        income = yield_ * qty
        total_yield += income
        lines.append(
            f"🔸 <b>{name}</b> ({type_})\n"
            f"📦 Quantity: {qty}\n"
            f"📈 Daily Yield: {income} coins\n"
            f"⚠️ Risk: {risk}\n"
        )

    lines.append(f"\n💰 <b>Total Passive Income:</b> {total_yield} coins/day")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def collectincome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    now = int(time.time())
    assets = get_user_assets(uid)
    if not assets:
        return await update.message.reply_text(f"📭 <b>{username}</b>, you don't own any assets yet.", parse_mode="HTML")

    total_income = 0

    def _sync_op():
        nonlocal total_income
        with get_conn() as conn:
            for nm, type_, cost, yield_, risk, qty in assets:
                row = conn.execute(
                    "SELECT last_collected FROM user_assets WHERE uid=? AND asset_name=?",
                    (uid, nm)
                ).fetchone()

                last_collected = row[0] if row else 0
                elapsed = now - last_collected

                if elapsed >= 86400:
                    income = yield_ * qty
                    total_income += income
                    conn.execute(
                        "UPDATE user_assets SET last_collected=? WHERE uid=? AND asset_name=?",
                        (now, uid, nm)
                    )
    await asyncio.to_thread(_sync_op)

    if total_income == 0:
        return await update.message.reply_text("🕒 You've already collected income in the last 24 hours.")

    await asyncio.to_thread(update_balance, uid, total_income)
    await asyncio.to_thread(assign_investor_badge, uid)
    await asyncio.to_thread(update_achievements, uid)

    await update.message.reply_text(
        f"✅ <b>{username}</b>, you've collected <b>{total_income}</b> coins from your assets!\n"
        f"🏦 Thank you for banking with ITACHI'S SECURE BANK.",
        parse_mode="HTML"
    )


async def sellasset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    if not context.args:
        return await update.message.reply_text("🧾 Usage: /sellasset <asset_name>")

    asset_name = " ".join(context.args).strip()
    assets = get_user_assets(uid)
    owned = next((a for a in assets if a[0].lower() == asset_name.lower()), None)
    if not owned:
        return await update.message.reply_text(f"❌ You don't own any '{asset_name}' to sell.")

    name, type_, _, yield_, risk, qty = owned

    def _sync_op():
        with get_conn() as conn:
            return conn.execute(
                "SELECT price FROM asset_prices WHERE name=? ORDER BY timestamp DESC LIMIT 1",
                (name,)
            ).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text("❌ No price data available for this asset.")
    current_price = row[0]
    refund = current_price * qty

    def _sync_op2():
        with get_conn() as conn:
            conn.execute("DELETE FROM user_assets WHERE uid=? AND asset_name=?", (uid, name))
    await asyncio.to_thread(_sync_op2)

    await asyncio.to_thread(update_balance, uid, refund)
    await asyncio.to_thread(assign_investor_badge, uid)
    await asyncio.to_thread(update_achievements, uid)

    await update.message.reply_text(
        f"✅ <b>{username}</b> sold <b>{qty}x {name}</b> for <b>{refund}</b> coins at market price.\n"
        f"🏦 Thank you for banking with ITACHI'S SECURE BANK.",
        parse_mode="HTML"
    )


async def mintasset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can mint new assets.")

    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 5:
        return await update.message.reply_text("🧾 Usage: /mintasset Name | type | cost | yield | risk")

    name, type_, cost_str, yield_str, risk = parts
    try:
        cost = int(cost_str)
        yield_ = int(yield_str)
    except ValueError:
        return await update.message.reply_text("🚫 Cost and yield must be integers.")

    def _sync_op():
        with get_conn() as conn:
            exists = conn.execute("SELECT 1 FROM assets WHERE name=?", (name,)).fetchone()
            if exists:
                return "exists"
            conn.execute("INSERT INTO assets (name, type, cost, yield, risk) VALUES (?, ?, ?, ?, ?)",
                         (name, type_, cost, yield_, risk))
            ts = int(time.time())
            conn.execute("INSERT INTO asset_prices (name, price, timestamp) VALUES (?, ?, ?)", (name, cost, ts))
            conn.commit()
            return "ok"
    result = await asyncio.to_thread(_sync_op)
    if result == "exists":
        return await update.message.reply_text(f"⚠️ Asset '{name}' already exists.")

    await update.message.reply_text(
        f"✅ Minted <b>{name}</b>!\n💰 Cost: {cost} coins\n📈 Yield: {yield_}/day\n⚠️ Risk: {risk}",
        parse_mode="HTML"
    )


async def removeasset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can remove assets.")

    if not context.args:
        return await update.message.reply_text("🧾 Usage: /removeasset <asset_name>")

    asset_name = " ".join(context.args).strip()

    def _sync_op():
        with get_conn() as conn:
            exists = conn.execute("SELECT 1 FROM assets WHERE name=?", (asset_name,)).fetchone()
            if not exists:
                return "not_found"
            conn.execute("DELETE FROM assets WHERE name=?", (asset_name,))
            conn.execute("DELETE FROM asset_prices WHERE name=?", (asset_name,))
            conn.execute("DELETE FROM user_assets WHERE asset_name=?", (asset_name,))
            conn.commit()
            return "ok"
    result = await asyncio.to_thread(_sync_op)
    if result == "not_found":
        return await update.message.reply_text(f"❌ Asset '{asset_name}' not found.")

    await update.message.reply_text(
        f"🗑️ Asset '<b>{asset_name}</b>' has been removed from ITACHI'S SECURE BANK.",
        parse_mode="HTML"
    )


async def investrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT ua.uid, SUM(a.cost * ua.quantity) AS total_value
                FROM user_assets ua
                JOIN assets a ON ua.asset_name = a.name
                GROUP BY ua.uid ORDER BY total_value DESC LIMIT 10
            """).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("📭 No investors found in ITACHI'S SECURE BANK.")

    lines = ["🏦 <b>Top Investors — ITACHI'S SECURE BANK</b>:"]
    for i, (uid, value) in enumerate(rows, start=1):
        username = await asyncio.to_thread(get_username, uid)
        lines.append(f"{i}. <b>{username}</b> — 💼 Portfolio Value: {value} coins")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def assetinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("🔍 Usage: /assetinfo <asset_name>")

    asset_name = " ".join(context.args).strip()
    assets = get_asset_market()
    asset = next((a for a in assets if a[0].lower() == asset_name.lower()), None)

    if not asset:
        return await update.message.reply_text(f"❌ Asset '{asset_name}' not found in ITACHI'S SECURE BANK.")

    name, type_, cost, yield_, risk = asset
    await update.message.reply_text(
        f"📊 <b>Asset Info — {name}</b>\n"
        f"🏷️ Type: {type_}\n💰 Cost: {cost} coins\n📈 Daily Yield: {yield_} coins\n"
        f"⚠️ Risk Level: {risk}\n🏦 Available in ITACHI'S SECURE BANK",
        parse_mode="HTML"
    )


async def assettrend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("📊 Usage: /assettrend <asset_name>")

    asset_name = " ".join(context.args).strip()
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT timestamp, price FROM asset_prices WHERE name=?
                ORDER BY timestamp DESC LIMIT 5
            """, (asset_name,)).fetchall()
    history = await asyncio.to_thread(_sync_op)

    if not history:
        return await update.message.reply_text(f"❌ No price data found for '{asset_name}'.")

    lines = [f"📉 <b>Price Trend — {asset_name.title()}</b>:"]
    for ts, price in reversed(history):
        dt = time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))
        lines.append(f"🕒 {dt} — 💰 {price} coins")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def auditvault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can audit the vault.")

    def _sync_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT a.type, SUM(a.cost * ua.quantity) AS total_value
                FROM user_assets ua JOIN assets a ON ua.asset_name = a.name
                GROUP BY a.type
            """).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("📭 No assets found in the vault.")

    lines = ["🏛️ <b>Community Vault — ITACHI'S SECURE BANK</b>:"]
    total = 0
    for type_, value in rows:
        total += value
        lines.append(f"🔹 <b>{type_.title()}</b>: {value} coins")
    lines.append(f"\n💰 <b>Total Vault Value:</b> {total} coins")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def assetshare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("📊 Usage: /assetshare <asset_name>")

    asset_name = " ".join(context.args).strip()
    def _sync_op():
        with get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(DISTINCT uid) FROM user_assets WHERE asset_name=?", (asset_name,)
            ).fetchone()[0]
    count = await asyncio.to_thread(_sync_op)

    await update.message.reply_text(
        f"📈 <b>{count}</b> users currently own <b>{asset_name.title()}</b>.",
        parse_mode="HTML"
    )


async def bankstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            total_users = conn.execute("SELECT COUNT(DISTINCT uid) FROM user_assets").fetchone()[0]
            total_assets = conn.execute("SELECT COUNT(*) FROM user_assets").fetchone()[0]
            total_income = conn.execute("""
                SELECT SUM(a.yield * ua.quantity) FROM user_assets ua
                JOIN assets a ON ua.asset_name = a.name
            """).fetchone()[0]
            return total_users, total_assets, total_income
    total_users, total_assets, total_income = await asyncio.to_thread(_sync_op)

    await update.message.reply_text(
        f"📊 <b>ITACHI'S SECURE BANK — Global Stats</b>\n"
        f"👥 Investors: {total_users}\n📦 Total Assets Held: {total_assets}\n"
        f"💰 Daily Passive Income Potential: {total_income} coins",
        parse_mode="HTML"
    )


async def assetcompare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("📊 Usage: /assetcompare <Asset A> | <Asset B>")

    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 2:
        return await update.message.reply_text("🚫 Format: Asset A | Asset B")

    a_name, b_name = parts
    assets = get_asset_market()
    a = next((x for x in assets if x[0].lower() == a_name.lower()), None)
    b = next((x for x in assets if x[0].lower() == b_name.lower()), None)

    if not a or not b:
        return await update.message.reply_text("❌ One or both assets not found.")

    def format_asset(data):
        name, type_, cost, yield_, risk = data
        return f"<b>{name}</b>\n💰 Cost: {cost}\n📈 Yield: {yield_}/day\n⚠️ Risk: {risk}\n🏷️ Type: {type_}"

    await update.message.reply_text(
        f"📊 <b>Asset Comparison</b>\n\n{format_asset(a)}\n\n🆚\n\n{format_asset(b)}",
        parse_mode="HTML"
    )


async def assetlore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("📜 Usage: /assetlore <asset_name>")

    asset_name = " ".join(context.args).strip()
    lore = ASSET_LORE.get(asset_name.title())

    if not lore:
        return await update.message.reply_text(f"❌ No lore found for '{asset_name}'.")

    await update.message.reply_text(f"📜 <b>{asset_name.title()} Lore</b>\n{lore}", parse_mode="HTML")


def parse_duration(s: str) -> int:
    m = re.match(r"^(\d+)([smhSMH])?$", s)
    if not m:
        return 0
    val = int(m.group(1))
    unit = m.group(2).lower() if m.group(2) else "s"
    return {"s": 1, "m": 60, "h": 3600}[unit] * val


async def _end_flash_sale(context: ContextTypes.DEFAULT_TYPE):
    asset_name = context.job.data
    flash_sales.pop(asset_name, None)
    success = remove_flash_discount(asset_name)
    if success:
        print(f"⏰ Flash sale ended: {asset_name} price restored to base cost.")
    else:
        print(f"⚠️ Flash sale cleanup failed: asset '{asset_name}' not found.")


async def flashsale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can trigger flash sales.")

    if len(context.args) != 3:
        return await update.message.reply_text(
            "🛍️ Usage: /flashsale <asset_name> <discount%> <duration>\n"
            "Example: /flashsale BITCOIN 25 30m"
        )

    asset_name = context.args[0]
    try:
        discount = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("🚫 Discount must be a number.")

    duration_sec = parse_duration(context.args[2])
    if duration_sec <= 0:
        return await update.message.reply_text("🚫 Invalid duration. Use 30m, 2h, or seconds.")

    from bank_utils import apply_flash_discount
    apply_flash_discount(asset_name, discount)

    expiry = int(time.time()) + duration_sec
    flash_sales[asset_name] = expiry
    context.job_queue.run_once(_end_flash_sale, when=duration_sec, data=asset_name)

    await update.message.reply_text(
        f"🔥 FLASH SALE! {asset_name} is {discount}% off for the next {context.args[2]}.\n"
        f"🏦 Available at ITACHI'S SECURE BANK.",
        parse_mode="HTML"
    )


def auto_collect_income():
    now = int(time.time())
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT ua.uid, ua.asset_name, ua.quantity, ua.last_collected, a.yield
            FROM user_assets ua JOIN assets a ON ua.asset_name = a.name
        """).fetchall()
        for uid, asset, qty, last, daily_yield in rows:
            if now - (last or 0) >= 86400:
                income = daily_yield * qty
                update_balance(uid, income)
                assign_investor_badge(uid)
                update_achievements(uid)
                conn.execute(
                    "UPDATE user_assets SET last_collected=? WHERE uid=? AND asset_name=?",
                    (now, uid, asset)
                )
        conn.commit()


def scheduled_asset_appreciation():
    fluctuate_asset_prices()


async def runbankengine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Admin only.")
    auto_collect_income()
    scheduled_asset_appreciation()
    await update.message.reply_text("✅ Bank engine executed: income collected & asset prices updated.")


async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT * FROM achievements WHERE uid=?", (uid,)).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text(f"📭 <b>{username}</b>, no achievements found yet.", parse_mode="HTML")

    _, first, total, income, diversified = row
    join_date = time.strftime('%Y-%m-%d', time.localtime(first))

    await update.message.reply_text(
        f"🏅 <b>{username}'s Achievements — ITACHI'S SECURE BANK</b>\n"
        f"📆 First Investment: {join_date}\n📦 Assets Owned: {total}\n"
        f"💰 Passive Income Potential: {income}/day\n🌐 Diversification Score: {diversified} types",
        parse_mode="HTML"
    )


async def assettitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT max_income, diversified FROM achievements WHERE uid=?", (uid,)).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text("📭 No title yet. Start investing!")

    income, diversified = row
    if income >= 500 and diversified >= 4:
        title = "🌐 Shinobi Syndicate Leader"
    elif income >= 250:
        title = "📈 Strategic Tycoon"
    elif diversified >= 3:
        title = "🌀 Multi-Asset Ninja"
    else:
        title = "💼 Rising Investor"

    await update.message.reply_text(
        f"🏷️ <b>Your Title:</b> {title}\nKeep growing to unlock elite status!",
        parse_mode="HTML"
    )


async def questbook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    lines = [f"📖 <b>{username}'s Questbook — ITACHI'S SECURE BANK</b>:"]

    def _sync_op():
        with get_conn() as conn:
            result = []
            for quest in get_all_quests():
                name = quest["name"]
                row = conn.execute("SELECT completed FROM quests WHERE uid=? AND quest_name=?", (uid, name)).fetchone()
                status = "✅ Completed" if row and row[0] else "❌ Incomplete"
                result.append(f"🔹 <b>{name}</b>: {status}\n📝 {quest['description']}\n🎁 Reward: {quest['reward']} coins\n")
            return result
    quest_lines = await asyncio.to_thread(_sync_op)
    lines.extend(quest_lines)

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


def complete_quest(uid: int, name: str, context):
    quest = get_quest_by_name(name)
    if not quest:
        return False

    with get_conn() as conn:
        row = conn.execute("SELECT completed FROM quests WHERE uid=? AND quest_name=?", (uid, name)).fetchone()
        if row and row[0]:
            return False
        conn.execute("REPLACE INTO quests (uid, quest_name, completed) VALUES (?, ?, ?)", (uid, name, True))
        conn.commit()

    update_balance(uid, quest["reward"])
    try:
        context.bot.send_message(
            chat_id=uid,
            text=(
                f"🎯 <b>Quest Completed</b>\n✅ <b>{name}</b>\n"
                f"🎁 Reward: {quest['reward']} coins added to your balance."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass
    return True


async def groupgoal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT goal_name, target, progress, completed FROM group_goals").fetchall()
    rows = await asyncio.to_thread(_sync_op)
    if not rows:
        return await update.message.reply_text("📭 No group goals found.")

    lines = ["🏯 <b>Clan Goals — ITACHI'S SECURE BANK</b>:"]
    for name, target, progress, done in rows:
        status = "✅ Completed" if done else f"🔄 {progress}/{target}"
        lines.append(f"🔹 {name}: {status}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def fluctuateprices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Admin only.")
    fluctuate_asset_prices()
    await update.message.reply_text("✅ Asset prices have been updated.")


DAILY_TASKS = ["Filhal Berojgaron ke liya koi task nhi."]
user_missions = {}


async def dailymission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_missions:
        return await update.message.reply_text(f"📜 Your mission today:\n<b>{user_missions[uid]}</b>", parse_mode="HTML")
    task = random.choice(DAILY_TASKS)
    user_missions[uid] = task
    await update.message.reply_text(f"🎯 <b>Daily Mission</b>:\n{task}", parse_mode="HTML")


def get_streak(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT streak_day, last_claimed FROM streaks WHERE uid=?", (uid,)).fetchone()
        return row if row else (0, 0)


def update_streak(uid, day, now):
    with get_conn() as conn:
        conn.execute("REPLACE INTO streaks (uid, streak_day, last_claimed) VALUES (?, ?, ?)", (uid, day, now))
        conn.commit()


async def claimstreak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = int(time.time())
    day, last = get_streak(uid)

    if now - last < 86400:
        return await update.message.reply_text("🕒 You've already claimed your streak today.")

    day = day + 1 if now - last < 172800 else 1
    reward = 50 + (day * 10)
    await asyncio.to_thread(update_balance, uid, reward)
    await asyncio.to_thread(update_streak, uid, day, now)

    await update.message.reply_text(
        f"🔥 <b>Streak Day {day}</b>\nYou earned <b>{reward}</b> coins!",
        parse_mode="HTML"
    )


async def profilecard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    coins = await asyncio.to_thread(get_balance, uid)
    karma = get_karma(uid)
    wins, losses, draws = get_duel_rank(uid)
    day, _ = get_streak(uid)

    if wins >= 50 and karma >= 100:
        title = "🌌 Shinobi Legend"
    elif wins >= 25:
        title = "⚔️ Duel Master"
    elif karma >= 50:
        title = "✨ Karma Sage"
    else:
        title = "🎴 Rising Shinobi"

    relics = get_user_relics(uid)
    artefacts = get_user_artefacts(uid)
    prestige = karma + len(relics) * 100 + len(artefacts) * 150

    await update.message.reply_text(
        f"🧙 <b>{username}'s Profile Card</b>\n🏷️ Title: {title}\n💰 Coins: {coins}\n"
        f"🌟 Karma: {format_karma(karma)}\n🏆 Wins: {wins} | ❌ Losses: {losses} | 🤝 Draws: {draws}\n"
        f"🔥 Streak: {day} days\n🧠 Prestige Score: {prestige}",
        parse_mode="HTML"
    )


async def bossfight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    boss = {
        "name": "Shadow Kurama",
        "hp": 150,
        "attack": random.randint(20, 40),
        "reward": random.randint(200, 500)
    }

    player_hp = 100
    boss_hp = boss["hp"]
    log = [f"⚔️ <b>{username} vs {boss['name']}</b>"]

    while player_hp > 0 and boss_hp > 0:
        player_hit = random.randint(15, 35)
        boss_hit = boss["attack"]
        boss_hp -= player_hit
        player_hp -= boss_hit
        log.append(f"🗡️ You hit for {player_hit} | 🧟 Boss hits for {boss_hit}")

    if player_hp > 0:
        await asyncio.to_thread(update_balance, uid, boss["reward"])
        log.append(f"\n🏆 Victory! You earned {boss['reward']} coins.")
    else:
        log.append("\n💀 Defeated! Better luck next time.")

    await update.message.reply_text("\n".join(log), parse_mode="HTML")


async def duelnews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_duelists = get_duel_rank(limit=5)
    if not top_duelists:
        return await update.message.reply_text("📭 No duel activity found.")

    lines = ["📰 <b>Duel Arena News</b>:"]
    for i, (uid, coins) in enumerate(top_duelists, start=1):
        username = await asyncio.to_thread(get_username, uid)
        lines.append(f"{i}. <b>{username}</b> — {coins} coins")

    lines.append("\n⚔️ Duel heat rising! Who will claim the top spot?")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def banknews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT name, price FROM asset_prices
                WHERE timestamp >= strftime('%s','now','-1 day')
                ORDER BY price DESC LIMIT 5
            """).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("📭 No recent asset activity.")

    lines = ["🏦 <b>Bank Market News</b>:"]
    for name, price in rows:
        lines.append(f"💹 <b>{name}</b> surged to <b>{price}</b> coins!")
    lines.append("\n🔥 Flash sales may be coming soon. Stay alert!")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def npcvisit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    npcs = [
        {"name": "Master Itachi", "quote": "True power comes from restraint."},
        {"name": "Rogue Trader", "quote": "I've got rare cards... for a price."},
        {"name": "Shadow Duelist", "quote": "Care to test your fate in the dark?"}
    ]
    npc = random.choice(npcs)
    await update.message.reply_text(
        f"👤 <b>{npc['name']} appears!</b>\n🗨️ \"{npc['quote']}\"",
        parse_mode="HTML"
    )


async def cardstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = list_all_cards()
    if not cards:
        return await update.message.reply_text("📭 No cards found in the vault.")

    total = len(cards)
    rarity_count = {}
    for card in cards:
        rarity = card.get("rarity", "Unknown").title()
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1

    lines = [f"📊 <b>Card Vault Stats</b>\nTotal Cards: {total}"]
    for rarity, count in rarity_count.items():
        lines.append(f"🎴 {rarity}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def prestigevault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = list_all_cards()
    if not cards:
        return await update.message.reply_text("📭 No cards found.")

    filtered = [c for c in cards if c.get("rarity", "").lower() in ["legendary", "mythic", "special mythic"]]
    if not filtered:
        return await update.message.reply_text("🔒 No prestige cards found.")

    lines = ["🏆 <b>Prestige Vault</b>:"]
    for card in filtered:
        lines.append(f"• <b>{card['name']}</b> | 🔮 {card['power']} | 💥 {card['value']} | 🎴 {card['rarity'].title()}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


QUIZ_QUESTIONS = [
    {"q": "Who is the founder of the bot's bank system?", "a": "Itachi"},
    {"q": "What command lets you draw a spell card?", "a": "/draw"},
    {"q": "Which rarity is higher: Epic or Mythic?", "a": "Mythic"},
    {"q": "What does karma represent?", "a": "Reputation or honor"},
    {"q": "Which command shows your duel rank?", "a": "/duelrank"}
]


async def shinobiquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(QUIZ_QUESTIONS)
    await update.message.reply_text(
        f"🧠 <b>Shinobi Quiz</b>\n{q['q']}\n\nReply with your answer!",
        parse_mode="HTML"
    )


async def karmahall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT uid, karma FROM users ORDER BY karma DESC LIMIT 10").fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("📭 No karma data found.")

    lines = ["🌟 <b>Karma Hall of Fame</b>:"]
    for i, (uid, karma) in enumerate(rows, start=1):
        username = await asyncio.to_thread(get_username, uid)
        lines.append(f"{i}. <b>{username}</b> — ✨ {format_karma(karma)}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def duelbadge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = await asyncio.to_thread(get_username, uid)
    # FIX: get_duel_rank by uid, not username string
    wins, _, _ = get_duel_rank(uid)

    if wins >= 100:
        badge = "👑 Grandmaster Duelist"
    elif wins >= 50:
        badge = "⚔️ Elite Shinobi"
    elif wins >= 25:
        badge = "🥷 Rising Challenger"
    else:
        badge = "🎴 Novice Duelist"

    await update.message.reply_text(
        f"🏅 <b>{username}'s Duel Badge</b>\nTitle: {badge}\nWins: {wins}",
        parse_mode="HTML"
    )


SHOP_ITEMS = [
    {"name": "Mythic Card Pack", "cost": 1000},
    {"name": "Karma Halo", "cost": 750},
    {"name": "Duel Boost", "cost": 500}
]


async def shinobishop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🛍️ <b>Shinobi Prestige Shop</b>:"]
    for item in SHOP_ITEMS:
        lines.append(f"• <b>{item['name']}</b> — 💰 {item['cost']} coins")
    lines.append("Use /byitem &lt;item_name&gt; to purchase.")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def byitem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("🛒 Usage: /byitem <item_name>")

    item_name = " ".join(context.args).strip().lower()
    item = next((i for i in SHOP_ITEMS if i["name"].lower() == item_name), None)

    if not item:
        return await update.message.reply_text(f"❌ Item '{item_name}' not found in Shinobi Shop.")

    coins = await asyncio.to_thread(get_balance, uid)
    if coins < item["cost"]:
        return await update.message.reply_text(f"🚫 You need {item['cost']} coins to buy '{item['name']}'. You have {coins}.")

    await asyncio.to_thread(update_balance, uid, -item["cost"])
    await update.message.reply_text(
        f"✅ Purchased <b>{item['name']}</b> for <b>{item['cost']}</b> coins!\n🎁 Use it wisely, shinobi.",
        parse_mode="HTML"
    )


async def shinobititle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = await asyncio.to_thread(get_username, uid)
    karma = get_karma(uid)
    wins, _, _ = get_duel_rank(uid)  # FIX: pass uid not username

    if karma >= 100 and wins >= 50:
        title = "🌌 Shinobi Legend"
    elif karma >= 50:
        title = "✨ Karma Sage"
    elif wins >= 25:
        title = "⚔️ Duel Master"
    else:
        title = "🎴 Novice Shinobi"

    await update.message.reply_text(
        f"🏷️ <b>{username}'s Shinobi Title</b>\nTitle: {title}\n🌟 Karma: {format_karma(karma)}\n🏆 Wins: {wins}",
        parse_mode="HTML"
    )


KARMA_QUIZ = [
    {"q": "What triggers karma gain in this bot?", "a": "Reply with +1 or 👍"},
    {"q": "What command shows your karma?", "a": "/karma"},
    {"q": "What is karma used for?", "a": "Prestige, reputation, and titles"},
    {"q": "Can you give karma to yourself?", "a": "No"},
    {"q": "What boosts karma besides +1?", "a": "Saying 'itachi is best'"}
]


async def karmaquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(KARMA_QUIZ)
    await update.message.reply_text(
        f"🧠 <b>Karma Quiz</b>\n{q['q']}\n\nReply with your answer!",
        parse_mode="HTML"
    )


async def shinobirank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("""
                SELECT uid, karma + (
                    SELECT COUNT(*) FROM user_cards WHERE user_cards.uid = users.uid
                ) AS prestige_score
                FROM users ORDER BY prestige_score DESC LIMIT 10
            """).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("📭 No prestige data found.")

    lines = ["🧭 <b>Shinobi Prestige Rank</b>:"]
    for i, (uid, score) in enumerate(rows, start=1):
        username = await asyncio.to_thread(get_username, uid)
        lines.append(f"{i}. <b>{username}</b> — 🧠 Prestige: {score}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def shinobibadge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    coins = await asyncio.to_thread(get_balance, uid)
    karma = get_karma(uid)
    cards = get_deck_size(uid)

    badges = []
    if coins >= 10000:
        badges.append("💰 Wealthy Shinobi")
    if karma >= 100:
        badges.append("✨ Karma Master")
    if cards >= 20:
        badges.append("🎴 Card Collector")
    if not badges:
        badges.append("🎴 Novice Shinobi")

    await update.message.reply_text(
        f"🏅 <b>Your Shinobi Badges</b>\n" + "\n".join(badges),
        parse_mode="HTML"
    )


async def shinobichest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    reward_type = random.choice(["coins", "karma", "card"])

    if reward_type == "coins":
        amount = random.randint(100, 500)
        await asyncio.to_thread(update_balance, uid, amount)
        reward_msg = f"💰 You found <b>{amount}</b> coins!"
    elif reward_type == "karma":
        def _sync_op():
            with get_conn() as conn:
                conn.execute("UPDATE users SET karma = karma + 5 WHERE uid=?", (uid,))
                conn.commit()
        await asyncio.to_thread(_sync_op)
        reward_msg = "✨ You gained <b>5 karma</b>!"
    else:
        card = apply_rarity_bonus(get_random_card())
        def _sync_op():
            with get_conn() as conn:
                conn.execute("""
                    INSERT INTO user_cards (uid, file_id, name, power, value, rarity, drawn_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (uid, card.get("file_id"), card.get("name"), card.get("power"),
                      card.get("value"), card.get("rarity"), int(time.time())))
        await asyncio.to_thread(_sync_op)
        reward_msg = f"🎴 You received a <b>{card['rarity'].title()}</b> card: <b>{card['name']}</b>!"

    await update.message.reply_text(f"🎁 <b>Shinobi Chest Opened!</b>\n{reward_msg}", parse_mode="HTML")


async def shinobiarena(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_duelists = get_duel_rank(limit=10)
    if not top_duelists:
        return await update.message.reply_text("📭 No duel data found.")

    lines = ["⚔️ <b>Shinobi Arena</b> — Top Duelists:"]
    for i, (uid, wins) in enumerate(top_duelists, start=1):
        username = await asyncio.to_thread(get_username, uid)
        lines.append(f"{i}. <b>{username}</b> — 🏆 {wins} wins")
    lines.append("\n🔥 Arena is open. Challenge someone with /duel <username>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


SHINOBI_TASKS = [
    "Give karma to 3 users", "Win 2 duels today",
    "Send 100 coins to someone", "Draw 3 cards", "Check your prestige rank"
]
user_tasks = {}


async def shinobitask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_tasks:
        return await update.message.reply_text(f"📜 Your current task:\n<b>{user_tasks[uid]}</b>", parse_mode="HTML")
    task = random.choice(SHINOBI_TASKS)
    user_tasks[uid] = task
    await update.message.reply_text(f"📜 <b>Shinobi Task</b>:\n{task}", parse_mode="HTML")


async def shinobiblessing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    blessings = [
        {"type": "karma", "amount": 5, "msg": "✨ You feel enlightened. +5 karma."},
        {"type": "coins", "amount": 250, "msg": "💰 A hidden monk gifts you 250 coins."},
        {"type": "title", "msg": "🌌 You are now known as 'Blessed Shinobi'."}
    ]
    blessing = random.choice(blessings)

    if blessing["type"] == "karma":
        def _sync_op():
            with get_conn() as conn:
                conn.execute("UPDATE users SET karma = karma + ? WHERE uid=?", (blessing["amount"], uid))
                conn.commit()
        await asyncio.to_thread(_sync_op)
    elif blessing["type"] == "coins":
        await asyncio.to_thread(update_balance, uid, blessing["amount"])

    await update.message.reply_text(f"🙏 <b>Shinobi Blessing</b>\n{blessing['msg']}", parse_mode="HTML")


async def shinobiforge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    inventory = await asyncio.to_thread(get_user_inventory, uid)

    if len(inventory) < 2:
        return await update.message.reply_text("🛠️ You need at least 2 cards to forge.")

    combo = random.sample(inventory, 2)
    new_card = {
        "name": f"{combo[0]['name']} + {combo[1]['name']}",
        "power": f"{combo[0]['power']} & {combo[1]['power']}",
        "value": combo[0]['value'] + combo[1]['value'] + random.randint(50, 150),
        "rarity": "Forged"
    }
    save_card_to_user(uid, new_card)
    await update.message.reply_text(
        f"🔨 <b>Forging Complete!</b>\nYou created a new card:\n<b>{new_card['name']}</b>\n🎴 Rarity: {new_card['rarity']}",
        parse_mode="HTML"
    )


async def shinobitrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("🔁 Usage: /shinobitrade <@username> <amount>")

    target_username = context.args[0].lstrip("@")
    try:
        amount = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("🚫 Amount must be a number.")

    sender_id = update.effective_user.id
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT uid FROM users WHERE username=?", (target_username,)).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text("❌ User not found.")
    receiver_id = row[0]

    if await asyncio.to_thread(get_balance, sender_id) < amount:
        return await update.message.reply_text("🚫 You don't have enough coins.")

    await asyncio.to_thread(update_balance, sender_id, -amount)
    await asyncio.to_thread(update_balance, receiver_id, amount)
    await update.message.reply_text(
        f"✅ You sent <b>{amount}</b> coins to <b>@{target_username}</b>.",
        parse_mode="HTML"
    )


async def shinobialtar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    inventory = await asyncio.to_thread(get_user_inventory, uid)

    if not inventory:
        return await update.message.reply_text("🕯️ You have no cards to sacrifice.")

    card = random.choice(inventory)
    remove_card(uid, card["name"])
    karma_gain = random.randint(3, 10)

    def _sync_op():
        with get_conn() as conn:
            conn.execute("UPDATE users SET karma = karma + ? WHERE uid=?", (karma_gain, uid))
            conn.commit()
    await asyncio.to_thread(_sync_op)

    await update.message.reply_text(
        f"🕯️ <b>Altar Ritual</b>\nYou sacrificed <b>{card['name']}</b>.\n✨ Gained <b>{karma_gain}</b> karma.",
        parse_mode="HTML"
    )


MARKET_ITEMS = [
    {"name": "Epic Card Pack", "cost": 800},
    {"name": "Spell Scroll", "cost": 500},
    {"name": "Karma Boost", "cost": 300}
]


async def shinobimarket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["🏪 <b>Shinobi Market</b>:"]
    for item in MARKET_ITEMS:
        lines.append(f"• <b>{item['name']}</b> — 💰 {item['cost']} coins")
    lines.append("Use /marketbuy &lt;item_name&gt; to purchase.")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def shinobitomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT name, rarity FROM tomb WHERE uid=?", (uid,)).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("⚰️ No fallen cards or sacrifices found.")

    lines = ["⚰️ <b>Shinobi Tomb</b> — Your Sacrifices:"]
    for name, rarity in rows:
        lines.append(f"• <b>{name}</b> — 🎴 {rarity}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def marketbuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("🛒 Usage: /marketbuy <item_name>")

    item_name = " ".join(context.args).strip().lower()
    item = next((i for i in MARKET_ITEMS if i["name"].lower() == item_name), None)

    if not item:
        return await update.message.reply_text(f"❌ Item '{item_name}' not found in Shinobi Market.")

    coins = await asyncio.to_thread(get_balance, uid)
    if coins < item["cost"]:
        return await update.message.reply_text(f"🚫 You need {item['cost']} coins. You have {coins}.")

    await asyncio.to_thread(update_balance, uid, -item["cost"])
    await update.message.reply_text(
        f"✅ Purchased <b>{item['name']}</b> for <b>{item['cost']}</b> coins!",
        parse_mode="HTML"
    )


async def tombstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            rows = conn.execute("SELECT rarity, COUNT(*) FROM tomb GROUP BY rarity").fetchall()
            total = sum(count for _, count in rows)
            return rows, total
    rows, total = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("⚰️ No sacrifices recorded yet.")

    lines = [f"⚰️ <b>Global Tomb Stats</b>\nTotal Sacrifices: {total}"]
    for rarity, count in rows:
        lines.append(f"• 🎴 {rarity.title()}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def shinobifusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    inventory = await asyncio.to_thread(get_user_inventory, uid)

    if len(inventory) < 2:
        return await update.message.reply_text("🧬 You need at least 2 cards to fuse.")

    combo = random.sample(inventory, 2)
    relic = {
        "name": f"{combo[0]['name']} × {combo[1]['name']}",
        "power": f"{combo[0]['power']} + {combo[1]['power']}",
        "value": combo[0]['value'] + combo[1]['value'] + random.randint(100, 300),
        "rarity": "Relic"
    }
    save_card_to_user(uid, relic)
    await update.message.reply_text(
        f"🧬 <b>Fusion Complete!</b>\nCreated Relic: <b>{relic['name']}</b>\n🎴 Rarity: {relic['rarity']}",
        parse_mode="HTML"
    )


async def shinobibattle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    opponent = random.choice(["Shadow Itachi", "Rogue Trader", "Mystic Monk"])
    player_hp = 100
    enemy_hp = 120
    log = [f"⚔️ <b>You vs {opponent}</b>"]

    while player_hp > 0 and enemy_hp > 0:
        hit = random.randint(20, 35)
        enemy_hit = random.randint(15, 30)
        enemy_hp -= hit
        player_hp -= enemy_hit
        log.append(f"🗡️ You hit {hit} | 👊 {opponent} hits {enemy_hit}")

    if player_hp > 0:
        reward = random.randint(300, 600)
        await asyncio.to_thread(update_balance, uid, reward)
        log.append(f"\n🏆 Victory! You earned {reward} coins.")
    else:
        log.append("\n💀 Defeated! Train harder, shinobi.")

    await update.message.reply_text("\n".join(log), parse_mode="HTML")


async def shinobirelic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    relics = get_user_relics(uid)

    if not relics:
        return await update.message.reply_text("🗿 No relics found in your vault.")

    lines = ["🗿 <b>Your Shinobi Relics</b>:"]
    for relic in relics:
        lines.append(f"• <b>{relic['name']}</b> | 🔮 {relic['power']} | 💥 {relic['value']}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def shinobiartefact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    artefacts = get_user_artefacts(uid)

    if not artefacts:
        return await update.message.reply_text("🗝️ No artefacts found in your vault.")

    lines = ["🗝️ <b>Your Shinobi Artefacts</b>:"]
    for artefact in artefacts:
        lines.append(f"• <b>{artefact['name']}</b> — 🧠 {artefact['effect']}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def shinobiblessingvault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT blessing, received_at FROM blessings WHERE uid=?", (uid,)).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("🙌 No blessings recorded yet.")

    lines = ["🙌 <b>Your Blessing Vault</b>:"]
    for blessing, ts in rows:
        date = time.strftime('%Y-%m-%d', time.localtime(ts))
        lines.append(f"• {blessing} — 🕒 {date}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def shinobilegacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    coins = await asyncio.to_thread(get_balance, uid)
    karma = get_karma(uid)
    relics = get_user_relics(uid)
    artefacts = get_user_artefacts(uid)
    score = coins + karma + len(relics) * 100 + len(artefacts) * 150

    lines = [
        "🧘 <b>Your Shinobi Legacy</b>",
        f"💰 Coins: {coins}", f"✨ Karma: {karma}",
        f"🗿 Relics: {len(relics)}", f"🗝️ Artefacts: {len(artefacts)}",
        f"\n🧠 <b>Legacy Score:</b> {score}"
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ── Heart / Proposal ──────────────────────────────────────────────────────────
async def sendheart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use /sendheart.")

    if len(context.args) < 2:
        return await update.message.reply_text("💌 Usage: /sendheart @username <your message>")

    target = context.args[0]
    message = " ".join(context.args[1:])
    if not target.startswith("@"):
        return await update.message.reply_text("💘 First argument must be an @username")

    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT uid FROM users WHERE username=?", (target[1:],)).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text("❌ Target not found in bot database.")

    target_uid = row[0]
    pending_heart[uid] = {"target_uid": target_uid, "target_username": target, "message": message}

    def _sync_op2():
        with get_conn() as conn:
            return conn.execute("SELECT chat_id, title FROM known_groups").fetchall()
    groups = await asyncio.to_thread(_sync_op2)

    if not groups:
        return await update.message.reply_text("📭 No groups found.")

    keyboard = [[InlineKeyboardButton(f"📢 {title}", callback_data=f"heart_gc:{chat_id}")]
                for chat_id, title in groups]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="heart_cancel")])

    await update.message.reply_text(
        f"🩷 Choose a group to deliver your message for {target}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def heart_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if uid not in pending_heart:
        return await query.edit_message_text("⚠️ No pending heart message.")

    data = pending_heart.pop(uid)
    msg = f"💌 <b>Someone left you a note:</b>\n🩷 \"{data['message']}\""

    if query.data.startswith("heart_gc:"):
        group_id = int(query.data.split(":")[1])
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=f"{data['target_username']} —\n{msg}",
                parse_mode="HTML"
            )
            await query.edit_message_text("📢 Heart posted in selected group 💘")
        except Exception:
            await query.edit_message_text("❌ Failed to send message to group.")
    else:
        await query.edit_message_text("❌ Heart canceled.")


async def propose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use /propose.")

    if len(context.args) < 2:
        return await update.message.reply_text("💍 Usage: /propose @username <your message>")

    target = context.args[0]
    message = " ".join(context.args[1:])
    if not target.startswith("@"):
        return await update.message.reply_text("💘 First argument must be an @username")

    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT uid FROM users WHERE username=?", (target[1:],)).fetchone()
    row = await asyncio.to_thread(_sync_op)
    if not row:
        return await update.message.reply_text("❌ Target not found in bot database.")

    target_uid = row[0]
    sender_name = update.effective_user.first_name
    pending_proposal[target_uid] = {"sender_id": uid, "sender_name": sender_name, "message": message}

    keyboard = [[
        InlineKeyboardButton("💖 Accept", callback_data="proposal_accept"),
        InlineKeyboardButton("💔 Reject", callback_data="proposal_reject")
    ]]

    await context.bot.send_message(
        chat_id=target_uid,
        text=(
            f"💌 <b>@{update.effective_user.username}</b> has proposed to you:\n"
            f"🩷 \"{message}\""
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    await update.message.reply_text(f"✅ Proposal sent to {target} 💘")


async def proposal_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if uid not in pending_proposal:
        return await query.edit_message_text("⚠️ No pending proposal.")

    data = pending_proposal.pop(uid)
    sender_name = data["sender_name"]

    if query.data == "proposal_accept":
        await query.edit_message_text(
            f"💖 <b>{query.from_user.first_name}</b> accepted the proposal from <b>{sender_name}</b>!\n"
            f"🌸 May your bond be stronger than any jutsu.",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            f"💔 <b>{query.from_user.first_name}</b> rejected the proposal.\n"
            f"🥲 Better luck next time, shinobi.",
            parse_mode="HTML"
        )


# ── Username / user tracking ──────────────────────────────────────────────────
def get_ref_reward():
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'ref_reward'").fetchone()
        return int(row[0]) if row else 50


def update_username(uid: int, new_username: str):
    if not new_username or new_username.lower() == "none":
        return
    from database import save_username
    current = get_username(uid)
    if current != new_username:
        save_username(uid, new_username)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await send_start_logger(context.bot, user)
    chat = update.effective_chat
    uid = user.id
    username = user.username or user.first_name

    update_username(uid, user.username)
    track_user(uid, username)

    def _sync_op():
        with get_conn() as conn:
            if chat.type in ["group", "supergroup"]:
                conn.execute(
                    "INSERT OR IGNORE INTO groups (group_id, group_name) VALUES (?, ?)",
                    (chat.id, chat.title)
                )
            else:
                conn.execute("INSERT OR IGNORE INTO users (uid, username) VALUES (?, ?)", (uid, username))
            conn.commit()
    await asyncio.to_thread(_sync_op)

    args = context.args
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != uid:
                reward = get_ref_reward()
                def _sync_op2():
                    with get_conn() as conn:
                        conn.execute("INSERT OR IGNORE INTO users (uid, coins) VALUES (?, 0)", (referrer_id,))
                        conn.execute("UPDATE users SET coins = coins + ? WHERE uid = ?", (reward, referrer_id))
                        conn.execute("""
                            CREATE TABLE IF NOT EXISTS referrals (
                                new_uid INTEGER PRIMARY KEY,
                                referrer_uid INTEGER,
                                timestamp INTEGER
                            )
                        """)
                        conn.execute("""
                            INSERT OR IGNORE INTO referrals (new_uid, referrer_uid, timestamp)
                            VALUES (?, ?, ?)
                        """, (uid, referrer_id, int(time.time())))
                        conn.commit()
                await asyncio.to_thread(_sync_op2)
                await update.message.reply_text(
                    f"🌱 You were summoned through a sacred link.\n"
                    f"✨ Your referrer has earned <b>{reward}</b> Echoes of Gratitude.",
                    parse_mode="HTML"
                )
        except ValueError:
            pass

    await update.message.reply_text(
        f"👋 <b>Welcome, {username}</b>!\n\n"
        "You've entered the realm of <b>ITACHI'S BOT</b>—a vault of memory, mischief, and meaning.\n\n"
        "🔍 Use <code>/help</code> to explore, and earn.\n"
        "🧙‍♂️ Every command is a spell. Every asset is a bond. Every ban is a reckoning.\n\n"
        "Let the ritual begin.",
        parse_mode="HTML"
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    coins = await asyncio.to_thread(get_balance, uid) or 0
    await update.message.reply_text(
        f"💰 <b>{username}</b>, your balance is <b>{coins}</b> coins.",
        parse_mode="HTML"
    )


async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.full_name or str(uid)
    await asyncio.to_thread(add_user, uid, username)

    if not await asyncio.to_thread(can_earn, uid):
        return await update.message.reply_text("🕒 Already claimed. Try again in 24 hours.")

    amount = random.randint(100, 300)
    await asyncio.to_thread(update_balance, uid, amount)
    await asyncio.to_thread(update_earn_time, uid)
    new_total = await asyncio.to_thread(get_balance, uid)
    await update.message.reply_text(f"✅ You earned {amount} coins! You now have {new_total} coins.")


async def resolve_name(chat_id: int, uid: int, context) -> str:
    name = await asyncio.to_thread(get_username, uid)
    if name and name.lower() != "none":
        return name
    try:
        member = await context.bot.get_chat_member(chat_id, uid)
        user = member.user
        if user.username:
            return f"@{user.username}"
        elif user.full_name:
            return user.full_name
        else:
            return str(uid)
    except Exception:
        return str(uid)


# ── Party ─────────────────────────────────────────────────────────────────────
async def party(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    now = int(time.time())
    active_window = 60 * 60

    def _sync_op():
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_users (
                    chat_id INTEGER, user_id INTEGER, username TEXT, last_seen INTEGER,
                    PRIMARY KEY (chat_id, user_id)
                )
            """)
            return conn.execute("""
                SELECT user_id, username FROM active_users
                WHERE chat_id = ? AND last_seen >= ?
            """, (chat.id, now - active_window)).fetchall()
    rows = await asyncio.to_thread(_sync_op)

    if not rows:
        return await update.message.reply_text("👻 No active members found in the last hour.")

    mentions = [f'<a href="tg://user?id={uid}">{name}</a>' for uid, name in rows]
    await update.message.reply_text("🎉 Party time!\n" + " ".join(mentions), parse_mode="HTML")


# ── Schedule ──────────────────────────────────────────────────────────────────
async def schedulemsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        return await update.message.reply_text("⛔ Only group admins can schedule messages.")

    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 2:
        return await update.message.reply_text("📝 Usage: /schedulemsg <DD-MM HH:MM> | <your message>")

    try:
        now_dt = datetime.now()
        date_str, time_str = parts[0].split()
        target_time = datetime.strptime(f"{date_str} {time_str}", "%d-%m %H:%M")
        target_time = target_time.replace(year=now_dt.year)
        if target_time < now_dt:
            return await update.message.reply_text("⛔ Time must be in the future.")
    except Exception:
        return await update.message.reply_text("⛔ Invalid format. Use DD-MM HH:MM (24h).")

    scheduled_messages.append({
        "chat_id": chat.id,
        "text": parts[1],
        "timestamp": int(target_time.timestamp())
    })
    await update.message.reply_text(
        f"✅ Message scheduled for {target_time.strftime('%d %b %Y • %H:%M')}.\nWill send: {parts[1]}"
    )


async def viewschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        return await update.message.reply_text("⛔ Only group admins can view scheduled messages.")

    upcoming = [msg for msg in scheduled_messages if msg["chat_id"] == chat.id]
    if not upcoming:
        return await update.message.reply_text("📭 No scheduled messages for this group.")

    lines = ["📅 <b>Scheduled Messages</b>:"]
    for msg in upcoming:
        time_str = datetime.fromtimestamp(msg["timestamp"]).strftime("%d %b %Y • %H:%M")
        lines.append(f"🕰️ <b>{time_str}</b>\n{msg['text']}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def clearschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await context.bot.get_chat_member(chat.id, user.id)

    if member.status not in ("administrator", "creator"):
        return await update.message.reply_text("⛔ Only group admins can clear scheduled messages.")

    before = len(scheduled_messages)
    scheduled_messages[:] = [msg for msg in scheduled_messages if msg["chat_id"] != chat.id]
    removed = before - len(scheduled_messages)

    if removed == 0:
        return await update.message.reply_text("📭 No scheduled messages found for this group.")
    await update.message.reply_text(
        f"🧹 Cleared <b>{removed}</b> scheduled message(s) for this group.",
        parse_mode="HTML"
    )


# ── Activity tracker ──────────────────────────────────────────────────────────
async def activity_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        uid = update.message.from_user.id
        name = update.message.from_user.username or update.message.from_user.full_name
        now = int(time.time())
        def _sync_op():
            with get_conn() as conn:
                conn.execute("INSERT OR IGNORE INTO users (uid, username) VALUES (?, ?)", (uid, name))
                conn.execute("UPDATE users SET last_active=? WHERE uid=?", (now, uid))
                conn.commit()
        await asyncio.to_thread(_sync_op)


# ── Broadcast ─────────────────────────────────────────────────────────────────
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use /broadcast.")

    if update.message.reply_to_message:
        msg = update.message.reply_to_message.text
    else:
        msg = " ".join(context.args).strip()
        if not msg:
            return await update.message.reply_text("📝 Your message can't be empty.")

    final_msg = f"<b>📢 Broadcast</b>\n\n{msg}\n\n<i>— Reverse System</i>"
    user_ids = get_all_user_ids()
    group_ids = get_all_group_ids()
    targets = user_ids + group_ids
    success = fail = 0

    for target in targets:
        try:
            await context.bot.send_message(
                chat_id=target, text=final_msg,
                parse_mode="HTML", disable_web_page_preview=True
            )
            success += 1
        except Exception as e:
            print(f"⚠️ Failed to send to {target}: {e}")
            fail += 1

    return await update.message.reply_text(
        f"✅ Broadcast completed.\n📩 Sent: {success}\n❌ Failed: {fail}"
    )


async def broadcaststatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            total_groups = conn.execute("SELECT COUNT(*) FROM known_groups").fetchone()[0]
            conn.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_failures (
                    chat_id INTEGER PRIMARY KEY, title TEXT, last_failed INTEGER
                )
            """)
            failed_groups = conn.execute("SELECT chat_id, title, last_failed FROM broadcast_failures").fetchall()
            return total_groups, failed_groups
    total_groups, failed_groups = await asyncio.to_thread(_sync_op)

    lines = ["📡 <b>Broadcast Status</b>",
             f"✅ Total Groups: <b>{total_groups}</b>",
             f"❌ Failed Deliveries: <b>{len(failed_groups)}</b>\n"]

    for chat_id, title, last_failed in failed_groups:
        timestamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(last_failed))
        lines.append(f"• {title} — <code>{chat_id}</code> (Last failed: {timestamp})")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def broadcast_to_all(context, chat_ids, message):
    sent = failed = 0
    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed to send to {chat_id}: {e}")
            def _sync_op():
                with get_conn() as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS broadcast_failures (
                            chat_id INTEGER PRIMARY KEY, title TEXT, last_failed INTEGER
                        )
                    """)
                    conn.execute("""
                        INSERT OR REPLACE INTO broadcast_failures (chat_id, title, last_failed)
                        VALUES (?, ?, ?)
                    """, (chat_id, "Unknown", int(time.time())))
            await asyncio.to_thread(_sync_op)
    return sent, failed


async def mentionall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return await update.message.reply_text("🤔 This only works in a group.")

    if not context.args:
        return await update.message.reply_text("🛑 Usage: /mentionall <your message here>")

    broadcast_text = " ".join(context.args)
    all_uids = get_all_user_ids()
    if not all_uids:
        return await update.message.reply_text("👥 No users to mention.")

    mentions = []
    for uid in all_uids:
        name = await resolve_name(chat.id, uid, context)
        mentions.append(f'<a href="tg://user?id={uid}">{name}</a>')

    text = f"{broadcast_text}\n\n" + " ".join(mentions)
    await update.message.reply_text(text, parse_mode="HTML")


# ── Karma ─────────────────────────────────────────────────────────────────────
async def karma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    k = get_karma(uid)
    await update.message.reply_text(f"🌟 Your karma: {format_karma(k)}")


async def duelrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = get_duel_rank(limit=10)
    if not top_users:
        return await update.message.reply_text("📭 No leaderboard data.")

    lines = ["🏅 <b>Duel Leaderboard</b>:"]
    for i, (uid, coins) in enumerate(top_users, start=1):
        lines.append(f"{i}. <b>{await asyncio.to_thread(get_username, uid)}</b> — {coins} coins")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def request_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester = update.effective_user

    if not context.args or len(context.args) < 1:
        return await update.message.reply_text("📦 Usage: /request <amount> [@username or UID] or reply to a message.")

    try:
        amount = int(context.args[0])
        if amount <= 0:
            return await update.message.reply_text("🚫 Amount must be positive.")
    except ValueError:
        return await update.message.reply_text("🚫 Amount must be a number.")

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
    elif len(context.args) >= 2:
        target = context.args[1]
        target_id = None
        if target.startswith("@"):
            username = target[1:]
            def _sync_op():
                with get_conn() as conn:
                    return conn.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
            result = await asyncio.to_thread(_sync_op)
            if result:
                target_id = result[0]
        else:
            try:
                target_id = int(target)
            except ValueError:
                return await update.message.reply_text("🚫 Invalid UID.")
    else:
        return await update.message.reply_text("🧑 Specify who you're requesting from by replying or tagging.")

    target_name = await asyncio.to_thread(get_username, target_id)
    await update.message.reply_text(
        f"📨 <b>{requester.full_name}</b> is requesting <b>{amount}</b> coins from <b>{target_name}</b>!",
        parse_mode="HTML"
    )


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user
    sender_id = sender.id

    if not context.args or len(context.args) < 1:
        return await update.message.reply_text("📦 Usage: /send <amount> [@username or UID] or reply to a message.")

    try:
        amount = int(context.args[0])
        if amount <= 0:
            return await update.message.reply_text("🚫 Amount must be positive.")
    except ValueError:
        return await update.message.reply_text("🚫 Amount must be a number.")

    receiver_id = None
    receiver_name = "Unknown"

    if update.message.reply_to_message:
        receiver = update.message.reply_to_message.from_user
        receiver_id = receiver.id
        receiver_name = receiver.full_name
    elif len(context.args) >= 2:
        target = context.args[1]
        if target.startswith("@"):
            username = target[1:]
            def _sync_op():
                with get_conn() as conn:
                    return conn.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
            result = await asyncio.to_thread(_sync_op)
            if result:
                receiver_id = result[0]
                receiver_name = await asyncio.to_thread(get_username, receiver_id)
        else:
            try:
                receiver_id = int(target)
                receiver_name = await asyncio.to_thread(get_username, receiver_id)
            except ValueError:
                return await update.message.reply_text("🚫 Invalid UID.")
    else:
        return await update.message.reply_text("🧑 Specify a recipient by replying or using @username/UID.")

    if not receiver_id:
        return await update.message.reply_text("❌ Recipient not found.")

    sender_balance = await asyncio.to_thread(get_balance, sender_id)
    if sender_balance < amount:
        return await update.message.reply_text("🚫 Not enough coins to send.")

    await asyncio.to_thread(update_balance, sender_id, -amount)
    await asyncio.to_thread(update_balance, receiver_id, amount)
    await asyncio.to_thread(log_transfer, sender_id, receiver_id, amount)
    await update.message.reply_text(
        f"✅ <b>{sender.full_name}</b> sent <b>{amount}</b> coins to <b>{receiver_name}</b>!",
        parse_mode="HTML"
    )


async def dumpusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Admins only.")

    def _sync_op():
        with get_conn() as conn:
            return conn.execute("SELECT id, username, coins FROM users").fetchall()
    rows = await asyncio.to_thread(_sync_op)

    lines = ["🗄️ <b>DB Users</b>:"]
    for uid, usr, coins in rows:
        lines.append(f"{uid} → '{usr}' — {coins} coins")

    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 4096:
            await update.message.reply_text(chunk, parse_mode="HTML")
            chunk = ""
        chunk += line + "\n"
    if chunk:
        await update.message.reply_text(chunk, parse_mode="HTML")


async def adjustcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    if len(context.args) < 2:
        return await update.message.reply_text("🧾 Usage: /adjustcoins <@username|user_id> <amount>")

    target_raw = context.args[0]
    try:
        amount = int(context.args[1])
        if amount < 0:
            return await update.message.reply_text("🚫 Amount must be non-negative.")
    except ValueError:
        return await update.message.reply_text("🚫 Amount must be a valid integer.")

    if target_raw.startswith("@"):
        username = target_raw[1:]
        target_uid = get_user_by_username(username)
        if not target_uid:
            return await update.message.reply_text(f"❌ User '@{username}' not found.")
    else:
        try:
            target_uid = int(target_raw)
        except ValueError:
            return await update.message.reply_text("🚫 First argument must be a @username or a numeric user ID.")
        if await asyncio.to_thread(get_balance, target_uid) is None:
            return await update.message.reply_text(f"❌ No user with ID {target_uid} found.")

    set_balance(target_uid, amount)
    new_bal = await asyncio.to_thread(get_balance, target_uid)

    # FIX: log the adjustment
    adjust_log.append({
        "admin_id": admin_id,
        "admin_name": update.effective_user.full_name or str(admin_id),
        "target_name": await asyncio.to_thread(get_username, target_uid) or str(target_uid),
        "amount": amount,
        "timestamp": int(time.time())
    })

    tg_username = await asyncio.to_thread(get_username, target_uid)
    if tg_username and tg_username.lower() != "none":
        display = f"@{tg_username}"
    else:
        try:
            user = await context.bot.get_chat(target_uid)
            display = user.full_name or str(target_uid)
        except Exception:
            display = str(target_uid)

    await update.message.reply_text(
        f"✅ {display}'s balance has been set to <b>{new_bal:,}</b> coins.",
        parse_mode="HTML"
    )


async def adjusthistory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can view adjustment history.")

    if not adjust_log:
        return await update.message.reply_text("📭 No adjustments have been made yet.")

    now = int(time.time())
    three_days_ago = now - (3 * 24 * 60 * 60)
    recent_entries = [e for e in adjust_log if e["timestamp"] >= three_days_ago]
    old_entries = [e for e in adjust_log if e["timestamp"] < three_days_ago]

    entries_to_show = recent_entries if len(recent_entries) > 10 else \
        recent_entries + old_entries[-(10 - len(recent_entries)):]

    lines = []
    for entry in reversed(entries_to_show):
        ts = time.strftime("%d %b %Y %H:%M", time.localtime(entry["timestamp"]))
        lines.append(
            f"🕒 <b>{ts}</b>\n"
            f"👤 <a href='tg://user?id={entry['admin_id']}'>{entry['admin_name']}</a> "
            f"set <b>{entry['target_name']}</b>'s balance to <b>{entry['amount']:,}</b> coins.\n"
        )

    await update.message.reply_text(
        "📜 <b>Adjustment History:</b>\n\n" + "\n".join(lines),
        parse_mode="HTML"
    )


async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    uids = await asyncio.to_thread(get_all_user_ids)
    if not uids:
        return await update.message.reply_text("📭 No users in the database.")

    def _sync_op():
        return [(uid, get_balance(uid)) for uid in uids]
    board = sorted(await asyncio.to_thread(_sync_op), key=lambda x: x[1], reverse=True)
    header = "📜 <b>All Bot Users & Balances</b>:\n"
    lines = []

    for rank, (uid, bal) in enumerate(board, start=1):
        bal_str = f"{bal:,}"
        username = await asyncio.to_thread(get_username, uid)
        if username and username.lower() != "none":
            display = f"@{username}"
        else:
            try:
                user = await context.bot.get_chat(uid)
                name = user.full_name or ""
                display = f"{name} ({uid})" if name else str(uid)
            except Exception:
                display = str(uid)
        lines.append(f"{rank}. <b>{display}</b> — 💰 {bal_str} coins")

    chunk = header
    for line in lines:
        if len(chunk) + len(line) + 1 > 4096:
            await update.message.reply_text(chunk, parse_mode="HTML")
            chunk = ""
        chunk += line + "\n"
    if chunk:
        await update.message.reply_text(chunk, parse_mode="HTML")


async def checkbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    if not context.args:
        return await update.message.reply_text("🧾 Usage: /checkbalance <@username or UID>")

    target = context.args[0]
    uid = None

    if target.startswith("@"):
        username = target[1:]
        def _sync_op():
            with get_conn() as conn:
                return conn.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
        result = await asyncio.to_thread(_sync_op)
        if result:
            uid = result[0]
    else:
        try:
            uid = int(target)
        except ValueError:
            return await update.message.reply_text("🚫 Invalid UID.")

    if not uid:
        return await update.message.reply_text("❌ User not found.")

    coins = await asyncio.to_thread(get_balance, uid)
    karma_val = await asyncio.to_thread(get_karma, uid)
    username = await asyncio.to_thread(get_username, uid)
    await update.message.reply_text(
        f"🧾 <b>{username}</b>\n💰 Coins: {coins}\n✨ Karma: {format_karma(karma_val)}",
        parse_mode="HTML"
    )


async def resetearn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    if len(context.args) != 1:
        return await update.message.reply_text("🧾 Usage: /resetearn <@username|user_id>")

    target_raw = context.args[0]
    if target_raw.startswith("@"):
        name = target_raw[1:]
        uid = await asyncio.to_thread(get_user_by_username, name)
        if not uid:
            return await update.message.reply_text(f"❌ User '@{name}' not found.")
    else:
        try:
            uid = int(target_raw)
        except ValueError:
            return await update.message.reply_text("🚫 First argument must be @username or numeric user ID.")

    def _sync_op():
        with get_conn() as conn:
            conn.execute("DELETE FROM earn_times WHERE uid = ?", (uid,))
            conn.commit()
    await asyncio.to_thread(_sync_op)

    last_itachi_reward.pop(uid, None)
    await update.message.reply_text(
        f"✅ Cleared daily-earn cooldown for <b>{target_raw}</b>. They can now use /earn again.",
        parse_mode="HTML"
    )


async def transferlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can view the transfer log.")

    logs = await asyncio.to_thread(get_transfer_logs, limit=10)
    if not logs:
        return await update.message.reply_text("📭 No transfers found.")

    lines = ["📜 <b>Transfer Log</b>:"]
    for sender, receiver, amount, ts in logs:
        sender_name = await asyncio.to_thread(get_username, sender)
        receiver_name = await asyncio.to_thread(get_username, receiver)
        lines.append(f"💸 {sender_name} → {receiver_name}: {amount} coins")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = update.effective_user
    sender_id = sender.id

    if not context.args or len(context.args) < 1:
        return await update.message.reply_text("📦 Usage: /give <amount> [@username or UID] or reply to a message.")

    try:
        amount = int(context.args[0])
        if amount <= 0:
            return await update.message.reply_text("🚫 Amount must be positive.")
    except ValueError:
        return await update.message.reply_text("🚫 Amount must be a number.")

    receiver_id = None
    if update.message.reply_to_message:
        receiver = update.message.reply_to_message.from_user
        receiver_id = receiver.id
    elif len(context.args) >= 2:
        target = context.args[1]
        if target.startswith("@"):
            username = target[1:]
            def _sync_op():
                with get_conn() as conn:
                    return conn.execute("SELECT uid FROM users WHERE username=?", (username,)).fetchone()
            result = await asyncio.to_thread(_sync_op)
            if result:
                receiver_id = result[0]
        else:
            try:
                receiver_id = int(target)
            except ValueError:
                return await update.message.reply_text("🚫 Invalid UID.")
    else:
        return await update.message.reply_text("🧑 Specify a recipient by replying or using @username/UID.")

    if not receiver_id:
        return await update.message.reply_text("❌ Recipient not found.")

    sender_balance = await asyncio.to_thread(get_balance, sender_id)
    if sender_balance < amount:
        return await update.message.reply_text("🚫 Not enough coins to give.")

    await asyncio.to_thread(update_balance, sender_id, -amount)
    await asyncio.to_thread(update_balance, receiver_id, amount)
    await asyncio.to_thread(log_transfer, sender_id, receiver_id, amount)
    receiver_name = await asyncio.to_thread(get_username, receiver_id)
    await update.message.reply_text(
        f"🎁 <b>{sender.full_name}</b> gave <b>{amount}</b> coins to <b>{receiver_name}</b>!",
        parse_mode="HTML"
    )


STEAL_COOLDOWN = 7200
MAX_STEAL = 25000
last_steal_time = {}


async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    thief = update.effective_user
    thief_id = thief.id
    now = int(time.time())

    if thief_id in last_steal_time and now - last_steal_time[thief_id] < STEAL_COOLDOWN:
        wait = STEAL_COOLDOWN - (now - last_steal_time[thief_id])
        return await update.message.reply_text(
            f"🕒 Chill out! You can steal again in {wait // 120}m {wait % 60}s."
        )

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        target_id = target.id
        target_name = target.username or target.first_name
    elif context.args and context.args[0].startswith("@"):
        uname = context.args[0][1:]
        def _sync_op():
            with get_conn() as conn:
                return conn.execute("SELECT uid FROM users WHERE username=?", (uname,)).fetchone()
        row = await asyncio.to_thread(_sync_op)
        if not row:
            return await update.message.reply_text(f"❌ No user @{uname} found.")
        target_id = row[0]
        target_name = uname
    else:
        return await update.message.reply_text(
            "📦 Usage:\n • Reply: `/steal` (to someone's message)\n • Tag:  `/steal @username`",
            parse_mode="Markdown"
        )

    if target_id == thief_id:
        return await update.message.reply_text("🫣 You can't steal from yourself.")

    steal_amt = random.randint(0, MAX_STEAL)
    victim_balance = await asyncio.to_thread(get_balance, target_id)
    actual = min(steal_amt, victim_balance)

    await asyncio.to_thread(update_balance, target_id, -actual)
    await asyncio.to_thread(update_balance, thief_id, actual)
    last_steal_time[thief_id] = now
    await update.message.reply_text(f"💰 You stole {actual} coins from {target_name}!")
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"😠 {thief.username or thief.first_name} stole {actual} coins from you!"
        )
    except Exception:
        pass


async def reverse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await asyncio.to_thread(get_balance, update.effective_user.id) < 25:
        return await update.message.reply_text("🚫 You need 25 coins to reverse.")
    target = context.args[0] if context.args else "@someone"
    await asyncio.to_thread(update_balance, update.effective_user.id, -25)
    await update.message.reply_text(f"🔁 You reversed {target}'s move!")


async def checkcards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _sync_op():
        with get_conn() as conn:
            user_cards = conn.execute("SELECT file_id FROM user_cards").fetchall()
            deck_cards = conn.execute("SELECT file_id FROM deck").fetchall()
            return user_cards, deck_cards
    user_cards, deck_cards = await asyncio.to_thread(_sync_op)

    user_ids = {row[0] for row in user_cards}
    deck_ids = {row[0] for row in deck_cards}
    missing = user_ids - deck_ids

    if not missing:
        return await update.message.reply_text("✅ All drawn cards exist in the deck.")

    lines = ["⚠️ Missing cards in deck:"]
    for fid in missing:
        lines.append(f"• {fid}")
    await update.message.reply_text("\n".join(lines))


async def cardlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = await asyncio.to_thread(list_all_cards)
    if not cards:
        return await update.message.reply_text("📭 No cards available in the bot.")

    lines = ["📜 <b>Available Cards</b>:"]
    for i, card in enumerate(cards, start=1):
        lines.append(
            f"{i}. <b>{card.get('name', 'Unknown')}</b> | 🔮 {card.get('power', 'Unknown')} "
            f"| 💥 {card.get('value', 0)} | 🎴 {card.get('rarity', 'Common')}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# FIX: /top now works in private too (falls back to global leaderboard)
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type in ("group", "supergroup"):
        from telegram_utils import get_group_user_ids
        group_user_ids = await get_group_user_ids(context, chat.id)
        def _sync_op():
            with get_conn() as conn:
                return conn.execute("SELECT id FROM users").fetchall()
        rows = await asyncio.to_thread(_sync_op)
        all_uids = [r[0] for r in rows]
        target_uids = [uid for uid in all_uids if uid in group_user_ids]
        title_text = update.effective_chat.title
    else:
        # Private chat: show global top
        target_uids = await asyncio.to_thread(get_all_user_ids)
        title_text = "Global"

    if not target_uids:
        return await update.message.reply_text("📭 No users found.")

    def _sync_op2():
        return [(uid, get_balance(uid)) for uid in target_uids]
    board = sorted(await asyncio.to_thread(_sync_op2), key=lambda x: x[1], reverse=True)[:10]

    if not any(balance for _, balance in board):
        return await update.message.reply_text("📭 No one has coins yet.")

    lines = [f"🏆 <b>Top Coin Holders — {title_text}</b>:"]
    for rank, (uid, bal) in enumerate(board, start=1):
        bal_str = f"{bal:,}"
        username = await asyncio.to_thread(get_username, uid)
        if username and username.lower() != "none":
            display = f"@{username}"
        else:
            try:
                user = await context.bot.get_chat(uid)
                full = user.full_name or ""
                display = f"{full} ({uid})" if full else str(uid)
            except Exception:
                display = str(uid)
        lines.append(f"{rank}. <b>{display}</b> — 💰 {bal_str} coins")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def btop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uids = await asyncio.to_thread(get_all_user_ids)
    if not uids:
        return await update.message.reply_text("📭 No users found.")

    def _sync_op():
        return [(uid, get_balance(uid)) for uid in uids]
    board = sorted(await asyncio.to_thread(_sync_op), key=lambda x: x[1], reverse=True)[:10]

    if not any(balance for _, balance in board):
        return await update.message.reply_text("📭 No one has coins yet.")

    lines = ["🌐 <b>Global Top Coin Holders</b>:"]
    for rank, (uid, bal) in enumerate(board, start=1):
        bal_str = f"{bal:,}"
        username = await asyncio.to_thread(get_username, uid)
        if username and username.lower() != "none":
            display = f"@{username}"
        else:
            try:
                user = await context.bot.get_chat(uid)
                full = user.full_name or ""
                display = f"{full} ({uid})" if full else str(uid)
            except Exception:
                display = str(uid)
        lines.append(f"{rank}. <b>{display}</b> — 💰 {bal_str} coins")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cardvault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can access the card vault.")

    cards = await asyncio.to_thread(list_all_cards)
    if not cards:
        return await update.message.reply_text("📭 No cards found.")

    for card in cards:
        name = card.get("name", "Unknown")
        power = card.get("power", "Unknown")
        value = card.get("value", 0)
        rarity = card.get("rarity", "Common")
        text = f"🃏 <b>{name}</b>\n🔮 Power: {power}\n💥 Value: {value}\n🎴 Rarity: {rarity}"
        keyboard = [[InlineKeyboardButton("🗑️ Delete", callback_data=f"removecard:{name}")]]
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def deletecard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    if uid not in ADMIN_IDS:
        return await query.edit_message_text("⛔ Only admins can delete cards.")

    if query.data.startswith("removecard:"):
        card_name = query.data.split(":", 1)[1]
        success = await asyncio.to_thread(remove_card_by_name, card_name)
        if success:
            await query.edit_message_text(f"✅ Card '<b>{card_name}</b>' removed from the bot.", parse_mode="HTML")
        else:
            await query.edit_message_text(f"⚠️ Failed to remove card '<b>{card_name}</b>'. Not found.", parse_mode="HTML")


async def deletecardbyindex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can delete cards.")

    if not context.args:
        return await update.message.reply_text("🗑️ Usage: /deletecardbyindex <index>")

    try:
        index = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("🚫 Index must be a valid number.")

    cards = await asyncio.to_thread(list_all_cards)
    if not cards:
        return await update.message.reply_text("📭 No cards found in the database.")

    if index < 0 or index >= len(cards):
        return await update.message.reply_text("⚠️ Invalid index. Use /viewcards to see valid indexes.")

    card = cards[index]
    name = card.get("name", "Unknown")
    success = await asyncio.to_thread(remove_card_by_name, name)
    if success:
        await update.message.reply_text(f"✅ Card <b>{name}</b> deleted successfully.", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Failed to delete the card.")


async def viewcards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can view all cards.")

    cards = await asyncio.to_thread(list_all_cards)
    if not cards:
        return await update.message.reply_text("📭 No cards found in the database.")

    message = "🃏 <b>Card Vault Overview</b>\n"
    for i, card in enumerate(cards, start=1):
        message += (
            f"{i}. <b>{card.get('name', 'Unknown')}</b> | 🔮 {card.get('power', 'Unknown')} "
            f"| 💥 {card.get('value', 0)} | 🎴 {card.get('rarity', 'Common')}\n"
        )
    message += "\n🗑️ Use /deletecardbyindex <index> to delete a card."
    await update.message.reply_text(message, parse_mode="HTML")


async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    if len(context.args) != 1:
        return await update.message.reply_text("🗑️ Usage: /removeuser <@username|user_id>")

    target = context.args[0]
    if target.startswith("@"):
        name = target[1:]
        uid = await asyncio.to_thread(get_user_by_username, name)
        if not uid:
            return await update.message.reply_text(f"❌ User '@{name}' not found.")
        ok = await asyncio.to_thread(remove_user_by_id, uid)
    else:
        try:
            uid = int(target)
        except ValueError:
            return await update.message.reply_text("🚫 Must be @username or numeric ID.")
        ok = await asyncio.to_thread(remove_user_by_id, uid)

    if ok:
        await update.message.reply_text(f"✅ User <b>{target}</b> has been removed from the bot.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ No record found for <b>{target}</b>.", parse_mode="HTML")


async def purgecardbyindex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can purge cards.")

    if not context.args:
        return await update.message.reply_text("🛑 Usage: /purgecardbyindex <index>")

    try:
        idx = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("🚫 Index must be a number.")

    cards = await asyncio.to_thread(list_all_cards)
    if idx < 1 or idx > len(cards):
        return await update.message.reply_text("⚠️ Invalid index. Use /admincards to see valid indexes.")

    card = cards[idx - 1]
    name = card.get("name", "Untitled")

    def _sync_op():
        with get_conn() as conn:
            for file_id, raw in conn.execute("SELECT file_id, json FROM deck"):
                try:
                    data = json.loads(raw)
                    if data.get("name", "").lower() == name.lower():
                        conn.execute("DELETE FROM deck WHERE file_id = ?", (file_id,))
                except Exception:
                    continue
            conn.execute("DELETE FROM user_cards WHERE LOWER(name) = ?", (name.lower(),))
            conn.execute("DELETE FROM tomb WHERE LOWER(name) = ?", (name.lower(),))
            conn.commit()
    await asyncio.to_thread(_sync_op)

    await update.message.reply_text(f"🧨 Card <b>{name}</b> purged from all bot tables.", parse_mode="HTML")


async def deletebyname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    if not context.args:
        return await update.message.reply_text("🗑️ Usage: /deletebyname <card_name>")

    card_name = " ".join(context.args).strip()
    success = await asyncio.to_thread(remove_card_by_name, card_name)

    if success:
        await update.message.reply_text(f"✅ Card '<b>{card_name}</b>' deleted from the database.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"⚠️ Card '<b>{card_name}</b>' not found or deletion failed.", parse_mode="HTML")


async def getcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can use this command.")

    try:
        amount = int(context.args[0]) if context.args else 100000
        if amount <= 0:
            return await update.message.reply_text("🚫 Amount must be positive.")
    except (ValueError, IndexError):
        return await update.message.reply_text("🚫 Usage: /getcoins <amount>")

    await asyncio.to_thread(update_balance, uid, amount)
    await update.message.reply_text(
        f"✅ You received <b>{amount}</b> coins, shinobi banker!",
        parse_mode="HTML"
    )


setup_tax_bank()
TAX_RATE = 0.10


async def sellcard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("📦 Usage: /sellcard <card name>")

    name = " ".join(context.args).lower()
    def _sync_op():
        with get_conn() as conn:
            row = conn.execute(
                "SELECT name, value FROM user_cards WHERE uid=? AND LOWER(name)=?", (uid, name)
            ).fetchone()
            if not row:
                return None
            card_name, value = row
            conn.execute("DELETE FROM user_cards WHERE uid=? AND LOWER(name)=?", (uid, name))
            conn.commit()
            return (card_name, value)
    result = await asyncio.to_thread(_sync_op)
    if result is None:
        return await update.message.reply_text(f"🔍 No card named '{name}' found.")
    card_name, value = result

    tax = int(value * TAX_RATE)
    payout = value - tax
    await asyncio.to_thread(update_balance, uid, payout)
    await asyncio.to_thread(deposit_tax, tax)

    await update.message.reply_text(
        f"✅ Sold <b>{card_name}</b>\n💰 Gross: {value} coins\n💸 Tax: {tax} coins\n🏦 You receive: {payout}",
        parse_mode="HTML"
    )


def distribute_tax_rewards():
    with get_conn() as conn:
        total = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()[0] or 0
        if total == 0:
            return "🚫 Tax pool is empty."
        top5 = conn.execute("SELECT uid FROM balance ORDER BY coins DESC LIMIT 5").fetchall()
        if not top5:
            return "🚫 No players to reward."
        share = total // len(top5)
        for (uid,) in top5:
            update_balance(uid, share)
        conn.execute("DELETE FROM tax_bank")
        conn.commit()
        return f"🏆 Distributed {total} coins: {share} each to top 5."


async def distribute_tax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("🚫 You're not authorized.")

    try:
        amount = int(context.args[0])
        top_count = int(context.args[1])
        if amount <= 0 or top_count <= 0:
            return await update.message.reply_text("⚠️ Enter valid amount and top count.")

        def _sync_op():
            with get_conn() as conn:
                tax_pool = conn.execute("SELECT coins FROM banktax WHERE id = 1").fetchone()
                if not tax_pool or tax_pool[0] < amount:
                    return ("no_funds", tax_pool[0] if tax_pool else 0)

                top_users = conn.execute(
                    "SELECT id FROM bank WHERE coins > 0 ORDER BY coins DESC LIMIT ?", (top_count,)
                ).fetchall()

                if not top_users:
                    return ("no_users",)

                share = amount // len(top_users)
                for (uid,) in top_users:
                    conn.execute("UPDATE bank SET coins = coins + ? WHERE id = ?", (share, uid))
                conn.execute("UPDATE banktax SET coins = coins - ? WHERE id = 1", (amount,))
                conn.commit()
                return ("ok", len(top_users), share)
        result = await asyncio.to_thread(_sync_op)

        if result[0] == "no_funds":
            return await update.message.reply_text(f"❌ Not enough tax in pool. Available: {result[1]}")
        elif result[0] == "no_users":
            return await update.message.reply_text("⚠️ No eligible users to receive tax.")

        await update.message.reply_text(
            f"✅ Distributed {amount} coins to top {result[1]} users.\nEach received {result[2]} coins."
        )
    except Exception:
        await update.message.reply_text("⚠️ Usage:\n/distribute_tax <amount> <top_count>")


async def taxpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can view the tax pool.")
    amount = await asyncio.to_thread(get_tax_pool)
    await update.message.reply_text(f"🏦 <b>Current Tax Pool:</b> ₹{amount} coins", parse_mode="HTML")


async def debugvault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = await asyncio.to_thread(list_all_cards)
    total = len(cards)
    lines = [f"📦 Found {total} cards in vault."]
    for c in cards:
        lines.append(f"• {c.get('name')} | 🎴 {c.get('rarity')} | 💥 {c.get('value')}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def adminpanel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Only admins can access the panel.")

    buttons = [
        [InlineKeyboardButton("💰 Adjust Coins", callback_data="adjustcoins")],
        [InlineKeyboardButton("🔍 Check Balance", callback_data="checkbalance")],
        [InlineKeyboardButton("📜 Transfer Log", callback_data="transferlog")],
        [InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🃏 Manage Cards", callback_data="managecards")],
    ]
    await update.message.reply_text("🛠️ Admin Control Panel:", reply_markup=InlineKeyboardMarkup(buttons))


async def getfileid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text("📸 Reply to a photo to get its file ID.")
    photo = update.message.reply_to_message.photo[-1]
    await update.message.reply_text(f"🆔 File ID: <code>{photo.file_id}</code>", parse_mode="HTML")


async def panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if uid not in ADMIN_IDS:
        return await query.edit_message_text("⛔ Admin access only.")

    data = query.data
    if data == "adjustcoins":
        return await query.edit_message_text("💰 Use /adjustcoins <@username or UID> <amount>")
    elif data == "checkbalance":
        return await query.edit_message_text("🔍 Use /checkbalance <@username or UID>")
    elif data == "transferlog":
        logs = await asyncio.to_thread(get_transfer_logs, limit=10)
        if not logs:
            return await query.edit_message_text("📭 No transfers found.")
        lines = ["📜 <b>Transfer Log</b>:"]
        for sender, receiver, amount, ts in logs:
            s_name = await asyncio.to_thread(get_username, sender)
            r_name = await asyncio.to_thread(get_username, receiver)
            lines.append(f"💸 {s_name} → {r_name}: {amount} coins")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")
    elif data == "leaderboard":
        top_users = await asyncio.to_thread(get_duel_rank, limit=10)
        if not top_users:
            return await query.edit_message_text("📭 No leaderboard data.")
        lines = ["🏅 <b>Leaderboard</b>:"]
        for i, (uid, coins) in enumerate(top_users, start=1):
            uname = await asyncio.to_thread(get_username, uid)
            lines.append(f"{i}. <b>{uname}</b> — {coins} coins")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")
    elif data == "managecards":
        cards = await asyncio.to_thread(list_all_cards)
        if not cards:
            return await query.edit_message_text("📭 No cards found.")
        lines = ["🃏 <b>Card Vault</b>:"]
        for i, card in enumerate(cards, start=1):
            lines.append(f"{i}. <b>{card['name']}</b> | {card['power']} | {card['value']} | {card['rarity']}")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")


KARMA_TRIGGERS = ["+1", "++", "+karma", "👍", "👍🏼", "✨"]


async def karma_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.reply_to_message:
        return

    text = msg.text.strip().lower()
    giver = msg.from_user
    receiver = msg.reply_to_message.from_user

    if giver.id == receiver.id:
        return await msg.reply_text("🫣 You can't karma boost yourself.")

    await asyncio.to_thread(track_user, giver.id, giver.username)
    await asyncio.to_thread(track_user, receiver.id, receiver.username)

    karma_boost = 0
    if any(trigger in text for trigger in KARMA_TRIGGERS):
        karma_boost = 1
    elif "itachi is best" in text:
        karma_boost = 5

    if karma_boost == 0:
        return

    def _sync_op():
        with get_conn() as conn:
            conn.execute("UPDATE users SET karma = karma + ? WHERE uid = ?", (karma_boost, receiver.id))
            conn.commit()
    await asyncio.to_thread(_sync_op)

    karma_val = await asyncio.to_thread(get_karma, receiver.id)
    await msg.reply_text(
        f"🌟 <b>{receiver.full_name}</b> gained <b>{karma_boost}</b> karma!\nTotal Karma: <b>{format_karma(karma_val)}</b>",
        parse_mode="HTML"
    )


async def handle_manage_showroom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Showroom management: Use /admin_showroom for full access.")


async def handle_remove_bike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Use /admin_removeitem_from for item removal.")


async def handle_show_all_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 Use /admin_owners for owner listing.")


async def groupstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = await asyncio.to_thread(get_all_group_ids)
    if not groups:
        return await update.message.reply_text("📭 No groups tracked yet.")
    lines = ["📊 Tracked Groups:"]
    for gid in groups:
        lines.append(f"• Group ID: <code>{gid}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def track_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type in ["group", "supergroup"]:
        _chat_id = chat.id
        _user_id = user.id
        _username = user.username or user.first_name
        _now = int(time.time())
        def _sync_op():
            with get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_users (
                        chat_id INTEGER, user_id INTEGER, username TEXT, last_seen INTEGER,
                        PRIMARY KEY (chat_id, user_id)
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO active_users (chat_id, user_id, username, last_seen)
                    VALUES (?, ?, ?, ?)
                """, (_chat_id, _user_id, _username, _now))
                conn.commit()
        await asyncio.to_thread(_sync_op)


import logging
from telegram.error import BadRequest


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("⚠️ Exception while handling update:", exc_info=context.error)
    try:
        if hasattr(update, "callback_query") and update.callback_query:
            message = update.callback_query.message
            try:
                await message.edit_text("⚠️ Something went wrong. The devs have been notified.")
            except BadRequest:
                try:
                    await message.edit_caption("⚠️ Something went wrong.")
                except Exception as e:
                    logging.error("🧨 Failed to edit caption:", exc_info=e)
        else:
            chat = getattr(update, "effective_chat", None)
            if chat:
                await context.bot.send_message(chat.id, "⚠️ Something went wrong.")
    except Exception as e:
        logging.error("🧨 Failed to send error message:", exc_info=e)


async def unified_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    reply_to = msg.reply_to_message

    if not reply_to or reply_to.from_user.id != context.bot.id or not msg.text:
        return

    reply = await asyncio.to_thread(get_ai_reply, msg.text)
    await msg.reply_text(reply)


OWNER_USERNAME = "@Itachiplub2"


async def owner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.from_user.is_bot:
        return
    text = msg.text or ""
    if re.search(r"\bowner\b", text, re.IGNORECASE):
        await msg.reply_text(OWNER_USERNAME)


async def manager_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.from_user.is_bot:
        return
    text = msg.text or ""
    if re.search(r"\bmanager\b", text, re.IGNORECASE):
        await msg.reply_text("I AM SELF DEPENDENT")


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATION SETUP
# ══════════════════════════════════════════════════════════════════════════════

application = ApplicationBuilder().token(BOT_TOKEN).build()

for h in admin_handlers:
    application.add_handler(h, group=0)

application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, itachi_listener), group=2
)
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, nitho_listener), group=3
)
application.add_handler(reaction_handler, group=2)

# ── Core commands ─────────────────────────────────────────────────────────────
commands = {
    "start": start,
    "help": help_command,
    "balance": balance,
    "earn": earn,
    "resetearn": resetearn,
    "reverse": reverse,
    "draw": draw,
    "mycards": mycards,
    "steal": steal,
    "send": send,
    "give": give,
    "challenge": challenge,
    "request": request_coins,
    "top": top,
    "btop": btop,
    "taxpool": taxpool,
    "listusers": listusers,
    "dumpusers": dumpusers,
    "flip": flip,
    "roll": roll,
    "rps": rps,
    "guessbet": guessbet,
    "spin": spin,
    "enter": enter,
    "removeuser": removeuser,
    "geco": getcoins,
    "uploadcard": uploadcard,
    "deletebyname": deletebyname,
    "admincards": admincards,
    "purgecardbyindex": purgecardbyindex,
    "purgecard": purgecard,
    "deletecardbyindex": deletecardbyindex,
    "adco": adjustcoins,
    "adjusthistory": adjusthistory,
    "checkbalance": checkbalance,
    "transferlog": transferlog,
    "duelrank": duelrank,
    "cardvault": cardvault,
    "cardlist": cardlist,
    "broadcast": broadcast,
    "party": party,
    "karma": karma,
    "adminpanel": adminpanel,
    "assetmarket": assetmarket,
    "buyasset": buyasset,
    "myassets": myassets,
    "collectincome": collectincome,
    "sellasset": sellasset,
    "mintasset": mintasset,
    "removeasset": removeasset,
    "investrank": investrank,
    "assetinfo": assetinfo,
    "assettrend": assettrend,
    "fluctuateprices": fluctuateprices,
    "auditvault": auditvault,
    "assetshare": assetshare,
    "bankstats": bankstats,
    "assetcompare": assetcompare,
    "assetlore": assetlore,
    "flashsale": flashsale,
    "runbankengine": runbankengine,
    "achievements": achievements,
    "assettitle": assettitle,
    "questbook": questbook,
    "getfileid": getfileid,
    "groupgoal": groupgoal,
    "dailymission": dailymission,
    "claimstreak": claimstreak,
    "profilecard": profilecard,
    "bossfight": bossfight,
    "settitle": settitle,
    "invite": invite,
    "duelnews": duelnews,
    "banknews": banknews,
    "npcvisit": npcvisit,
    "cardstats": cardstats,
    "prestigevault": prestigevault,
    "shinobiquiz": shinobiquiz,
    "karmahall": karmahall,
    "duelbadge": duelbadge,
    "shinobishop": shinobishop,
    "byitem": byitem,
    "shinobititle": shinobititle,
    "karmaquiz": karmaquiz,
    "shinobirank": shinobirank,
    "shinobibadge": shinobibadge,
    "shinobichest": shinobichest,
    "shinobiarena": shinobiarena,
    "shinobitask": shinobitask,
    "shinobiblessing": shinobiblessing,
    "shinobiforge": shinobiforge,
    "shinobitrade": shinobitrade,
    "shinobialtar": shinobialtar,
    "shinobimarket": shinobimarket,
    "shinobitomb": shinobitomb,
    "marketbuy": marketbuy,
    "tombstats": tombstats,
    "shinobifusion": shinobifusion,
    "shinobibattle": shinobibattle,
    "shinobirelic": shinobirelic,
    "shinobiartefact": shinobiartefact,
    "shinobiblessingvault": shinobiblessingvault,
    "shinobilegacy": shinobilegacy,
    "sendheart": sendheart,
    "debugvault": debugvault,
    "createclan": createclan,
    "leaveclan": leaveclan,
    "joinclan": joinclan,
    "clangoal": clangoal,
    "clanrank": clanrank,
    "myclan": myclan,
    "welcome": welcome,
    "farewell": farewell,
    "setwelcome": setwelcome,
    "setfarewell": setfarewell,
    "viewwelcome": viewwelcome,
    "schedulemsg": schedulemsg,
    "viewschedule": viewschedule,
    "clearschedule": clearschedule,
    "broadcaststatus": broadcaststatus,
    "myreferrals": myreferrals,
    "referrank": referrank,
    "setrefreward": setrefreward,
    "createbank": createbank,
    "joinbank": joinbank,
    "mybank": mybank,
    "bankinfo": bankinfo,
    "bankdeposit": bankdeposit,
    "bankwithdraw": bankwithdraw,
    "bankrank": bankrank,
    "bankdashboard": bankdashboard,
    "transferbank": transferbank,
    "bankmembers": bankmembers,
    "deletebank": deletebank,
    "banklog": banklog,
    "bankinvite": bankinvite,
    "bankaudit": bankaudit,
    "sab": handle_sab,
    "circle_list": handle_circle_list,
    "circle_clear": handle_circle_clear,
    "sahab": handle_sahab,
    "manage_showroom": handle_manage_showroom,
    "remove_bike": handle_remove_bike,
    "show_all_owners": handle_show_all_owners,
    "viewcards": viewcards,
    "checkcards": checkcards,
    "groupstats": groupstats,
}

for cmd, func in commands.items():
    application.add_handler(CommandHandler(cmd, func))

# ── Callbacks ─────────────────────────────────────────────────────────────────
application.add_handler(CallbackQueryHandler(heart_confirm_handler, pattern="^heart_"))
application.add_handler(CallbackQueryHandler(deletecard_callback, pattern="^removecard:"))
application.add_handler(CallbackQueryHandler(button_handler, pattern="^(accept|reject):"))
application.add_handler(CallbackQueryHandler(fight_action, pattern="^(punch|slap|kick)$"))
application.add_handler(CallbackQueryHandler(proposal_response_handler, pattern="^proposal_"))
application.add_handler(CallbackQueryHandler(handle_mines_button, pattern="^(reveal_|exitmines)"))
application.add_handler(CallbackQueryHandler(handle_wire_choice, pattern=r"^wire:"))
application.add_handler(CallbackQueryHandler(handle_battle_response, pattern=r"^(accept_battle|decline_battle):"))
application.add_handler(CallbackQueryHandler(status_callback_handler,
    pattern="^(refresh_status|full_stats_report|admin_restart|admin_leaderboard|admin_tax_pool|admin_transfer_logs)$"))
application.add_handler(CallbackQueryHandler(card_callback, pattern="^card_"))
application.add_handler(CallbackQueryHandler(panel_callback))   # catch-all, must be last

# ── Inline text pattern handlers ──────────────────────────────────────────────
application.add_handler(MessageHandler(
    filters.TEXT & filters.REPLY & filters.Regex(r"(?i)\bowner\b"), owner_handler
))
application.add_handler(MessageHandler(
    filters.TEXT & filters.REPLY & filters.Regex(r"(?i)\bmanager\b"), manager_handler
))

# ── Extra command aliases ─────────────────────────────────────────────────────
application.add_handler(CommandHandler("startwordgame", startwordgame))
application.add_handler(CommandHandler("ithink", guess))
application.add_handler(CommandHandler("hint", hint))
application.add_handler(CommandHandler("wordscore", wordscore))
application.add_handler(CommandHandler("wordtop", wordtop))
application.add_handler(CommandHandler("g", guess))
application.add_handler(CommandHandler("dig", dig))
application.add_handler(CommandHandler("blackjack", blackjack))
application.add_handler(CommandHandler("heist", heist))
application.add_handler(CommandHandler("fly", fly))
application.add_handler(CommandHandler("flystorm", flystorm))
application.add_handler(CommandHandler("flyshd", flyshield))
application.add_handler(CommandHandler("hafta", bribe))
application.add_handler(CommandHandler("wanted", wanted))
application.add_handler(CommandHandler("raid", raid))
application.add_handler(CommandHandler("unraid", unraid))
application.add_handler(CommandHandler("resetwallets", resetwallets))
application.add_handler(CommandHandler("resetdeposit", resetdeposit))
application.add_handler(CommandHandler("resetbank", resetbank))
application.add_handler(CommandHandler("resetinvestments", resetinvestments))
application.add_handler(CommandHandler("resetassets", resetassets))
application.add_handler(CommandHandler("resettea", resettea))
application.add_handler(CommandHandler("cleartax", cleartax))
application.add_handler(CommandHandler("propose", propose))
application.add_handler(CommandHandler("sellcard", sellcard))
application.add_handler(CommandHandler("distribute_tax", distribute_tax))
application.add_handler(CommandHandler("gift", gift))
application.add_handler(CommandHandler("exchange", exchange))
application.add_handler(CommandHandler("allcards", allcards))
application.add_handler(CommandHandler("editcard", editcard))
application.add_handler(CommandHandler("broadcastgroups", broadcastgroups))
application.add_handler(CommandHandler("broadcastdms", broadcastdms))
application.add_handler(CommandHandler("dmchat", dmchat))
application.add_handler(CommandHandler("finduid", finduid))
application.add_handler(CommandHandler("loan", loan))
application.add_handler(CommandHandler("rloan", repay_loan))
application.add_handler(CommandHandler("mloan", my_loan))
application.add_handler(CommandHandler("bloan", top_loans))
application.add_handler(CommandHandler("resetloan", resetloan))
application.add_handler(CommandHandler("resetallloans", resetallloans))
application.add_handler(CommandHandler("deduct", deduct_command))
application.add_handler(CommandHandler("tea", tea))
application.add_handler(CommandHandler("daily", daily))
application.add_handler(CommandHandler("leaderboard", leaderboard))
application.add_handler(CommandHandler("mines", mines))
application.add_handler(CommandHandler("minestrap", minestrap_toggle))
application.add_handler(CommandHandler("defuse", defuse))
application.add_handler(CommandHandler("tnd", start_tnd))
application.add_handler(CommandHandler("jointnd", join_tnd))
application.add_handler(CommandHandler("ready", ready_tnd))
application.add_handler(CommandHandler("truth", truth_tnd))
application.add_handler(CommandHandler("dare", dare_tnd))
application.add_handler(CommandHandler("complete", complete_tnd))
application.add_handler(CommandHandler("leavetnd", leavetnd))
application.add_handler(CommandHandler("endtnd", endtnd))
application.add_handler(CommandHandler("toptnd", toptnd))
application.add_handler(CommandHandler("tndstats", tndstats))
application.add_handler(CommandHandler("referrals", referrals))
application.add_handler(CommandHandler("referralscore", referralscore))
application.add_handler(CommandHandler("referralmap", referralmap))
application.add_handler(CommandHandler("bank", bank))
application.add_handler(CommandHandler("deposit", deposit))
application.add_handler(CommandHandler("withdraw", withdraw))
application.add_handler(CommandHandler("topbank", topbank))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(CommandHandler("claiminterest", claiminterest))
application.add_handler(CommandHandler("taxbank", taxbank))
application.add_handler(CommandHandler("taxtop", taxtop))
application.add_handler(CommandHandler("banklist", banklist))
application.add_handler(CommandHandler("leavebank", leavebank))
application.add_handler(CommandHandler("confirmleavebank", confirmleavebank))
application.add_handler(CommandHandler("uploadgiveawaycard", uploadgiveawaycard))
application.add_handler(CommandHandler("giveawaycards", giveawaycards))
application.add_handler(CommandHandler("editgiveawaycardbyindex", editgiveawaycardbyindex))
application.add_handler(CommandHandler("givecard", givecard))
application.add_handler(CommandHandler("mygiveaways", mygiveaways))
application.add_handler(CommandHandler("giveawaylist", giveawaylist))
application.add_handler(CommandHandler("removegivecard", removegivecard))
application.add_handler(CommandHandler("deletegiveawaycard", deletegiveawaycard))
application.add_handler(CommandHandler("additem", additem))
application.add_handler(CommandHandler("showroom", showroom))
application.add_handler(CommandHandler("buy", buy))
application.add_handler(CommandHandler("myshowroom", myshowroom))
application.add_handler(CommandHandler("sellitem", sellitem))
application.add_handler(CommandHandler("market", market))
application.add_handler(CommandHandler("buymitem", buymitem))
application.add_handler(CommandHandler("mylistings", mylistings))
application.add_handler(CommandHandler("cancelitem", cancelitem))
application.add_handler(CommandHandler("admin_showroom", admin_showroom))
application.add_handler(CommandHandler("admin_additem_to", admin_additem_to))
application.add_handler(CommandHandler("admin_removeitem_from", admin_removeitem_from))
application.add_handler(CommandHandler("admin_market", admin_market))
application.add_handler(CommandHandler("admin_removelisting", admin_removelisting))
application.add_handler(CommandHandler("admin_owners", admin_owners))
application.add_handler(CommandHandler("rakhi", handle_rakhi))
application.add_handler(CommandHandler("rakhibond", handle_rakhibond))
application.add_handler(CommandHandler("rakhiuntie", handle_rakhiuntie))
application.add_handler(CommandHandler("rakhiwrite", handle_rakhiwrite))
application.add_handler(CommandHandler("rakhiwish", handle_rakhiwish))
application.add_handler(CommandHandler("rakhiwall", handle_rakhiwall))
application.add_handler(CommandHandler("rakhiarchive", handle_rakhiarchive))
application.add_handler(CommandHandler("rakhitop", handle_rakhitop))
application.add_handler(CommandHandler("restart", bot_restart))
application.add_handler(CommandHandler("bstatus", bot_status))
application.add_handler(CommandHandler("health", bot_health))
application.add_handler(CommandHandler("adoptpet", adoptpet))
application.add_handler(CommandHandler("feedpet", feedpet))
application.add_handler(CommandHandler("mypet", mypet))
application.add_handler(CommandHandler("petbattle", petbattle))
application.add_handler(CommandHandler("listitems", listitems))
application.add_handler(CommandHandler("edititem", edititem))
application.add_handler(CommandHandler("deleteitem", deleteitem))
application.add_handler(CommandHandler("decksync", decksync))
application.add_handler(CommandHandler("drawpreview", drawpreview))
application.add_handler(CommandHandler("mycards_preview", mycards_preview))
application.add_handler(CommandHandler("deckclean", deckclean))
application.add_handler(CommandHandler("fixcards", fixcards))
application.add_handler(CommandHandler("uploadbulk", uploadbulk))
application.add_handler(CommandHandler("endbulk", endbulk))
application.add_handler(MessageHandler(filters.PHOTO & filters.Caption(), handle_bulk_photo))
application.add_handler(CommandHandler("mentionall", mentionall))

# ── Catch-all / low-priority handlers (group=5 and group=10) ─────────────────
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, unified_message_handler), group=5
)
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, dm_reply_listener), group=5
)

application.add_handler(MessageHandler(filters.ALL, track_group_user), group=10)
application.add_handler(MessageHandler(filters.ALL, track_group), group=10)
application.add_handler(MessageHandler(filters.ALL, track_activity), group=10)
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, activity_tracker), group=10
)

# ── Group management & welcome ────────────────────────────────────────────────
for handler in get_groupmanage_handlers():
    application.add_handler(handler)

add_handlers(application)

application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, karma_handler))

application.add_error_handler(error_handler)

# FIX: register_admin_commands with correct bot object — called at startup
register_admin_commands(application.bot)


# ── Scheduled message loop ────────────────────────────────────────────────────
async def check_scheduled_messages(app):
    while True:
        now = int(time.time())
        to_send = [msg for msg in scheduled_messages if msg["timestamp"] <= now]
        for msg in to_send:
            try:
                await app.bot.send_message(msg["chat_id"], msg["text"])
            except Exception as e:
                print(f"⚠️ Failed to send scheduled message: {e}")
            scheduled_messages.remove(msg)
        await asyncio.sleep(60)


# ── Lifecycle hooks ───────────────────────────────────────────────────────────
async def on_startup(app):
    await send_alive_logger(app.bot, "Itachi Bot")
    print("🚀 Scheduler started.")
    asyncio.create_task(check_scheduled_messages(app))
    start_backup_scheduler()
    try:
        backup_database()
    except Exception as e:
        print(f"⚠️ Initial backup failed: {e}")


async def on_shutdown(app):
    await send_shutdown_logger(app.bot, "Itachi Bot")
    print("👋 Shutdown triggered. Cleaning up…")


application.post_init = on_startup
application.post_shutdown = on_shutdown


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("✅ Itachi Bot is running... (Press Ctrl+C to stop)")
    try:
        # FIX: removed stop_signals=None so Ctrl+C (SIGINT) works correctly
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
    finally:
        print("✅ Cleanup done.")