import time
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Update, User, Chat
from telegram.ext import ContextTypes

# =========================================================
# LOGGER CONFIGURATION
# =========================================================

from config import LOGGER_GROUP_ID
ENABLE_LOGGING = True  # Master switch for logging
ENABLE_DEBUG_LOGS = False  # Enable debug-level logging

# Setup logging to file as backup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_logs.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_timestamp(timestamp: int = None) -> str:
    """Format timestamp for consistent display."""
    if timestamp is None:
        timestamp = int(time.time())
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram markdown."""
    if not text:
        return "None"
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def safe_send_message(client, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Safely send a message with error handling."""
    try:
        await client.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except Exception as e:
        logger.error(f"Failed to send log message: {e}")
        # Try without parse_mode if HTML fails
        try:
            await client.send_message(chat_id=chat_id, text=text, parse_mode=None)
            return True
        except Exception as e2:
            logger.error(f"Failed to send log message even without parse_mode: {e2}")
            return False

# =========================================================
# MAIN LOGGER FUNCTIONS
# =========================================================

async def send_alive_logger(client, bot_name: str = "Itachi Bot"):
    """Send a message to the logger channel when the bot comes online."""
    if not ENABLE_LOGGING:
        return
    
    uptime_text = f"""
🔥 <b>BOT IS NOW ONLINE</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: {escape_markdown(bot_name)}
⏰ Time: <code>{format_timestamp()}</code>
⚡ Status: <b>🟢 ACTIVE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, uptime_text)
    logger.info(f"Bot online notification sent to {LOGGER_GROUP_ID}")

async def send_shutdown_logger(client, bot_name: str = "Itachi Bot"):
    """Send a message when the bot shuts down."""
    if not ENABLE_LOGGING:
        return
    
    shutdown_text = f"""
🔴 <b>BOT IS SHUTTING DOWN</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: {escape_markdown(bot_name)}
⏰ Time: <code>{format_timestamp()}</code>
⚡ Status: <b>🔴 OFFLINE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, shutdown_text)
    logger.info(f"Bot shutdown notification sent to {LOGGER_GROUP_ID}")

async def send_start_logger(client, user: User):
    """Log when a new user starts interacting with the bot."""
    if not ENABLE_LOGGING:
        return
    
    # Check if user is new (you may want to implement this check)
    user_text = f"""
🚀 <b>USER STARTED BOT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Name: {escape_markdown(user.full_name or 'Unknown')}
🆔 User ID: <code>{user.id}</code>
📛 Username: @{escape_markdown(user.username) if user.username else 'None'}
🗓️ First Seen: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, user_text)
    logger.info(f"New user started bot: {user.id} - {user.username}")

async def send_group_logger(client, chat: Chat):
    """Log when the bot is added to a new group."""
    if not ENABLE_LOGGING:
        return
    
    try:
        members = await client.get_chat_members_count(chat.id)
    except Exception as e:
        logger.error(f"Failed to get member count for {chat.id}: {e}")
        members = "Unknown"
    
    group_text = f"""
🔥 <b>BOT ADDED TO GROUP</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ Group: {escape_markdown(chat.title or 'Unknown')}
🆔 Chat ID: <code>{chat.id}</code>
👥 Members: {members}
📝 Type: {chat.type}
⏰ Added: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, group_text)
    logger.info(f"Bot added to group: {chat.id} - {chat.title}")

async def send_leave_group_logger(client, chat: Chat):
    """Log when the bot is removed from a group."""
    if not ENABLE_LOGGING:
        return
    
    leave_text = f"""
⚠️ <b>BOT REMOVED FROM GROUP</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ Group: {escape_markdown(chat.title or 'Unknown')}
🆔 Chat ID: <code>{chat.id}</code>
⏰ Removed: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, leave_text)
    logger.info(f"Bot removed from group: {chat.id} - {chat.title}")

async def send_command_logger(client, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log when a user executes a command."""
    if not ENABLE_LOGGING:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    
    if not message or not message.text:
        return
    
    command_text = f"""
⌨️ <b>COMMAND EXECUTED</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User: {escape_markdown(user.full_name or 'Unknown')}
🆔 User ID: <code>{user.id}</code>
📛 Username: @{escape_markdown(user.username) if user.username else 'None'}

💬 Command: <code>{escape_markdown(message.text[:100])}</code>
🏷️ Chat: {escape_markdown(chat.title or 'Private')}
🆔 Chat ID: <code>{chat.id}</code>

⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, command_text)
    if ENABLE_DEBUG_LOGS:
        logger.debug(f"Command logged: {message.text} from {user.id}")

async def send_error_logger(client, error: Exception, update: Update = None):
    """Log errors that occur in the bot."""
    if not ENABLE_LOGGING:
        return
    
    error_text = f"""
❌ <b>ERROR OCCURRED</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Error: <code>{escape_markdown(str(error)[:200])}</code>
📌 Type: {type(error).__name__}

"""
    
    if update and update.effective_user:
        user = update.effective_user
        error_text += f"""
👤 User: {escape_markdown(user.full_name or 'Unknown')}
🆔 User ID: <code>{user.id}</code>
"""
    
    if update and update.effective_chat:
        chat = update.effective_chat
        error_text += f"""
🏷️ Chat: {escape_markdown(chat.title or 'Private')}
🆔 Chat ID: <code>{chat.id}</code>
"""
    
    if update and update.effective_message and update.effective_message.text:
        error_text += f"""
