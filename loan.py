import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, ContextTypes
from telegram.constants import ParseMode
from database import get_conn, db_lock, get_balance, update_balance, is_bot_admin

INTEREST_RATE = 0.07
LOAN_DURATION_HOURS = 24
DAILY_DEDUCTION_DAYS = 3

async def loan(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    args = context.args

    if len(args) != 1 or not args[0].isdigit():
        return await update.message.reply_text("⚠️ Usage: /loan <amount>")

    amount = int(args[0])

    if amount > 1_000_000:
        return await update.message.reply_text(
            "🚫 Loan amount exceeds the maximum limit of ₹1,000,000.\nTry a smaller amount to stay within ritual bounds.\n(Autat me 🌚)"
        )

    with db_lock:
        with get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            row = conn.execute("SELECT total_due FROM loans WHERE id = ? AND repaid = 0", (uid,)).fetchone()
            if row:
                due = row["total_due"]
                return await update.message.reply_text(
                    f"❌ You already have an active loan of ₹{due:,}.\nRepay it first using /rloan before requesting another."
                )

            conn.execute("DELETE FROM loans WHERE id = ?", (uid,))

            interest = round(amount * INTEREST_RATE)
            total_due = amount + interest
            now = datetime.utcnow()

            conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, uid))
            conn.execute("""
                INSERT INTO loans (id, amount, interest, total_due, loan_time, repaid, daily_deduction_started, last_deduction_time)
                VALUES (?, ?, ?, ?, ?, 0, 0, NULL)
            """, (uid, amount, interest, total_due, now))
            conn.commit()

    return await update.message.reply_text(
        f"✅ *Loan Approved*\n"
        f"Amount: ₹{amount:,}\n"
        f"Interest: ₹{interest:,}\n"
        f"Total Due: ₹{total_due:,}\n\n"
        f"Repay within 24h using /rloan — every coin is part of your legacy.",
        parse_mode=ParseMode.MARKDOWN
    )


async def repay_loan(update: Update, context: CallbackContext):
    uid = update.effective_user.id

    with db_lock:
        with get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            loan = conn.execute("SELECT * FROM loans WHERE id = ? AND repaid = 0", (uid,)).fetchone()
            if not loan:
                return await update.message.reply_text("❌ No active loan found.")

            balance = await asyncio.to_thread(get_balance, uid)
            if balance < loan["total_due"]:
                return await update.message.reply_text("❌ Insufficient balance to repay.")

            conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (loan["total_due"], uid))
            conn.execute("UPDATE loans SET repaid = 1 WHERE id = ?", (uid,))
            conn.commit()

    return await update.message.reply_text(f"✅ Loan repaid\nTotal Paid: ₹{loan['total_due']}")


def run_daily_deductions():
    with db_lock:
        with get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=LOAN_DURATION_HOURS)
            overdue = conn.execute(
                "SELECT id, amount FROM loans WHERE repaid = 0 AND loan_time < ? AND daily_deduction_started = 0",
                (cutoff.isoformat()[:19],),
            ).fetchall()
            for row in overdue:
                uid = row["id"]
                bal = get_balance(uid)
                ded = min(bal, int(row["amount"] * 0.1))
                if ded > 0:
                    conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (ded, uid))
                conn.execute(
                    "UPDATE loans SET daily_deduction_started = 1, last_deduction_time = ? WHERE id = ?",
                    (now.isoformat()[:19], uid),
                )
            conn.commit()
            return len(overdue)


async def my_loan(update: Update, context: CallbackContext):
    uid = update.effective_user.id

    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        loan = conn.execute("SELECT * FROM loans WHERE id = ?", (uid,)).fetchone()
        if not loan:
            return await update.message.reply_text("❌ You have no loan history.")

        loan_time_str = loan["loan_time"]
        loan_time = None
        formats_to_try = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%d-%m-%Y %H:%M",
        ]

        for fmt in formats_to_try:
            try:
                loan_time = datetime.strptime(loan_time_str, fmt)
                break
            except ValueError:
                continue

        if loan_time is None:
            return await update.message.reply_text(f"⚠️ Invalid loan_time format: {loan_time_str}")

        time_left = max(0, int((loan_time + timedelta(hours=LOAN_DURATION_HOURS) - datetime.utcnow()).total_seconds() // 3600))

        status = "✅ Repaid" if loan["repaid"] else "❌ Unpaid"
        deduction = "Started" if loan["daily_deduction_started"] else "Not started"

    return await update.message.reply_text(
        f"📜 Loan Status:\n"
        f"Amount: ₹{loan['amount']}\n"
        f"Interest: ₹{loan['interest']}\n"
        f"Total Due: ₹{loan['total_due']}\n"
        f"Time Left: {time_left}h\n"
        f"Status: {status}\n"
        f"Daily Deduction: {deduction}"
    )


async def top_loans(update: Update, context: CallbackContext):
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        rows = conn.execute(
            "SELECT id, total_due FROM loans WHERE repaid = 0 ORDER BY total_due DESC LIMIT 10"
        ).fetchall()

        if not rows:
            return await update.message.reply_text("No active loans found.")

        leaderboard = "🏦 *Top Loans:*\n"
        for i, row in enumerate(rows, start=1):
            uid = row["id"]
            due = row["total_due"]
            due_str = f"{due:,}"

            try:
                user = await context.bot.get_chat(uid)

                if user.username:
                    display_name = f"@{user.username}"
                else:
                    raw_name = user.first_name or f"UID {uid}"
                    safe_name = (
                        raw_name
                        .replace("_", "\\_")
                        .replace("*", "\\*")
                        .replace("[", "\\[")
                        .replace("]", "\\]")
                        .replace("(", "\\(")
                        .replace(")", "\\)")
                    )
                    display_name = f"[{safe_name}](tg://user?id={uid})"

            except Exception:
                display_name = f"[UID {uid}](tg://user?id={uid})"

            leaderboard += f"{i}. {display_name} → Due: ₹{due_str}\n"

        return await update.message.reply_text(leaderboard, parse_mode=ParseMode.MARKDOWN)


async def deduct_command(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not is_bot_admin(uid):
        return await update.message.reply_text("❌ You are not authorized to run this command.")

    count = await asyncio.to_thread(run_daily_deductions)
    await update.message.reply_text(f"✅ Daily deductions processed for {count} overdue loans.")


async def resetloan(update: Update, context: CallbackContext):
    admin_id = update.effective_user.id

    if not is_bot_admin(admin_id):
        return await update.message.reply_text("🚫 You are not authorized to perform this ritual.")

    if update.message.reply_to_message:
        target_uid = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        target_uid = int(context.args[0])
    else:
        return await update.message.reply_text("⚠️ Usage: /resetloan <uid> or reply to a user.")

    with db_lock:
        with get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            affected = conn.execute(
                "UPDATE loans SET repaid = 1 WHERE id = ? AND repaid = 0", (target_uid,)
            ).rowcount
            conn.commit()

    if affected:
        await update.message.reply_text(
            f"✅ Loan for UID {target_uid} has been reset.\nThe path is clear for a new request."
        )
    else:
        await update.message.reply_text(
            f"ℹ️ No active loan found for UID {target_uid}.\nNothing to reset."
        )
