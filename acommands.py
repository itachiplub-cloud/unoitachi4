import sys
import os
import time
import json
import asyncio
import psutil
import platform
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# =========================================================
# LOAD CONFIGURATION
# =========================================================

from database import is_bot_admin

def get_logger_chat_id():
    """Get logger chat ID from logger.py."""
    try:
        from logger import LOGGER_GC_ID
        return LOGGER_GC_ID
    except ImportError:
        print("⚠️ Could not import LOGGER_GC_ID from logger.py")
        return None
    except Exception as e:
        print(f"⚠️ Error getting logger ID: {e}")
        return None

# Global variables
LOGGER_GC_ID = get_logger_chat_id()
BOT_START_TIME = datetime.now()

# Command statistics
command_stats = {
    'total_commands': 0,
    'restart_count': 0,
    'status_count': 0,
    'health_count': 0
}

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_number(num):
    """Format number with commas."""
    if num is None:
        return "0"
    return f"{num:,}"

def get_uptime():
    """Get bot uptime string."""
    delta = datetime.now() - BOT_START_TIME
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)

async def get_bot_statistics(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Collect bot statistics from SQLite database."""
    from database import get_conn, get_ref_reward, get_tax_pool
    
    stats = {}
    
    # Get current time
    current_time = datetime.now()
    start_time = context.bot_data.get('start_time', BOT_START_TIME)
    stats['start_time_str'] = start_time.strftime("%Y-%m-%d %H:%M:%S")
    stats['current_time'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate uptime
    uptime_delta = current_time - start_time
    days = uptime_delta.days
    hours = uptime_delta.seconds // 3600
    minutes = (uptime_delta.seconds % 3600) // 60
    seconds = uptime_delta.seconds % 60
    
    uptime_parts = []
    if days > 0:
        uptime_parts.append(f"{days}d")
    if hours > 0:
        uptime_parts.append(f"{hours}h")
    if minutes > 0:
        uptime_parts.append(f"{minutes}m")
    uptime_parts.append(f"{seconds}s")
    stats['uptime'] = " ".join(uptime_parts)
    
    # Get database statistics
    def _fetch_db_stats():
        with get_conn() as conn:
            result = {}
            user_row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            result['total_users'] = user_row[0] if user_row else 0

            group_row = conn.execute("SELECT COUNT(*) FROM groups").fetchone()
            result['total_groups'] = group_row[0] if group_row else 0

            active_row = conn.execute(
                "SELECT COUNT(*) FROM users WHERE last_active >= ?",
                (int(time.time()) - 86400,)
            ).fetchone()
            result['active_users'] = active_row[0] if active_row else 0

            today_start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
            new_row = conn.execute(
                "SELECT COUNT(*) FROM users WHERE last_active >= ?",
                (today_start,)
            ).fetchone()
            result['new_users_today'] = new_row[0] if new_row else 0

            coins_row = conn.execute("SELECT SUM(coins) FROM users").fetchone()
            result['total_coins'] = coins_row[0] if coins_row and coins_row[0] else 0

            tax_row = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()
            result['total_tax'] = tax_row[0] if tax_row and tax_row[0] else 0

            bank_row = conn.execute("SELECT SUM(bank) FROM users").fetchone()
            result['total_bank'] = bank_row[0] if bank_row and bank_row[0] else 0

            if result['total_users'] > 0:
                result['avg_balance'] = result['total_coins'] // result['total_users']
            else:
                result['avg_balance'] = 0

            richest_row = conn.execute(
                "SELECT username, coins FROM users ORDER BY coins DESC LIMIT 1"
            ).fetchone()
            if richest_row:
                result['richest_user'] = richest_row[1] if richest_row[1] else 0
                result['richest_name'] = richest_row[0] if richest_row[0] else "Unknown"
            else:
                result['richest_user'] = 0
                result['richest_name'] = "N/A"

            top_users = conn.execute(
                "SELECT username, coins FROM users ORDER BY coins DESC LIMIT 5"
            ).fetchall()
            result['top_5_users'] = [(row[0] or "Unknown", row[1] or 0) for row in top_users]

            card_row = conn.execute("SELECT COUNT(*) FROM deck").fetchone()
            result['total_cards'] = card_row[0] if card_row else 0

            owned_row = conn.execute("SELECT COUNT(*) FROM user_cards").fetchone()
            result['total_owned_cards'] = owned_row[0] if owned_row else 0

            duel_row = conn.execute("SELECT SUM(wins + losses + draws) FROM duel_stats").fetchone()
            result['total_duels'] = duel_row[0] if duel_row and duel_row[0] else 0

            bank_count_row = conn.execute("SELECT COUNT(*) FROM banks").fetchone()
            result['total_banks'] = bank_count_row[0] if bank_count_row else 0

            member_row = conn.execute("SELECT COUNT(*) FROM bank_members").fetchone()
            result['total_bank_members'] = member_row[0] if member_row else 0

            reserve_row = conn.execute("SELECT SUM(coins) FROM bank_reserves").fetchone()
            result['total_bank_reserves'] = reserve_row[0] if reserve_row and reserve_row[0] else 0

            ref_row = conn.execute("SELECT COUNT(*) FROM referrals").fetchone()
            result['total_referrals'] = ref_row[0] if ref_row else 0

            result['ref_reward'] = get_ref_reward()
            result['total_tax_pool'] = get_tax_pool()
        return result

    db_stats = await asyncio.to_thread(_fetch_db_stats)
    stats.update(db_stats)
    
    # System statistics
    try:
        stats['cpu_percent'] = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        stats['memory_percent'] = memory.percent
        stats['ram_used'] = round(memory.used / (1024 * 1024), 2)
        stats['ram_total'] = round(memory.total / (1024 * 1024), 2)
        
        # Disk usage
        disk = psutil.disk_usage('.')
        stats['disk_percent'] = disk.percent
        stats['disk_used'] = round(disk.used / (1024 * 1024 * 1024), 2)
        stats['disk_total'] = round(disk.total / (1024 * 1024 * 1024), 2)
        
        stats['python_version'] = platform.python_version()
        stats['platform'] = platform.system()
        stats['platform_release'] = platform.release()
    except Exception as e:
        print(f"⚠️ Error getting system stats: {e}")
        stats['cpu_percent'] = 0
        stats['memory_percent'] = 0
        stats['ram_used'] = 0
        stats['ram_total'] = 0
        stats['disk_percent'] = 0
        stats['disk_used'] = 0
        stats['disk_total'] = 0
        stats['python_version'] = platform.python_version()
        stats['platform'] = platform.system()
        stats['platform_release'] = "Unknown"
    
    return stats


def register_admin_commands(application):
    print("✅ Admin commands registered")
# =========================================================
# BOT RESTART COMMAND (Admin Only)
# =========================================================

async def bot_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the bot - Admin only command (Direct restart, no confirmation)."""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not is_bot_admin(user_id):
        await update.message.reply_text(
            "❌ <b>Access Denied!</b>\n\n"
            "This command is only available for bot administrators.",
            parse_mode="HTML"
        )
        return
    
    # Send restart message
    await update.message.reply_text(
        f"🔄 <b>Bot is restarting...</b>\n\n"
        f"Please wait a few seconds.\n"
        f"The bot will reconnect automatically.\n\n"
        f"⏰ Restart initiated at: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
        f"👤 Requested by: <code>{update.effective_user.first_name}</code>",
        parse_mode="HTML"
    )
    
    # Send restart notification to logger group (optional)
    if LOGGER_GC_ID:
        try:
            await context.bot.send_message(
                chat_id=LOGGER_GC_ID,
                text=f"🔴 <b>BOT RESTART INITIATED</b>\n\n"
                     f"👤 Admin: <code>{update.effective_user.first_name}</code>\n"
                     f"⏰ Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                     f"🆔 User ID: <code>{user_id}</code>",
                parse_mode="HTML"
            )
        except:
            pass
    
    # Perform restart
    await asyncio.sleep(2)
    os.execl(sys.executable, sys.executable, *sys.argv)
# =========================================================
# BOT STATUS COMMAND (Admin Only)
# =========================================================

async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display full bot statistics - Admin only command."""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not is_bot_admin(user_id):
        await update.message.reply_text(
            "❌ <b>Access Denied!</b>\n\n"
            "This command is only available for bot administrators.",
            parse_mode="HTML"
        )
        return
    
    command_stats['status_count'] += 1
    command_stats['total_commands'] += 1
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Collect statistics
    stats = await get_bot_statistics(context)
    
    # Create top 5 users text
    top_users_text = ""
    for i, (name, coins) in enumerate(stats['top_5_users'], 1):
        top_users_text += f"{i}. <code>{name}</code> — ₹{format_number(coins)}\n"
    
    # Create stats message
    stats_message = f"""
📊 <b>BOT FULL STATUS REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>BOT INFORMATION</b>
• Bot Name: <code>{context.bot.first_name}</code>
• Bot Username: @{context.bot.username}
• Bot ID: <code>{context.bot.id}</code>
• Uptime: <code>{stats['uptime']}</code>
• Started: <code>{stats['start_time_str']}</code>

👥 <b>USER STATISTICS</b>
• Total Users: <code>{format_number(stats['total_users'])}</code>
• Total Groups: <code>{format_number(stats['total_groups'])}</code>
• Active Users (24h): <code>{format_number(stats['active_users'])}</code>
• New Users (Today): <code>{format_number(stats['new_users_today'])}</code>

💰 <b>ECONOMY STATISTICS</b>
• Total Coins: <code>₹{format_number(stats['total_coins'])}</code>
• Total Bank Balance: <code>₹{format_number(stats['total_bank'])}</code>
• Average Balance: <code>₹{format_number(stats['avg_balance'])}</code>
• Richest User: <code>{stats['richest_name']}</code> (₹{format_number(stats['richest_user'])})
• Tax Pool: <code>₹{format_number(stats['total_tax_pool'])}</code>
• Referral Reward: <code>₹{stats['ref_reward']}</code>

🏆 <b>TOP 5 RICHEST USERS</b>
{top_users_text}

🎴 <b>CARD & GAME STATISTICS</b>
• Total Cards in Deck: <code>{format_number(stats['total_cards'])}</code>
• Total Cards Owned: <code>{format_number(stats['total_owned_cards'])}</code>
• Total Duels Fought: <code>{format_number(stats['total_duels'])}</code>
• Total Referrals: <code>{format_number(stats['total_referrals'])}</code>

🏦 <b>BANK SYSTEM STATISTICS</b>
• Total Banks Created: <code>{format_number(stats['total_banks'])}</code>
• Total Bank Members: <code>{format_number(stats['total_bank_members'])}</code>
• Total Bank Reserves: <code>₹{format_number(stats['total_bank_reserves'])}</code>

💻 <b>SYSTEM STATISTICS</b>
• CPU Usage: <code>{stats['cpu_percent']}%</code>
• RAM Usage: <code>{stats['memory_percent']}%</code>
• RAM Used: <code>{stats['ram_used']} MB</code> / <code>{stats['ram_total']} MB</code>
• Disk Usage: <code>{stats['disk_percent']}%</code>
• Disk Used: <code>{stats['disk_used']} GB</code> / <code>{stats['disk_total']} GB</code>

📦 <b>ENVIRONMENT</b>
• Python Version: <code>{stats['python_version']}</code>
• Platform: <code>{stats['platform']} {stats['platform_release']}</code>

📈 <b>COMMAND USAGE</b>
• Total Admin Commands: <code>{command_stats['total_commands']}</code>
• Restarts: <code>{command_stats['restart_count']}</code>
• Status Checks: <code>{command_stats['status_count']}</code>
• Health Checks: <code>{command_stats['health_count']}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 <i>Report generated: {stats['current_time']}</i>
"""
    
    # Add inline buttons for admin actions
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
            InlineKeyboardButton("📊 Full Report", callback_data="full_stats_report")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="admin_leaderboard"),
            InlineKeyboardButton("💰 Tax Pool", callback_data="admin_tax_pool")
        ],
        [
            InlineKeyboardButton("📜 Transfer Logs", callback_data="admin_transfer_logs"),
            InlineKeyboardButton("🔄 Restart Bot", callback_data="admin_restart")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send stats message
    await update.message.reply_text(
        stats_message,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def status_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle status menu callback buttons."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin
    if not is_bot_admin(user_id):
        await query.edit_message_text(
            "❌ <b>Access Denied!</b>\n\n"
            "You are not authorized to use admin features.",
            parse_mode="HTML"
        )
        return
    
    if query.data == "refresh_status":
        # Refresh stats
        await query.edit_message_text("🔄 Refreshing statistics...", parse_mode="HTML")
        stats = await get_bot_statistics(context)
        
        stats_message = f"""
📊 <b>BOT STATISTICS (Updated)</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 <b>Users:</b> <code>{format_number(stats['total_users'])}</code>
💬 <b>Groups:</b> <code>{format_number(stats['total_groups'])}</code>
💰 <b>Total Coins:</b> <code>₹{format_number(stats['total_coins'])}</code>
🏦 <b>Tax Pool:</b> <code>₹{format_number(stats['total_tax_pool'])}</code>
🕐 <b>Uptime:</b> <code>{stats['uptime']}</code>

⏰ <i>Updated: {stats['current_time']}</i>
"""
        await query.edit_message_text(stats_message, parse_mode="HTML")
        
    elif query.data == "full_stats_report":
        stats = await get_bot_statistics(context)
        
        report = f"""
📋 <b>FULL BOT REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 <b>USAGE STATISTICS</b>
• Total Admin Commands: <code>{command_stats['total_commands']}</code>
• Bot Uptime: <code>{stats['uptime']}</code>

💎 <b>TOP STATISTICS</b>
• Richest User: <code>{stats['richest_name']}</code>
• Richest Balance: <code>₹{format_number(stats['richest_user'])}</code>
• Total Cards: <code>{format_number(stats['total_cards'])}</code>
• Total Users: <code>{format_number(stats['total_users'])}</code>

━━━━━━━━━━━━━━━━━━━━━━
📅 <i>Report generated: {stats['current_time']}</i>
"""
        await query.edit_message_text(report, parse_mode="HTML")
        
    elif query.data == "admin_restart":
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data="confirm_restart"),
                InlineKeyboardButton("❌ No", callback_data="cancel_restart")
            ]
        ]
        await query.edit_message_text(
            "⚠️ <b>Confirm Bot Restart?</b>\n\n"
            "This will restart the bot immediately.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif query.data == "admin_leaderboard":
        from database import get_conn
        def _fetch_leaderboard():
            with get_conn() as conn:
                return conn.execute(
                    "SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10"
                ).fetchall()
        top_users = await asyncio.to_thread(_fetch_leaderboard)
        
        leaderboard = "🏆 <b>TOP 10 RICHEST USERS</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, row in enumerate(top_users, 1):
            username = row[0] if row[0] else f"User {i}"
            coins = row[1] if row[1] else 0
            leaderboard += f"{i}. {username} — <code>₹{format_number(coins)}</code>\n"
        
        await query.edit_message_text(leaderboard, parse_mode="HTML")
        
    elif query.data == "admin_tax_pool":
        from database import get_tax_pool
        tax_pool = get_tax_pool()
        await query.edit_message_text(
            f"💰 <b>TAX POOL BALANCE</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Total Tax Collected: <code>₹{format_number(tax_pool)}</code>\n\n"
            f"💡 Use <code>/distributetax</code> to distribute to top users.",
            parse_mode="HTML"
        )
        
    elif query.data == "admin_transfer_logs":
        from database import get_transfer_logs
        logs = get_transfer_logs(limit=10)
        
        if not logs:
            await query.edit_message_text("📭 No recent transfers found.", parse_mode="HTML")
            return
        
        log_text = "📜 <b>RECENT TRANSFERS (Last 10)</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for sender, receiver, amount, ts in logs:
            time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            log_text += f"💸 {sender} → {receiver}: <code>₹{format_number(amount)}</code> <i>({time_str})</i>\n"
        
        await query.edit_message_text(log_text, parse_mode="HTML")

# =========================================================
# BOT HEALTH CHECK COMMAND (Admin Only)
# =========================================================

async def bot_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot health - Admin only command."""
    user_id = update.effective_user.id
    
    if not is_bot_admin(user_id):
        await update.message.reply_text(
            "❌ <b>Access Denied!</b>",
            parse_mode="HTML"
        )
        return
    
    command_stats['health_count'] += 1
    command_stats['total_commands'] += 1
    
    # Check database connection
    db_status = "✅ Connected"
    db_details = ""
    try:
        from database import get_conn
        with get_conn() as conn:
            conn.execute("SELECT 1")
            # Get database size
            import os
            if os.path.exists("uno.db"):
                size = os.path.getsize("uno.db") / (1024 * 1024)
                db_details = f"\n• DB Size: <code>{size:.2f} MB</code>"
    except Exception as e:
        db_status = f"❌ Error: {str(e)[:50]}"
    
    # Check bot status
    health_message = f"""
🩺 <b>BOT HEALTH CHECK</b>
━━━━━━━━━━━━━━━━━━━━━━

📡 <b>Bot Status:</b> 🟢 Online
💾 <b>Database:</b> {db_status}{db_details}
🔄 <b>Uptime:</b> <code>{get_uptime()}</code>
⏰ <b>Current Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>

✅ <b>All systems operational</b>
"""
    
    await update.message.reply_text(health_message, parse_mode="HTML")

# =========================================================
# REGISTER HANDLERS (Add these to your main.py)
# =========================================================

"""
# Add these lines to your main.py after creating the application:

from admin_commands import bot_restart, bot_status, bot_health
from admin_commands import restart_callback_handler, status_callback_handler

# Command handlers
application.add_handler(CommandHandler("restart", bot_restart))
application.add_handler(CommandHandler("bstatus", bot_status))
application.add_handler(CommandHandler("health", bot_health))

# Callback handlers
application.add_handler(CallbackQueryHandler(restart_callback_handler, pattern="^(confirm_restart|cancel_restart)$"))
application.add_handler(CallbackQueryHandler(status_callback_handler, pattern="^(refresh_status|full_stats_report|admin_restart|admin_leaderboard|admin_tax_pool|admin_transfer_logs)$"))

# Set start time in bot_data (add this in your start callback or on startup)
context.bot_data['start_time'] = datetime.now()

# Update command_stats in your main.py if you want to track total commands
# context.bot_data['total_commands'] = command_stats['total_commands']
"""

# =========================================================
# COMMAND USAGE
# =========================================================

"""
Commands for Admins (HTML formatted):

/restart  - Restart the bot with confirmation dialog
/bstatus  - View full bot statistics (users, coins, cards, banks, system)
/health   - Quick health check (database, uptime, status)

All responses use HTML parse_mode with proper formatting,
emoji icons, and code blocks for better readability.
"""