💬 Message: <code>{escape_markdown(update.effective_message.text[:100])}</code>
"""
    
    error_text += f"""
⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await safe_send_message(client, LOGGER_GROUP_ID, error_text)
    logger.error(f"Error logged: {error}")

async def send_bank_transaction_logger(client, user_id: int, username: str, action: str, amount: int, bank_id: int = None):
    """Log bank transactions."""
    if not ENABLE_LOGGING:
        return
    
    transaction_text = f"""
💰 <b>BANK TRANSACTION</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User: @{escape_markdown(username) if username else str(user_id)}
🆔 User ID: <code>{user_id}</code>
💱 Action: <b>{action.upper()}</b>
💵 Amount: <b>₹{amount:,}</b>
"""
    
    if bank_id:
        transaction_text += f"""
🏦 Bank ID: <code>{bank_id}</code>
"""
    
    transaction_text += f"""
⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, transaction_text)

async def send_card_draw_logger(client, user_id: int, username: str, card_name: str, card_rarity: str, card_value: int):
    """Log when a user draws a card."""
    if not ENABLE_LOGGING:
        return
    
    card_text = f"""
🎴 <b>CARD DRAWN</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User: @{escape_markdown(username) if username else str(user_id)}
🆔 User ID: <code>{user_id}</code>

🃏 Card: <b>{escape_markdown(card_name)}</b>
⭐ Rarity: {card_rarity.upper()}
💎 Value: {card_value}

⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, card_text)

async def send_trade_logger(client, sender_id: int, sender_name: str, receiver_id: int, receiver_name: str, amount: int):
    """Log coin transfers/trades between users."""
    if not ENABLE_LOGGING:
        return
    
    trade_text = f"""
🔄 <b>COIN TRANSFER</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 Sender: @{escape_markdown(sender_name) if sender_name else str(sender_id)}
🆔 Sender ID: <code>{sender_id}</code>

📥 Receiver: @{escape_markdown(receiver_name) if receiver_name else str(receiver_id)}
🆔 Receiver ID: <code>{receiver_id}</code>

💸 Amount: <b>₹{amount:,}</b>

⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, trade_text)

async def send_duel_logger(client, winner_id: int, winner_name: str, loser_id: int, loser_name: str, reward: int = None):
    """Log duel results."""
    if not ENABLE_LOGGING:
        return
    
    duel_text = f"""
⚔️ <b>DUEL COMPLETED</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Winner: @{escape_markdown(winner_name) if winner_name else str(winner_id)}
🆔 Winner ID: <code>{winner_id}</code>

💀 Loser: @{escape_markdown(loser_name) if loser_name else str(loser_id)}
🆔 Loser ID: <code>{loser_id}</code>
"""
    
    if reward:
        duel_text += f"""
💰 Reward: <b>₹{reward:,}</b>
"""
    
    duel_text += f"""
⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, duel_text)

async def send_bot_stats_logger(client, stats: Dict[str, Any]):
    """Send bot statistics periodically."""
    if not ENABLE_LOGGING:
        return
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 Total Users: {stats.get('total_users', 'Unknown')}
💬 Total Groups: {stats.get('total_groups', 'Unknown')}
💰 Total Coins in Circulation: ₹{stats.get('total_coins', 0):,}
🏦 Total Tax Collected: ₹{stats.get('total_tax', 0):,}
🎴 Total Cards in Deck: {stats.get('total_cards', 0)}

⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, stats_text)

# =========================================================
# ADMIN NOTIFICATION FUNCTIONS
# =========================================================

async def send_admin_alert(client, message: str, severity: str = "INFO"):
    """Send an alert to admins."""
    if not ENABLE_LOGGING:
        return
    
    severity_emoji = {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥"
    }
    
    alert_text = f"""
{severity_emoji.get(severity, 'ℹ️')} <b>ADMIN ALERT</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{escape_markdown(message)}

⏰ Time: <code>{format_timestamp()}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await safe_send_message(client, LOGGER_GROUP_ID, alert_text)

# =========================================================
# BOT EVENT HANDLERS (to be integrated with main bot)
# =========================================================

async def setup_logger_handlers(application):
    """Setup logger handlers for the bot application."""
    
    # Store original handlers if needed
    pass

# =========================================================
# CONFIGURATION FUNCTION
# =========================================================

def configure_logger(logger_id: int = None, enable_debug: bool = False):
    """Configure logger settings."""
    global LOGGER_GROUP_ID, ENABLE_DEBUG_LOGS
    if logger_id:
        LOGGER_GROUP_ID = logger_id
    ENABLE_DEBUG_LOGS = enable_debug
    print(f"✅ Logger configured - Channel ID: {LOGGER_GROUP_ID}, Debug: {ENABLE_DEBUG_LOGS}")

# =========================================================
# TEST FUNCTION
# =========================================================

async def test_logger(client):
    """Test all logger functions."""
    print("Testing logger functions...")
    
    await send_alive_logger(client, "Test Bot")
    await send_bot_stats_logger(client, {
        'total_users': 100,
        'total_groups': 5,
        'total_coins': 50000,
        'total_tax': 5000,
        'total_cards': 50
    })
    await send_admin_alert(client, "This is a test alert", "INFO")
    
    print("Logger test completed")