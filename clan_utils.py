import time
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from database import get_balance, update_balance, get_conn, get_user_by_username, setup_clan_tables

CLAN_CREATION_TAX = 500


def create_clan(name, founder_id):
    with get_conn() as conn:
        conn.execute("INSERT INTO clans (name, founder_id, created_at) VALUES (?, ?, ?)", (name, founder_id, int(time.time())))
        clan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO clan_members (clan_id, uid, position, joined_at) VALUES (?, ?, ?, ?)", (clan_id, founder_id, "Master", int(time.time())))
        conn.commit()
        return clan_id

def get_clan_by_name(name):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM clans WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

def get_user_clan(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT clan_id FROM clan_members WHERE uid=?", (uid,)).fetchone()
        return row[0] if row else None

def join_clan(clan_id, uid):
    with get_conn() as conn:
        conn.execute("INSERT INTO clan_members (clan_id, uid, position, joined_at) VALUES (?, ?, ?, ?)", (clan_id, uid, "Member", int(time.time())))
        conn.commit()

def clan_goal_progress(clan_id):
    with get_conn() as conn:
        return conn.execute("SELECT goal_name, progress, target FROM clan_goals WHERE clan_id=?", (clan_id,)).fetchall()

def cast_vote(clan_id, voter_uid, target_uid):
    with get_conn() as conn:
        conn.execute("REPLACE INTO clan_votes (clan_id, voter_uid, target_uid) VALUES (?, ?, ?)", (clan_id, voter_uid, target_uid))
        conn.commit()

def get_clan_leaderboard(limit=10):
    with get_conn() as conn:
        return conn.execute("""
            SELECT clans.name, COUNT(*) as completed
            FROM clan_goals
            JOIN clans ON clans.id = clan_goals.clan_id
            WHERE clan_goals.progress >= clan_goals.target
            GROUP BY clan_goals.clan_id
            ORDER BY completed DESC
            LIMIT ?
        """, (limit,)).fetchall()

async def createclan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = " ".join(context.args).strip() if context.args else None

    if not name:
        return await update.message.reply_text("🏯 Usage: /createclan <clan_name>")
    if await asyncio.to_thread(get_balance, uid) < CLAN_CREATION_TAX:
        return await update.message.reply_text(f"💰 You need {CLAN_CREATION_TAX} coins to create a clan.")
    if await asyncio.to_thread(get_user_clan, uid):
        return await update.message.reply_text("🚫 You are already in a clan.")

    clan_id = await asyncio.to_thread(create_clan, name, uid)
    await asyncio.to_thread(update_balance, uid, -CLAN_CREATION_TAX)
    await update.message.reply_text(
        f"✅ Clan <b>{name}</b> created successfully!\nYou are the Clan Master.\n💸 {CLAN_CREATION_TAX} coins deducted.",
        parse_mode="HTML"
    )

async def joinclan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user      = update.effective_user
    clan_name = " ".join(context.args or []).strip()

    if not clan_name:
        return await update.message.reply_text("🏯 Usage: /joinclan <clan_name>")

    clan_id = await asyncio.to_thread(get_clan_by_name, clan_name)
    if not clan_id:
        return await update.message.reply_text(f"❌ Clan '{clan_name}' not found.")

    if await asyncio.to_thread(get_user_clan, user.id):
        return await update.message.reply_text("🚫 You are already in a clan.")

    username  = user.username or user.first_name
    joined_at = int(time.time())
    position  = "Member"

    def _join():
        with get_conn() as conn:
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                  idx_clan_members_clan_uid
                ON clan_members(clan_id, uid)
            """)
            conn.execute("""
                INSERT INTO clan_members
                  (clan_id, uid, username, position, joined_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(clan_id, uid) DO UPDATE
                  SET username  = excluded.username,
                      position  = excluded.position,
                      joined_at = excluded.joined_at
            """, (clan_id, user.id, username, position, joined_at))
            conn.commit()

    await asyncio.to_thread(_join)

    await update.message.reply_text(
        f"✅ You joined clan <b>{clan_name}</b> as {position}!",
        parse_mode="HTML"
    )


async def clangoal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clan_id = await asyncio.to_thread(get_user_clan, uid)
    if not clan_id:
        return await update.message.reply_text("🏯 You're not in a clan.")

    goals = await asyncio.to_thread(clan_goal_progress, clan_id)
    if not goals:
        return await update.message.reply_text("📭 No active goals for your clan.")

    lines = ["📜 <b>Clan Goals</b>:"]
    for goal_name, progress, target in goals:
        status = "✅ Completed" if progress >= target else f"🔄 {progress}/{target}"
        lines.append(f"• <b>{goal_name}</b>: {status}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def voteleader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voter_id = update.effective_user.id
    if not context.args or not context.args[0].startswith("@"):
        return await update.message.reply_text("🗳️ Usage: /voteleader @username")

    target_username = context.args[0][1:]
    target_id = await asyncio.to_thread(get_user_by_username, target_username)
    if not target_id:
        return await update.message.reply_text(f"❌ User '@{target_username}' not found.")

    clan_id = await asyncio.to_thread(get_user_clan, voter_id)
    if not clan_id:
        return await update.message.reply_text("🚫 You're not in a clan.")
    if await asyncio.to_thread(get_user_clan, target_id) != clan_id:
        return await update.message.reply_text("🚫 That user is not in your clan.")

    await asyncio.to_thread(cast_vote, clan_id, voter_id, target_id)
    await update.message.reply_text(f"🗳️ Vote cast for <b>@{target_username}</b> as new Clan Master!", parse_mode="HTML")

async def clanrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard = await asyncio.to_thread(get_clan_leaderboard)
    if not leaderboard:
        return await update.message.reply_text("📭 No clans have completed goals yet.")

    lines = ["🏆 <b>Top Clans</b> — By Goals Completed:"]
    for i, (clan_name, count) in enumerate(leaderboard, start=1):
        lines.append(f"{i}. <b>{clan_name}</b> — ✅ {count} goals")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def myclan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid      = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    def _get_myclan():
        with get_conn() as conn:
            clan_row = conn.execute("""
                SELECT c.id, c.name, c.master_uid, m.title
                  FROM clans c
                  JOIN clan_members m ON c.id = m.clan_id
                 WHERE m.uid = ?
            """, (uid,)).fetchone()

            if not clan_row:
                return None, None

            clan_id, clan_name, master_uid, your_title = clan_row

            members = conn.execute("""
                SELECT uid, username, title
                  FROM clan_members
                 WHERE clan_id = ?
            """, (clan_id,)).fetchall()

            return (clan_id, clan_name, master_uid, your_title, members)

    result = await asyncio.to_thread(_get_myclan)
    clan_id, clan_name, master_uid, your_title, members = result

    if not clan_id:
        return await update.message.reply_text("❌ You're not part of any clan.")

    lines = [
        f"🏯 Clan: <b>{clan_name}</b>",
        f"👤 You: <b>{username}</b> — {your_title}",
        "👥 Members:"
    ]

    for m_uid, m_username, m_title in members:
        tag = 'Master' if m_uid == master_uid else m_title
        lines.append(f"• @{m_username} — {tag}")


    footer = [""]  # blank line
    if uid == master_uid:
        footer.append(
            "As master, set titles by replying to a member’s message with "
            "/settitle <New Title>"
        )
    footer.append("📭 No active goals.")

    await update.message.reply_text(
        "\n".join(lines + footer),
        parse_mode="HTML"
    )




async def leaveclan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    setup_clan_tables()

    def _leave():
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT c.name
                  FROM clan_members m
                  JOIN clans c ON m.clan_id = c.id
                 WHERE m.uid = ?
                """,
                (uid,)
            ).fetchone()

            if not row:
                return None

            clan_name = row[0]

            conn.execute("DELETE FROM clan_members WHERE uid = ?", (uid,))
            conn.commit()

            return clan_name

    clan_name = await asyncio.to_thread(_leave)

    if not clan_name:
        return await update.message.reply_text("❌ You're not part of any clan.")

    await update.message.reply_text(
        f"🚪 <b>{username}</b> has left the clan <b>{clan_name}</b>.",
        parse_mode="HTML"
    )


def get_user_title(uid: int, clan_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT title FROM clan_members WHERE clan_id = ? AND uid = ?",
            (clan_id, uid),
        ).fetchone()
        return row[0] if row else None

async def settitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    issuer   = update.effective_user
    args     = context.args or []

    clan_id = await asyncio.to_thread(get_user_clan, issuer.id)
    if not clan_id:
        return await update.message.reply_text("🚫 You're not in any clan.")

    if await asyncio.to_thread(get_user_title, issuer.id, clan_id) != "Master":
        return await update.message.reply_text("❌ Only the clan master can set titles.")

    if update.message.reply_to_message:
        # — If replying to a member’s message
        target_user = update.message.reply_to_message.from_user
        new_title   = " ".join(args).strip()
    else:
        if len(args) < 2:
            return await update.message.reply_text(
                "🏷 Usage: /settitle <@username|user_id> <new title>"
            )
        mention, *title_parts = args
        new_title = " ".join(title_parts).strip()

        if mention.startswith("@"):
            uname = mention.lstrip("@")
            def _lookup():
                with get_conn() as conn:
                    row = conn.execute(
                        "SELECT uid FROM clan_members WHERE clan_id = ? AND username = ?",
                        (clan_id, uname),
                    ).fetchone()
                    return row
            row = await asyncio.to_thread(_lookup)
            if not row:
                return await update.message.reply_text(f"❌ {mention} is not in your clan.")
            target_user = type("U", (), {"id": row[0], "username": uname})
        elif mention.isdigit():
            target_user = type("U", (), {"id": int(mention), "username": None})
        else:
            return await update.message.reply_text("❌ Invalid user. Use @username or user ID.")

    if not new_title:
        return await update.message.reply_text("❌ Title cannot be empty.")

    def _set_title():
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE clan_members
                SET title = ?
                WHERE clan_id = ? AND uid = ?
                """,
                (new_title, clan_id, target_user.id),
            )

    await asyncio.to_thread(_set_title)

    display_name = (
        f"@{target_user.username}"
        if getattr(target_user, "username", None)
        else f"UID {target_user.id}"
    )
    await update.message.reply_text(
        f"✅ Set title of <b>{display_name}</b> to “<i>{new_title}</i>”.",
        parse_mode="HTML",
    )