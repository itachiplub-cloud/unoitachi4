from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from datetime import datetime, timedelta
from database import db_lock, get_conn
import asyncio
import random
import time

tnd_sessions = {}
_TND_SESSION_TTL = 3600  # 1 hour

tnd_stats = {}


def _cleanup_tnd_sessions():
    now = datetime.now()
    stale = [k for k, v in tnd_sessions.items()
             if (now - v.get("created_at", now)).total_seconds() > _TND_SESSION_TTL]
    for k in stale:
        del tnd_sessions[k]

def create_session(host_id: int, host_name: str = "Host"):
    _cleanup_tnd_sessions()
    tnd_sessions[host_id] = {
        "players": {},             
        "order": [],                
        "current_turn": 0,          
        "current_player": None,     
        "status": "waiting",        
        "completed": set(),         
        "created_at": datetime.now(),
        "theme": "default",         
        "host_name": host_name      
    }

def get_session_by_uid(uid: int):
    for host_id, session in tnd_sessions.items():
        if uid == host_id or uid in session["players"]:
            return host_id, session
    return None, None



async def start_tnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid in tnd_sessions:
        return await update.message.reply_text("❌ You already have a game running.")

    create_session(uid)

    await update.message.reply_text(
        "🧠🔥 <b>Truth & Dare Game Started!</b>\n"
        "You are now the host. Players can join using <code>/jointnd &lt;name&gt;</code>\n\n"
        "🧩 <b>Phase 1: Game Setup</b>\n"
        "<code>/tnd</code> → Starts the game (host only)\n"
        "<code>/jointnd &lt;name&gt;</code> → Join with a nickname\n"
        "<code>/ready</code> → Start the game once players join\n"
        "<code>/endtnd</code> → End the game manually\n\n"
        "🎮 <b>Phase 2: Turn Flow</b>\n"
        "Bot picks a random player: \u201cIt\u2019s <i>name</i>\u2019s turn!\u201d\n"
        "<code>/truth</code> or <code>/dare</code> → Choose your challenge\n"
        "Bot prompts: \u201cGive a truth/dare to <i>name</i>\u201d\n"
        "Other player replies with challenge\n"
        "<code>/complete</code> → Finish your turn\n"
        "<code>/ready</code> → Trigger next turn\n\n"
        "🏁 <b>Phase 3: Game End</b>\n"
        "<code>/endtnd</code> → Ends the game\n"
        "Bot rewards all players with coins\n"
        "Bot shows summary: who joined, who completed most\n\n"
        "📊 <b>Extras</b>\n"
        "<code>/tndboard</code> → Top dare players\n"
        "<code>/tndstats</code> → Your personal stats\n"
        "<code>/leavetnd</code> → Exit mid-game\n\n"
        "🕶️ Reverse God watches. Play fair. Play wild.",
        parse_mode=ParseMode.HTML
    )

async def join_tnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args:
        return await update.message.reply_text("❌ Usage: /jointnd <nickname>")

    nickname = args[0]
    host_id, session = get_session_by_uid(uid)

    if session:
        return await update.message.reply_text("❌ You're already in a game.")

    for host_id, session in tnd_sessions.items():
        if session["status"] == "waiting":
            session["players"][uid] = nickname
            session["order"].append(uid)

            # Track stats
            if uid not in tnd_stats:
                tnd_stats[uid] = {"completed": 0, "joined": 0}
            tnd_stats[uid]["joined"] += 1

            return await update.message.reply_text(f"✅ Joined game as <b>{nickname}</b>!", parse_mode=ParseMode.HTML)

    await update.message.reply_text("❌ No active game found. Ask someone to start with /tnd.")


async def ready_tnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    host_id, session = get_session_by_uid(uid)

    if not session:
        return await update.message.reply_text("❌ You're not in any game.")

    if session["status"] == "waiting":
        if uid != host_id:
            return await update.message.reply_text("❌ Only the host can start the game.")
        if not session["players"]:
            return await update.message.reply_text("❌ No players joined yet.")
        session["status"] = "active"
        return await update.message.reply_text("✅ Game started! Send /ready to begin the first turn.")

    if session["status"] != "active":
        return await update.message.reply_text("❌ Game is not active.")

    if session["current_turn"] >= len(session["order"]):
        session["current_turn"] = 0  # Loop back

    target_uid = session["order"][session["current_turn"]]
    nickname = session["players"].get(target_uid, "Unknown")

    session["current_player"] = target_uid
    session["current_turn"] += 1

    return await update.message.reply_text(
        f"🎯 It's <b>{nickname}</b>'s turn!\nChoose: /truth or /dare",
        parse_mode=ParseMode.HTML
    )

