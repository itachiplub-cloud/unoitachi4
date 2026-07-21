import time
import json
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_balance, update_balance, set_balance,
    get_user_stats, get_locked_savings,
    apply_interest, deposit_tax, get_all_users, get_conn,
    get_bank_balance, get_username, set_bank, db_lock,
    is_bot_admin,
    get_ref_reward
)

with open("config.json", "r") as f:
    config = json.load(f)




def setup_bank_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner_uid INTEGER,
                created_at INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_members (
                uid INTEGER PRIMARY KEY,
                bank_id INTEGER,
                joined_at INTEGER
            )
        """)
        conn.commit()


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = int(time.time())

    def _daily_sync():
        with get_conn() as conn:
            row = conn.execute("SELECT last_daily FROM users WHERE id = ?", (uid,)).fetchone()
            last = row[0] if row else 0
            if now - last < 86400:
                return None, int((86400 - (now - last)) / 60)
            reward = 100
            update_balance(uid, reward)
            conn.execute("UPDATE users SET last_daily = ? WHERE id = ?", (now, uid))
            conn.commit()
            return reward, None

    result, wait = await asyncio.to_thread(_daily_sync)
    if result is None:
        return await update.message.reply_text(f"🕒 Already claimed. Try again in {wait} minutes.")
    await update.message.reply_text(f"🎁 You received {result} coins as your daily reward!")


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await asyncio.to_thread(get_all_users)
    if not users:
        return await update.message.reply_text("📭 No users found.")

    lines = ["🏆 Top Richest Users:"]
    for i, (uid, username, coins) in enumerate(users[:10], start=1):
        name = f"@{username}" if username else f"User {uid}"
        lines.append(f"{i}. {name} — {coins} coins")

    await update.message.reply_text("\n".join(lines))


async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _referrals_sync():
        with get_conn() as conn:
            return conn.execute("SELECT username FROM users WHERE referrer_id = ?", (uid,)).fetchall()

    rows = await asyncio.to_thread(_referrals_sync)
    count = len(rows)
    names = [f"@{r[0]}" if r[0] else "Unnamed" for r in rows]
    msg = f"👥 You've invited {count} user(s).\n" + ("\n".join(names) if names else "No referrals yet.")
    await update.message.reply_text(msg)


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bot_username = "uno_reverse_god_bot"
    link = f"https://t.me/{bot_username}?start={uid}"

    await update.message.reply_text(
        f"🎁 <b>Invite Friends</b>\n"
        f"Share this link:\n<a href='{link}'>{link}</a>\n\n"
        f"💰 Earn coins when they join!",
        parse_mode="HTML"
    )


async def myreferrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _myref_sync():
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    new_uid INTEGER PRIMARY KEY,
                    referrer_uid INTEGER,
                    timestamp INTEGER
                )
            """)
            return conn.execute("""
                SELECT new_uid FROM referrals WHERE referrer_uid = ?
            """, (uid,)).fetchall()

    rows = await asyncio.to_thread(_myref_sync)
    if not rows:
        return await update.message.reply_text("🙁 You haven't invited anyone yet.")

    count = len(rows)
    ref_reward = await asyncio.to_thread(get_ref_reward)
    await update.message.reply_text(
        f"🎁 You've invited <b>{count}</b> users!\n💰 Earned: <b>{count * ref_reward} coins</b>",
        parse_mode="HTML"
    )


