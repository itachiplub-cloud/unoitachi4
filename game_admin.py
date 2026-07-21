import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import is_bot_admin, is_owner
from game_config import (
    GAME_REGISTRY, PRESETS, get_game_config, save_game_config,
    get_default_config, validate_config, apply_preset, update_game_param,
    register_admin_command, _col,
)


def _require_owner_sudo(uid):
    if not is_owner(uid) and not is_bot_admin(uid):
        return False
    return True


def _config_keyboard(game_id):
    reg = GAME_REGISTRY[game_id]
    config = get_game_config(game_id) or get_default_config(game_id)

    rows = []
    param_list = list(reg["params"].items())
    for i in range(0, len(param_list), 2):
        row = []
        for j in range(2):
            if i + j < len(param_list):
                key, pdef = param_list[i + j]
                val = config.get(key, pdef["default"])
                row.append(InlineKeyboardButton(
                    f"{pdef['label']}: {val}",
                    callback_data=f"gc_view:{game_id}:{key}"
                ))
        rows.append(row)

    preset_row = [
        InlineKeyboardButton("🟢 Easy", callback_data=f"gc_preset:{game_id}:easy"),
        InlineKeyboardButton("🟡 Medium", callback_data=f"gc_preset:{game_id}:medium"),
    ]
    rows.append(preset_row)
    preset_row2 = [
        InlineKeyboardButton("🟠 High", callback_data=f"gc_preset:{game_id}:high"),
        InlineKeyboardButton("🔴 Extreme", callback_data=f"gc_preset:{game_id}:extreme"),
    ]
    rows.append(preset_row2)
    rows.append([
        InlineKeyboardButton("⚫ Custom", callback_data=f"gc_preset:{game_id}:custom"),
    ])
    rows.append([
        InlineKeyboardButton("🔄 Reset Defaults", callback_data=f"gc_reset:{game_id}"),
        InlineKeyboardButton("💾 Save All", callback_data=f"gc_save:{game_id}"),
    ])
    rows.append([
        InlineKeyboardButton("❌ Close", callback_data=f"gc_close:{game_id}"),
    ])
    return InlineKeyboardMarkup(rows)


def _view_keyboard(game_id, param_name):
    reg = GAME_REGISTRY[game_id]
    pdef = reg["params"][param_name]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✏️ Edit Value", callback_data=f"gc_edit:{game_id}:{param_name}"),
        ],
        [
            InlineKeyboardButton("◀️ Back", callback_data=f"gc_panel:{game_id}"),
        ],
    ])


# =========================================================
# COMMAND HANDLERS
# =========================================================

async def game_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id=None):
    uid = update.effective_user.id
    if not _require_owner_sudo(uid):
        return await update.message.reply_text("⛔ Access Denied. Owner or Sudo Admin only.")

    if not game_id:
        if not context.args:
            return await _show_game_list(update)
        game_id = context.args[0].lower()

    if game_id not in GAME_REGISTRY:
        return await update.message.reply_text(
            f"❌ Unknown game: <code>{game_id}</code>\n"
            f"Use /gameconfig to see all available games.",
            parse_mode="HTML"
        )

    reg = GAME_REGISTRY[game_id]
    config = get_game_config(game_id) or get_default_config(game_id)

    text = (
        f"{reg['emoji']} <b>{reg['name']}</b> Configuration\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Command: <code>{reg['command']}</code>\n"
        f"File: <code>{reg['file']}</code>\n\n"
        f"<b>Current Settings:</b>\n"
    )
    for key, pdef in reg["params"].items():
        val = config.get(key, pdef["default"])
        default = pdef["default"]
        marker = " ⚡" if val != default else ""
        text += f"• {pdef['label']}: <code>{val}</code>{marker}\n"

    await update.message.reply_text(text, reply_markup=_config_keyboard(game_id), parse_mode="HTML")


async def _show_game_list(update):
    categories = {}
    for gid, reg in GAME_REGISTRY.items():
        cat = reg.get("category", "general")
        categories.setdefault(cat, []).append((gid, reg))

    text = "🎮 <b>Game Configuration Panel</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for cat, games in sorted(categories.items()):
        text += f"<b>{cat.upper()}</b>\n"
        for gid, reg in games:
            text += f"  {reg['emoji']} <code>{gid}</code> — {reg['name']}  <code>{reg['command']}</code>\n"
        text += "\n"
    text += "Usage: <code>/gameconfig &lt;game_id&gt;</code>"

    await update.message.reply_text(text, parse_mode="HTML")


# =========================================================
# CALLBACK HANDLERS
# =========================================================

