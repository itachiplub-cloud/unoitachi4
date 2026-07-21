from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import is_bot_admin, is_owner
from game_config import (
    GAME_REGISTRY, get_all_admin_commands, search_admin_commands,
    get_commands_by_category,
)


def _require_owner_sudo(uid):
    return is_owner(uid) or is_bot_admin(uid)


# =========================================================
# AUTO-GENERATED HELP CATEGORIES
# =========================================================

def _build_help_categories():
    categories = {}
    for cmd, info in get_all_admin_commands().items():
        cat = info.get("category", "General")
        categories.setdefault(cat, []).append((cmd, info))
    return categories


def _format_command_entry(cmd, info):
    perm_emoji = "👑" if "owner" in info["permission"] else "🛡️"
    lines = [
        f"  {perm_emoji} <code>{cmd}</code>",
        f"    {info['description']}",
        f"    Syntax: <code>{info['syntax']}</code>",
        f"    Example: <code>{info['example']}</code>",
        f"    Permission: {info['permission'].replace('_', ' ').title()}",
    ]
    if info.get("notes"):
        lines.append(f"    📝 {info['notes']}")
    return "\n".join(lines)


# =========================================================
# /helpadmin — full auto-generated help
# =========================================================

async def helpadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _require_owner_sudo(uid):
        return await update.message.reply_text(
            "⛔ <b>Access Denied</b>\nOnly Owner and Sudo Admins can use this command.",
            parse_mode="HTML"
        )

    if context.args:
        query = " ".join(context.args)
        return await _help_search(update, query)

    categories = _build_help_categories()
    game_count = len(GAME_REGISTRY)
    cmd_count = len(get_all_admin_commands())

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙ <b>UNO ITACHI ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 {cmd_count} commands across {len(categories)} categories\n"
        f"🎮 {game_count} games configured\n\n"
    )

    for cat_name in sorted(categories.keys()):
        cmds = categories[cat_name]
        text += f"\n━━━ {cat_name} ━━━\n"
        for cmd, info in sorted(cmds, key=lambda x: x[0]):
            text += _format_command_entry(cmd, info) + "\n\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔍 <b>Search:</b> <code>/helpadmin &lt;query&gt;</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            chunk = text[i:i + 4000]
            if i == 0:
                await update.message.reply_text(chunk, parse_mode="HTML")
            else:
                await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


# =========================================================
# REGISTER COMMANDS IN HELP SYSTEM
# =========================================================

def register_help_admin_commands():
    from game_config import register_admin_command

    register_admin_command(
        cmd="/helpadmin",
        handler=helpadmin,
        description="View all admin commands (auto-generated)",
        syntax="/helpadmin [query]",
        example="/helpadmin fly",
        permission="owner_sudo",
        category="📋 Help System",
        notes="Auto-detects all admin commands. Supports search.",
    )
    register_admin_command(
        cmd="/gamehelp",
        handler=gamehelp,
        description="View detailed help for a specific game",
        syntax="/gamehelp [game_id]",
        example="/gamehelp fly",
        permission="owner_sudo",
        category="📋 Help System",
        notes="Shows current config, defaults, and all parameters.",
    )


async def _help_search(update, query):
    results = search_admin_commands(query)

    if not results:
        text = (
            f"🔍 No results for <code>{query}</code>\n\n"
            f"Try: <code>/helpadmin fly</code>, <code>/helpadmin economy</code>, <code>/helpadmin game</code>"
        )
        return await update.message.reply_text(text, parse_mode="HTML")

    text = f"🔍 <b>Search: {query}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for cmd, info in sorted(results.items()):
        text += _format_command_entry(cmd, info) + "\n\n"

    await update.message.reply_text(text, parse_mode="HTML")


# =========================================================
# GAME-SPECIFIC HELP
# =========================================================

async def gamehelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _require_owner_sudo(uid):
        return await update.message.reply_text("⛔ Access Denied.", parse_mode="HTML")

    if not context.args:
        return await _show_game_help_list(update)

    game_id = context.args[0].lower()
    if game_id not in GAME_REGISTRY:
        return await update.message.reply_text(
            f"❌ Unknown game: <code>{game_id}</code>",
            parse_mode="HTML"
        )

    reg = GAME_REGISTRY[game_id]
    from game_config import get_game_config, get_default_config
    config = get_game_config(game_id) or get_default_config(game_id)

    text = (
        f"{reg['emoji']} <b>{reg['name']}</b> — Admin Reference\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Command: <code>{reg['command']}</code>\n"
        f"File: <code>{reg['file']}</code>\n\n"
        f"<b>Current Configuration:</b>\n"
    )

    for key, pdef in reg["params"].items():
        val = config.get(key, pdef["default"])
        default = pdef["default"]
        marker = " ⚡" if val != default else ""
        text += f"• {pdef['label']}: <code>{val}</code> (default: {default}){marker}\n"

    text += (
        f"\n<b>Configure:</b> <code>/gameconfig {game_id}</code>\n"
        f"<b>Search help:</b> <code>/helpadmin {game_id}</code>"
    )

    await update.message.reply_text(text, parse_mode="HTML")


async def _show_game_help_list(update):
    categories = {}
    for gid, reg in GAME_REGISTRY.items():
        cat = reg.get("category", "general")
        categories.setdefault(cat, []).append((gid, reg))

    text = "🎮 <b>Game Help Index</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for cat, games in sorted(categories.items()):
        text += f"<b>{cat.upper()}</b>\n"
        for gid, reg in games:
            text += f"  {reg['emoji']} <code>{gid}</code> — {reg['name']}\n"
        text += "\n"
    text += "Usage: <code>/gamehelp &lt;game_id&gt;</code>"

    await update.message.reply_text(text, parse_mode="HTML")