async def referrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _referrank_sync():
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    new_uid INTEGER PRIMARY KEY,
                    referrer_uid INTEGER,
                    timestamp INTEGER
                )
            """)
            return conn.execute("""
                SELECT referrer_uid, COUNT(*) as total
                FROM referrals
                GROUP BY referrer_uid
                ORDER BY total DESC
                LIMIT 10
            """).fetchall()

    rows = await asyncio.to_thread(_referrank_sync)
    if not rows:
        await update.message.reply_text("No referral data found.")
        return

    lines = ["🏆 <b>Top Referrers</b>"]
    for i, (uid, total) in enumerate(rows, 1):
        lines.append(f"{i}. <a href='tg://user?id={uid}'>User</a> — <b>{total}</b> invites")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def setrefreward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 You're not authorized.")

    try:
        new_value = int(context.args[0])
        def _setref_sync():
            with get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO settings (key, value) VALUES ('ref_reward', ?)
                """, (new_value,))
                conn.commit()

        await asyncio.to_thread(_setref_sync)
        await update.message.reply_text(f"✅ Referral reward set to {new_value} coins.")
    except:
        await update.message.reply_text("⚠️ Usage: /setrefreward <amount>")


async def referralscore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _rs_sync():
        with get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (uid,)).fetchone()[0]

    referred = await asyncio.to_thread(_rs_sync)
    total_earned = referred * 100
    await update.message.reply_text(f"💰 You've earned {total_earned} coins from {referred} referral(s).")


async def referralmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Admins only.")

    def _rmap_sync():
        with get_conn() as conn:
            return conn.execute("""
                SELECT u.username, r.username
                FROM users u
                LEFT JOIN users r ON u.referrer_id = r.id
                WHERE u.referrer_id IS NOT NULL
            """).fetchall()

    rows = await asyncio.to_thread(_rmap_sync)
    if not rows:
        return await update.message.reply_text("📭 No referral data found.")

    lines = ["📊 Referral Map:"]
    for invitee, referrer in rows:
        lines.append(f"👤 @{invitee} was invited by @{referrer}")
    await update.message.reply_text("\n".join(lines))


async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _bank_sync():
        with get_conn() as conn:
            row = conn.execute("SELECT bank FROM users WHERE id = ?", (uid,)).fetchone()
            return row[0] if row else 0

    bank_balance = await asyncio.to_thread(_bank_sync)
    await update.message.reply_text(f"🏦 Your bank balance: {bank_balance} coins")


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args or not args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /deposit <amount>")

    amount = int(args[0])
    coins = await asyncio.to_thread(get_balance, uid)

    if coins < amount:
        return await update.message.reply_text("❌ Not enough coins to deposit.")

    now = int(time.time())

    def _dep_sync():
        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET coins = coins - ?, bank = bank + ?, last_deposit_time = ? WHERE id = ?", (amount, amount, now, uid))
                conn.commit()

    await asyncio.to_thread(_dep_sync)
    await update.message.reply_text(f"✅ Deposited ₹{amount} into bank.\n⏳ Interest will be claimable after 24 hours using /claiminterest")


async def claiminterest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = int(time.time())

    def _claim_sync():
        with get_conn() as conn:
            row = conn.execute("SELECT bank, last_deposit_time FROM users WHERE id = ?", (uid,)).fetchone()
            if not row:
                return None, None, None
            bank_balance, last_deposit = row
            if now - last_deposit < 86400:
                remaining = 86400 - (now - last_deposit)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return None, hours, minutes
            interest = int(bank_balance * 0.04)
            with db_lock:
                conn.execute("UPDATE users SET bank = bank + ?, last_deposit_time = ? WHERE id = ?", (interest, now, uid))
                conn.commit()
            return interest, None, None

    result, hours, minutes = await asyncio.to_thread(_claim_sync)
    if result is None and hours is not None:
        return await update.message.reply_text(f"⏳ You can claim interest in {hours}h {minutes}m.")
    if result is None:
        return await update.message.reply_text("❌ You don't have a bank account.")
    await update.message.reply_text(f"✅ Claimed ₹{result} interest on your bank savings.")


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args or not args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /withdraw <amount>")

    amount = int(args[0])
    bank_balance = await asyncio.to_thread(get_bank_balance, uid)

    if bank_balance < amount:
        return await update.message.reply_text("❌ Not enough bank savings.")

    tax = int(amount * 0.025)
    net = amount - tax

    def _wd_sync():
        with db_lock:
            with get_conn() as conn:
                conn.execute("UPDATE users SET bank = bank - ?, coins = coins + ? WHERE id = ?", (amount, net, uid))
                conn.commit()

    await asyncio.to_thread(_wd_sync)
    await asyncio.to_thread(deposit_tax, tax)
    await update.message.reply_text(f"✅ Withdrawn ₹{amount} from bank.\n💸 ₹{tax} collected as tax.\n👜 You received ₹{net}")