async def game_config_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()

    if not _require_owner_sudo(uid):
        return await query.edit_message_text("⛔ Access Denied.")

    data = query.data
    parts = data.split(":")

    if data.startswith("gc_panel:"):
        game_id = parts[1]
        return await _refresh_panel(query, game_id)

    elif data.startswith("gc_view:"):
        game_id = parts[1]
        param_name = parts[2]
        return await _show_param_view(query, game_id, param_name)

    elif data.startswith("gc_preset:"):
        game_id = parts[1]
        preset = parts[2]
        return await _apply_preset(query, game_id, preset)

    elif data.startswith("gc_edit:"):
        game_id = parts[1]
        param_name = parts[2]
        return await _start_param_edit(query, context, game_id, param_name)

    elif data.startswith("gc_reset:"):
        game_id = parts[1]
        return await _reset_defaults(query, game_id)

    elif data.startswith("gc_save:"):
        game_id = parts[1]
        return await _save_config(query, game_id)

    elif data.startswith("gc_close:"):
        game_id = parts[1]
        return await query.edit_message_text("❌ Configuration panel closed.")


async def _refresh_panel(query, game_id):
    reg = GAME_REGISTRY[game_id]
    config = get_game_config(game_id) or get_default_config(game_id)

    text = (
        f"{reg['emoji']} <b>{reg['name']}</b> Configuration\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Command: <code>{reg['command']}</code>\n\n"
        f"<b>Current Settings:</b>\n"
    )
    for key, pdef in reg["params"].items():
        val = config.get(key, pdef["default"])
        default = pdef["default"]
        marker = " ⚡" if val != default else ""
        text += f"• {pdef['label']}: <code>{val}</code>{marker}\n"

    text += "\n🟢=Easy 🟡=Medium 🟠=High 🔴=Extreme ⚫=Custom"
    text += "\n⚡ = modified from default"

    await query.edit_message_text(text, reply_markup=_config_keyboard(game_id), parse_mode="HTML")


async def _show_param_view(query, game_id, param_name):
    reg = GAME_REGISTRY[game_id]
    pdef = reg["params"][param_name]
    config = get_game_config(game_id) or get_default_config(game_id)
    current = config.get(param_name, pdef["default"])

    text = (
        f"{reg['emoji']} <b>{reg['name']}</b> — {pdef['label']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Current: <code>{current}</code>\n"
        f"Default: <code>{pdef['default']}</code>\n"
        f"Range: <code>{pdef['min']}</code> — <code>{pdef['max']}</code>\n"
        f"Type: <code>{pdef['type']}</code>"
    )

    await query.edit_message_text(text, reply_markup=_view_keyboard(game_id, param_name), parse_mode="HTML")


async def _start_param_edit(query, context, game_id, param_name):
    reg = GAME_REGISTRY[game_id]
    pdef = reg["params"][param_name]
    config = get_game_config(game_id) or get_default_config(game_id)
    current = config.get(param_name, pdef["default"])

    context.user_data["gc_editing"] = {
        "game_id": game_id,
        "param": param_name,
        "chat_id": query.message.chat.id,
        "message_id": query.message.message_id,
    }

    text = (
        f"✏️ <b>Editing {pdef['label']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Current: <code>{current}</code>\n"
        f"Range: <code>{pdef['min']}</code> — <code>{pdef['max']}</code>\n\n"
        f"Send the new value as a reply."
    )

    await query.edit_message_text(text, parse_mode="HTML")