async def truth_tnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    host_id, session = get_session_by_uid(uid)

    if not session or session["status"] != "active":
        return await update.message.reply_text("❌ No active game.")

    if session.get("current_player") != uid:
        return await update.message.reply_text("❌ It's not your turn.")

    nickname = session["players"].get(uid, "Unknown")
    return await update.message.reply_text(
        f"🧠 Give a <b>truth</b> to <b>{nickname}</b>!",
        parse_mode=ParseMode.HTML
    )

async def dare_tnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    host_id, session = get_session_by_uid(uid)

    if not session or session["status"] != "active":
        return await update.message.reply_text("❌ No active game.")

    if session.get("current_player") != uid:
        return await update.message.reply_text("❌ It's not your turn.")

    nickname = session["players"].get(uid, "Unknown")
    return await update.message.reply_text(
        f"🔥 Give a <b>dare</b> to <b>{nickname}</b>!",
        parse_mode=ParseMode.HTML
    )


async def complete_tnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    host_id, session = get_session_by_uid(uid)

    if not session or session["status"] != "active":
        return await update.message.reply_text("❌ No active game.")

    if session.get("current_player") != uid:
        return await update.message.reply_text("❌ It's not your turn.")

    session["completed"].add(uid)
    tnd_stats[uid]["completed"] += 1

    return await update.message.reply_text("✅ Challenge completed! Host or bot can now send /ready for next turn.")

async def leavetnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    host_id, session = get_session_by_uid(uid)

    if not session:
        return await update.message.reply_text("❌ You're not in any game.")

    if uid == host_id:
        return await update.message.reply_text("❌ Host must use /endtnd to end the game.")

    session["players"].pop(uid, None)
    session["order"] = [u for u in session["order"] if u != uid]

    return await update.message.reply_text("🚪 You've left the game.")

async def endtnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    session = tnd_sessions.get(uid)

    if not session:
        return await update.message.reply_text("❌ You're not hosting any game.")

    player_ids = list(session["players"].keys())

    def _db_work():
        with db_lock:
            with get_conn() as conn:
                for pid in player_ids:
                    conn.execute("UPDATE users SET coins = coins + 100 WHERE id = ?", (pid,))
                conn.commit()

    await asyncio.to_thread(_db_work)

    summary = "\n".join([
        f"• {session['players'][pid]} — ✅ {tnd_stats[pid]['completed']} completed"
        for pid in session["players"]
    ])

    del tnd_sessions[uid]

    return await update.message.reply_text(
        f"🏁 <b>Game Ended!</b>\nAll players received ₹100 coins.\n\n<b>Summary:</b>\n{summary}",
        parse_mode=ParseMode.HTML
    )


async def toptnd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tnd_stats:
        return await update.message.reply_text("📉 No Truth & Dare data yet.")

    top_players = sorted(tnd_stats.items(), key=lambda x: x[1]["completed"], reverse=True)[:10]

    async def _get_name(uid):
        try:
            chat = await context.bot.get_chat(uid)
            return uid, chat.first_name
        except Exception:
            return uid, "Unknown"

    results = await asyncio.gather(*[_get_name(uid) for uid, _ in top_players])
    names = dict(results)

    leaderboard = "\n".join([
        f"{i+1}. <b>{names[uid]}</b> — ✅ {data['completed']} dares"
        for i, (uid, data) in enumerate(top_players)
    ])

    await update.message.reply_text(
        f"📊 <b>Top Truth & Dare Players</b>\n{leaderboard}",
        parse_mode=ParseMode.HTML
    )

async def tndstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    stats = tnd_stats.get(uid)

    if not stats:
        return await update.message.reply_text("📉 No stats found. Join a game with /jointnd <name>.")

    await update.message.reply_text(
        f"📈 <b>Your T&D Stats</b>\n"
        f"✅ Completed: {stats['completed']}\n"
        f"🎮 Games Joined: {stats['joined']}",
        parse_mode=ParseMode.HTML
    )