async def topbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _topbank_sync():
        with get_conn() as conn:
            return conn.execute("SELECT username, bank FROM users ORDER BY bank DESC LIMIT 10").fetchall()

    rows = await asyncio.to_thread(_topbank_sync)
    if not rows:
        return await update.message.reply_text("📭 No bank data found.")

    lines = ["🏦 Top Bank Balances:"]
    for i, (username, bank) in enumerate(rows, start=1):
        name = f"@{username}" if username else "Unnamed"
        lines.append(f"{i}. {name} — {bank} coins")

    await update.message.reply_text("\n".join(lines))


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_stats = await asyncio.to_thread(get_user_stats, uid)
    savings = await asyncio.to_thread(get_locked_savings, uid)

    await update.message.reply_text(
        f"📊 Your Stats:\n"
        f"💰 Coins: {user_stats['coins']}\n"
        f"🧘 Karma: {user_stats['karma']}\n"
        f"🔒 Locked Savings: {savings} coins"
    )


async def taxbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _taxbank_sync():
        with get_conn() as conn:
            row = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()
            return row[0] if row and row[0] else 0

    total_tax = await asyncio.to_thread(_taxbank_sync)
    await update.message.reply_text(f"🏛️ Total tax collected: {total_tax} coins")


async def taxtop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _taxtop_sync():
        with get_conn() as conn:
            return conn.execute("""
                SELECT u.username, SUM(t.amount) as total
                FROM tax_bank t
                JOIN users u ON t.id = u.id
                GROUP BY u.username
                ORDER BY total DESC
                LIMIT 10
            """).fetchall()

    rows = await asyncio.to_thread(_taxtop_sync)
    if not rows:
        return await update.message.reply_text("📭 No tax data found.")

    lines = ["🏆 Top Tax Contributors:"]
    for i, (username, total) in enumerate(rows, start=1):
        name = f"@{username}" if username else "Unnamed"
        lines.append(f"{i}. {name} — {total} coins")

    await update.message.reply_text("\n".join(lines))