async def handle_gc_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    editing = context.user_data.get("gc_editing")
    if not editing:
        return

    game_id = editing["game_id"]
    param_name = editing["param"]

    text = update.message.text.strip()
    try:
        if GAME_REGISTRY[game_id]["params"][param_name]["type"] == "int":
            value = int(text)
        else:
            value = float(text)
    except ValueError:
        return await update.message.reply_text("❌ Invalid number. Send again.")

    success, msg = update_game_param(game_id, param_name, value)

    del context.user_data["gc_editing"]
    await update.message.delete()

    if success:
        await update.message.reply_text(f"✅ {msg}")
        reg = GAME_REGISTRY[game_id]
        config = get_game_config(game_id) or get_default_config(game_id)

        result_text = (
            f"{reg['emoji']} <b>{reg['name']}</b> Updated\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        for key, pdef in reg["params"].items():
            val = config.get(key, pdef["default"])
            default = pdef["default"]
            marker = " ⚡" if val != default else ""
            result_text += f"• {pdef['label']}: <code>{val}</code>{marker}\n"

        await update.message.reply_text(result_text, reply_markup=_config_keyboard(game_id), parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ {msg}")


async def _apply_preset(query, game_id, preset_name):
    success, msg = apply_preset(game_id, preset_name)
    if success:
        await query.answer(f"✅ {msg}", show_alert=True)
        await _refresh_panel(query, game_id)
    else:
        await query.answer(f"❌ {msg}", show_alert=True)


async def _reset_defaults(query, game_id):
    defaults = get_default_config(game_id)
    save_game_config(game_id, defaults, preset="medium")
    await query.answer("✅ Reset to defaults", show_alert=True)
    await _refresh_panel(query, game_id)


async def _save_config(query, game_id):
    config = get_game_config(game_id)
    if config:
        _col("game_configs").update_one(
            {"game_id": game_id},
            {"$set": {"config": config, "saved_at": __import__("time").time()}},
            upsert=True,
        )
    await query.answer("✅ Configuration saved to database!", show_alert=True)


# =========================================================
# BATCH COMMANDS
# =========================================================

async def gameconfigall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _require_owner_sudo(uid):
        return await update.message.reply_text("⛔ Access Denied. Owner or Sudo Admin only.")

    text = "🎮 <b>All Game Configurations</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for gid, reg in sorted(GAME_REGISTRY.items()):
        config = get_game_config(gid) or get_default_config(gid)
        defaults = get_default_config(gid)
        modified = sum(1 for k in config if config.get(k) != defaults.get(k))
        status = f"⚡{modified} modified" if modified > 0 else "✅ default"
        text += f"{reg['emoji']} <code>{gid}</code> — {reg['name']}  [{status}]\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def gameconfigresetall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return await update.message.reply_text("⛔ Owner only command.")

    for gid in GAME_REGISTRY:
        defaults = get_default_config(gid)
        save_game_config(gid, defaults, preset="medium")

    await update.message.reply_text(
        f"✅ Reset all {len(GAME_REGISTRY)} game configurations to defaults.",
        parse_mode="HTML"
    )


async def gameconfigexport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _require_owner_sudo(uid):
        return await update.message.reply_text("⛔ Access Denied.")

    import json
    all_configs = {}
    for gid in GAME_REGISTRY:
        config = get_game_config(gid) or get_default_config(gid)
        all_configs[gid] = config

    text = f"<pre>{json.dumps(all_configs, indent=2)}</pre>"
    await update.message.reply_text(text, parse_mode="HTML")


# =========================================================
# REGISTER ALL COMMANDS
# =========================================================

def register_all_game_admin_commands():
    register_admin_command(
        cmd="/gameconfig",
        handler=game_config_command,
        description="Configure game difficulty, RTP, multipliers, and all settings",
        syntax="/gameconfig [game_id]",
        example="/gameconfig fly",
        permission="owner_sudo",
        category="🎮 Game Commands",
        notes="Opens inline keyboard panel. Use game_id from the list.",
    )
    register_admin_command(
        cmd="/gameconfigall",
        handler=gameconfigall,
        description="View all game configurations at once",
        syntax="/gameconfigall",
        example="/gameconfigall",
        permission="owner_sudo",
        category="🎮 Game Commands",
        notes="Shows status of every game config.",
    )
    register_admin_command(
        cmd="/gameconfigresetall",
        handler=gameconfigresetall,
        description="Reset ALL game configurations to defaults",
        syntax="/gameconfigresetall",
        example="/gameconfigresetall",
        permission="owner_only",
        category="🎮 Game Commands",
        notes="⚠️ Owner only. Resets everything.",
    )
    register_admin_command(
        cmd="/gameconfigexport",
        handler=gameconfigexport,
        description="Export all game configurations as JSON",
        syntax="/gameconfigexport",
        example="/gameconfigexport",
        permission="owner_sudo",
        category="🎮 Game Commands",
        notes="Shows full JSON export of all configs.",
    )

    for gid, reg in GAME_REGISTRY.items():
        async def _make_handler(game_id=gid):
            async def handler(update, context):
                await game_config_command(update, context, game_id)
            return handler

        h = asyncio.get_event_loop().run_until_complete(_make_handler()) if False else None

        handler_fn = lambda update, context, gid=gid: game_config_command(update, context, gid)
        register_admin_command(
            cmd=f"/{gid}config",
            handler=handler_fn,
            description=f"Configure {reg['name']} settings",
            syntax=f"/{gid}config",
            example=f"/{gid}config",
            permission="owner_sudo",
            category="🎮 Game Commands",
            notes=f"Opens {reg['name']} configuration panel.",
        )