async def createbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("🚫 Only admins can create banks.")

    name = " ".join(context.args)
    if not name:
        return await update.message.reply_text("⚠️ Usage: /createbank <name>")

    def _cb_sync():
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO banks (name, owner_uid, created_at)
                VALUES (?, ?, ?)
            """, (name, uid, int(time.time())))
            conn.commit()

    await asyncio.to_thread(_cb_sync)
    await update.message.reply_text(f"✅ Bank <b>{name}</b> created!", parse_mode="HTML")


async def joinbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    if not args:
        return await update.message.reply_text("⚠️ Usage: /joinbank <bank_id>")

    bank_id = int(args[0])
    entry_fee = 500

    def _jb_sync():
        with get_conn() as conn:
            coins = get_balance(uid)
            if coins < entry_fee:
                return False
            conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (entry_fee, uid))
            conn.execute("INSERT OR REPLACE INTO bank_members (uid, bank_id, joined_at) VALUES (?, ?, ?)", (uid, bank_id, int(time.time())))
            conn.commit()
            return True

    success = await asyncio.to_thread(_jb_sync)
    if not success:
        return await update.message.reply_text("❌ Not enough coins to join a bank.")
    await asyncio.to_thread(deposit_tax, entry_fee)
    await update.message.reply_text(f"✅ Joined bank ID {bank_id}. ₹{entry_fee} collected as tax.")


async def mybank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _mybank_sync():
        with get_conn() as conn:
            return conn.execute("""
                SELECT b.bank_id, b.name, b.owner_uid
                FROM bank_members bm
                JOIN banks b ON bm.bank_id = b.bank_id
                WHERE bm.uid = ?
            """, (uid,)).fetchone()

    row = await asyncio.to_thread(_mybank_sync)
    if not row:
        return await update.message.reply_text("❌ You haven't joined any bank yet.")

    bank_id, name, owner_uid = row
    owner = await asyncio.to_thread(get_username, owner_uid)

    await update.message.reply_text(
        f"🏦 <b>Your Bank</b>\n"
        f"• Name: <b>{name}</b>\n"
        f"• ID: <code>{bank_id}</code>\n"
        f"• Owner: 👑 {owner}",
        parse_mode="HTML"
    )


async def bankinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bank_id = int(context.args[0])
    except:
        return await update.message.reply_text("⚠️ Usage: /bankinfo <bank_id>")

    def _bi_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT name, owner_uid FROM banks WHERE bank_id = ?", (bank_id,)).fetchone()
            if not bank:
                return None, None
            members = conn.execute("SELECT COUNT(*) FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchone()[0]
            return bank, members

    bank, members = await asyncio.to_thread(_bi_sync)
    if bank is None:
        return await update.message.reply_text("❌ Bank not found.")

    await update.message.reply_text(
        f"🏦 <b>{bank[0]}</b>\n👑 Owner: <a href='tg://user?id={bank[1]}'>Admin</a>\n👥 Members: <b>{members}</b>",
        parse_mode="HTML"
    )


async def bankdeposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("⚠️ Usage: /bankdeposit <amount>")

    def _bd_sync():
        with get_conn() as conn:
            user = conn.execute("SELECT coins FROM users WHERE uid = ?", (uid,)).fetchone()
            if not user or user[0] < amount:
                return False
            bank_row = conn.execute("SELECT bank_id FROM bank_members WHERE uid = ?", (uid,)).fetchone()
            if not bank_row:
                return None
            bank_id = bank_row[0]
            conn.execute("UPDATE users SET coins = coins - ? WHERE uid = ?", (amount, uid))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bank_reserves (
                    bank_id INTEGER PRIMARY KEY,
                    coins INTEGER DEFAULT 0
                )
            """)
            conn.execute("INSERT OR IGNORE INTO bank_reserves (bank_id, coins) VALUES (?, 0)", (bank_id,))
            conn.execute("UPDATE bank_reserves SET coins = coins + ? WHERE bank_id = ?", (amount, bank_id))
            conn.commit()
            return True

    result = await asyncio.to_thread(_bd_sync)
    if result is False:
        return await update.message.reply_text("❌ Not enough coins.")
    if result is None:
        return await update.message.reply_text("❌ You haven't joined any bank.")
    await update.message.reply_text(f"✅ Deposited <b>{amount}</b> coins to your bank.", parse_mode="HTML")


async def bankwithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        amount = int(context.args[0])
        if amount <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("⚠️ Usage: /bankwithdraw <amount>")

    def _bw_sync():
        with get_conn() as conn:
            bank_row = conn.execute("SELECT bank_id FROM bank_members WHERE uid = ?", (uid,)).fetchone()
            if not bank_row:
                return False
            bank_id = bank_row[0]
            reserve = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (bank_id,)).fetchone()
            if not reserve or reserve[0] < amount:
                return None
            conn.execute("UPDATE bank_reserves SET coins = coins - ? WHERE bank_id = ?", (amount, bank_id))
            conn.execute("UPDATE users SET coins = coins + ? WHERE uid = ?", (amount, uid))
            conn.commit()
            return True

    result = await asyncio.to_thread(_bw_sync)
    if result is False:
        return await update.message.reply_text("❌ You haven't joined any bank.")
    if result is None:
        return await update.message.reply_text("❌ Bank doesn't have enough coins.")
    await update.message.reply_text(f"💸 Withdrawn <b>{amount}</b> coins from your bank.", parse_mode="HTML")


async def bankrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _br_sync():
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bank_reserves (
                    bank_id INTEGER PRIMARY KEY,
                    coins INTEGER DEFAULT 0
                )
            """)
            return conn.execute("""
                SELECT b.bank_id, b.name, r.coins
                FROM banks b
                LEFT JOIN bank_reserves r ON b.bank_id = r.bank_id
                ORDER BY r.coins DESC
                LIMIT 10
            """).fetchall()

    rows = await asyncio.to_thread(_br_sync)
    if not rows:
        return await update.message.reply_text("📉 No banks with reserves yet.")

    lines = ["🏦 <b>Top Banks</b>"]
    for i, (bank_id, name, coins) in enumerate(rows, 1):
        coins = coins or 0
        lines.append(f"{i}. <b>{name}</b> — 💰 {coins} coins (ID: {bank_id})")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def bankdashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _bdash_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT bank_id, name FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
            if not bank:
                return None
            bank_id, name = bank
            members = conn.execute("SELECT COUNT(*) FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchone()[0]
            coins = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (bank_id,)).fetchone()
            coins = coins[0] if coins else 0
            return bank_id, name, members, coins

    result = await asyncio.to_thread(_bdash_sync)
    if result is None:
        return await update.message.reply_text("❌ You don't own any bank.")

    bank_id, name, members, coins = result
    await update.message.reply_text(
        f"📊 <b>Bank Dashboard</b>\n🏦 Name: <b>{name}</b>\n👥 Members: <b>{members}</b>\n💰 Reserve: <b>{coins}</b> coins",
        parse_mode="HTML"
    )


async def transferbank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        to_bank_id = int(context.args[0])
        amount = int(context.args[1])
        if amount <= 0:
            raise ValueError
    except:
        return await update.message.reply_text("⚠️ Usage: /transferbank <to_bank_id> <amount>")

    def _tb_sync():
        with get_conn() as conn:
            from_bank = conn.execute("SELECT bank_id FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
            if not from_bank:
                return None, None
            from_bank_id = from_bank[0]
            from_reserve = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (from_bank_id,)).fetchone()
            if not from_reserve or from_reserve[0] < amount:
                return None, None
            target = conn.execute("SELECT name FROM banks WHERE bank_id = ?", (to_bank_id,)).fetchone()
            if not target:
                return None, None
            conn.execute("UPDATE bank_reserves SET coins = coins - ? WHERE bank_id = ?", (amount, from_bank_id))
            conn.execute("INSERT OR IGNORE INTO bank_reserves (bank_id, coins) VALUES (?, 0)", (to_bank_id,))
            conn.execute("UPDATE bank_reserves SET coins = coins + ? WHERE bank_id = ?", (amount, to_bank_id))
            conn.commit()
            return target[0], to_bank_id

    target_name, final_bank_id = await asyncio.to_thread(_tb_sync)
    if target_name is None:
        return await update.message.reply_text("❌ Transfer failed. Check your bank or target bank ID.")
    await update.message.reply_text(
        f"🔁 Transferred <b>{amount}</b> coins to <b>{target_name}</b> (ID: {final_bank_id})",
        parse_mode="HTML"
    )


async def bankmembers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bank_id = int(context.args[0])
    except:
        return await update.message.reply_text("⚠️ Usage: /bankmembers <bank_id>")

    def _bm_sync():
        with get_conn() as conn:
            return conn.execute("SELECT uid FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchall()

    rows = await asyncio.to_thread(_bm_sync)
    if not rows:
        return await update.message.reply_text("❌ No members found in this bank.")

    lines = [f"👥 <b>Members of Bank ID {bank_id}</b>"]
    for uid_row in rows:
        uid = uid_row[0]
        lines.append(f"• <a href='tg://user?id={uid}'>User</a>")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def deletebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        bank_id = int(context.args[0])
    except:
        return await update.message.reply_text("⚠️ Usage: /deletebank <bank_id>")

    def _db_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT owner_uid FROM banks WHERE bank_id = ?", (bank_id,)).fetchone()
            if not bank:
                return "not_found"
            if bank[0] != uid:
                return "not_owner"
            conn.execute("DELETE FROM banks WHERE bank_id = ?", (bank_id,))
            conn.execute("DELETE FROM bank_members WHERE bank_id = ?", (bank_id,))
            conn.execute("DELETE FROM bank_reserves WHERE bank_id = ?", (bank_id,))
            conn.execute("DELETE FROM bank_logs WHERE bank_id = ?", (bank_id,))
            conn.commit()
            return "ok"

    result = await asyncio.to_thread(_db_sync)
    if result == "not_found":
        return await update.message.reply_text("❌ Bank not found.")
    if result == "not_owner":
        return await update.message.reply_text("🚫 You don't own this bank.")
    await update.message.reply_text(f"🗑️ Bank ID <b>{bank_id}</b> deleted.", parse_mode="HTML")


async def banklog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _blog_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT bank_id FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
            if not bank:
                return None, None
            bank_id = bank[0]
            logs = conn.execute("""
                SELECT uid, action, amount, timestamp FROM bank_logs
                WHERE bank_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (bank_id,)).fetchall()
            return bank_id, logs

    bank_id, logs = await asyncio.to_thread(_blog_sync)
    if bank_id is None:
        return await update.message.reply_text("❌ You don't own any bank.")
    if not logs:
        return await update.message.reply_text("📭 No recent transactions.")

    lines = [f"📜 <b>Recent Transactions for Bank ID {bank_id}</b>"]
    for uid_row, action, amount, ts in logs:
        time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))
        lines.append(f"• <b>{action.title()}</b> — <code>{amount}</code> coins by <a href='tg://user?id={uid_row}'>User</a> at {time_str}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def bankstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _bstats_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT bank_id, name FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
            if not bank:
                return None
            bank_id, name = bank
            members = conn.execute("SELECT COUNT(*) FROM bank_members WHERE bank_id = ?", (bank_id,)).fetchone()[0]
            coins = conn.execute("SELECT coins FROM bank_reserves WHERE bank_id = ?", (bank_id,)).fetchone()
            coins = coins[0] if coins else 0
            deposits = conn.execute("""
                SELECT SUM(amount) FROM bank_logs WHERE bank_id = ? AND action = 'deposit'
            """, (bank_id,)).fetchone()[0] or 0
            withdrawals = conn.execute("""
                SELECT SUM(amount) FROM bank_logs WHERE bank_id = ? AND action = 'withdraw'
            """, (bank_id,)).fetchone()[0] or 0
            return name, members, coins, deposits, withdrawals

    result = await asyncio.to_thread(_bstats_sync)
    if result is None:
        return await update.message.reply_text("❌ You don't own any bank.")

    name, members, coins, deposits, withdrawals = result
    await update.message.reply_text(
        f"📊 <b>Bank Stats</b>\n🏦 Name: <b>{name}</b>\n👥 Members: <b>{members}</b>\n💰 Reserve: <b>{coins}</b>\n📥 Deposits: <b>{deposits}</b>\n📤 Withdrawals: <b>{withdrawals}</b>",
        parse_mode="HTML"
    )


async def bankinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _bi_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT bank_id, name FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
            return bank

    bank = await asyncio.to_thread(_bi_sync)
    if not bank:
        return await update.message.reply_text("❌ You don't own any bank.")

    invite_link = f"https://t.me/{context.bot.username}?start=joinbank_{bank[0]}"
    await update.message.reply_text(
        f"🔗 <b>Bank Invite Link</b>\nShare this to invite users to your bank:\n{invite_link}",
        parse_mode="HTML"
    )


async def bankaudit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _baudit_sync():
        with get_conn() as conn:
            bank = conn.execute("SELECT bank_id FROM banks WHERE owner_uid = ?", (uid,)).fetchone()
            if not bank:
                return None, None
            bank_id = bank[0]
            logs = conn.execute("""
                SELECT uid, action, amount, timestamp FROM bank_logs
                WHERE bank_id = ? AND amount >= 1000
                ORDER BY timestamp DESC
                LIMIT 10
            """, (bank_id,)).fetchall()
            return bank_id, logs

    bank_id, logs = await asyncio.to_thread(_baudit_sync)
    if bank_id is None:
        return await update.message.reply_text("❌ You don't own any bank.")
    if not logs:
        return await update.message.reply_text("✅ No suspicious activity detected.")

    lines = [f"🕵️ <b>Audit Log for Bank ID {bank_id}</b>"]
    for uid_row, action, amount, ts in logs:
        time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))
        lines.append(f"• <b>{action.title()}</b> — <code>{amount}</code> coins by <a href='tg://user?id={uid_row}'>User</a> at {time_str}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def banklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _blist_sync():
        with get_conn() as conn:
            return conn.execute("""
                SELECT bank_id, name, owner_uid FROM banks
                ORDER BY bank_id ASC
            """).fetchall()

    rows = await asyncio.to_thread(_blist_sync)
    if not rows:
        return await update.message.reply_text("📭 No banks have been created yet.")

    lines = ["🏦 <b>Available Banks</b>\n💸 Joining a bank costs <b>500 coins</b>."]
    for bank_id, name, owner_uid in rows:
        owner = await asyncio.to_thread(get_username, owner_uid)
        lines.append(
            f"• <b>{name}</b> (ID: {bank_id}) — 👑 {owner}\n"
            f"↪️ <code>/joinbank {bank_id}</code>"
        )

    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")


async def leavebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _lb_sync():
        with get_conn() as conn:
            row = conn.execute("""
                SELECT bm.bank_id, b.name
                FROM bank_members bm
                JOIN banks b ON bm.bank_id = b.bank_id
                WHERE bm.uid = ?
            """, (uid,)).fetchone()
            if not row:
                return None
            bank_id, bank_name = row
            savings = get_bank_balance(uid)
            return bank_id, bank_name, savings

    result = await asyncio.to_thread(_lb_sync)
    if result is None:
        return await update.message.reply_text("⚠️ You're not part of any bank.")

    bank_id, bank_name, savings = result
    await update.message.reply_text(
        f"🏦 <b>Bank:</b> {bank_name} (ID: {bank_id})\n"
        f"💰 <b>Your Bank Balance:</b> {savings} coins\n\n"
        f"⚠️ If you leave this bank:\n"
        f"• Your savings will be deleted\n"
        f"• The coins will be collected as tax\n"
        f"• You cannot recover them later\n\n"
        f"👉 To confirm, type <code>/confirmleavebank</code>",
        parse_mode="HTML"
    )


async def confirmleavebank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    def _clb_sync():
        with get_conn() as conn:
            row = conn.execute("SELECT bank_id FROM bank_members WHERE uid = ?", (uid,)).fetchone()
            if not row:
                return None
            savings = get_bank_balance(uid)
            if savings > 0:
                deposit_tax(savings)
            conn.execute("DELETE FROM bank_members WHERE uid = ?", (uid,))
            set_bank(uid, 0)
            conn.commit()
            return savings

    savings = await asyncio.to_thread(_clb_sync)
    if savings is None:
        return await update.message.reply_text("⚠️ You're not part of any bank.")

    await update.message.reply_text(
        f"✅ You've left your bank.\n💸 {savings} coins were collected as tax.\nYou can join another bank using /banklist.",
        parse_mode="HTML"
    )
