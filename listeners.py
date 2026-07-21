import asyncio
import time
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import get_balance, update_balance, add_user, get_username
from config import ACTIVITY_COOLDOWN, ACTIVITY_REWARD

last_itachi_reward = {}
last_nitho_reward = {}

async def itachi_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.lower()
    if "itachi" not in text or "best" not in text:
        return

    uid = msg.from_user.id
    now = int(time.time())
    cooldown = ACTIVITY_COOLDOWN

    last = last_itachi_reward.get(uid, 0)
    if now - last < cooldown:
        await msg.reply_text(f"⏳ Try again in {cooldown - (now - last)}s.")
        return
    last_itachi_reward[uid] = now

    await asyncio.to_thread(add_user, uid, msg.from_user.username or msg.from_user.full_name or str(uid))

    before = await asyncio.to_thread(get_balance, uid)
    print(f"DEBUG Itachi before: uid={uid}, balance={before}")

    reward = ACTIVITY_REWARD
    await asyncio.to_thread(update_balance, uid, reward)

    after = await asyncio.to_thread(get_balance, uid)
    print(f"DEBUG Itachi after:  uid={uid}, balance={after}")

    name = await asyncio.to_thread(get_username, uid)
    await msg.reply_text(f"🩷 @{name} earned {reward} coins! You now have {after} coins.")



async def nitho_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip().lower()
    
    logging.debug(f"Nitho Listener Received: {text}")

    if "nitho" in text and "nalla" in text:
        uid = msg.from_user.id
        now = int(time.time())
        cooldown = 300  # 5 minutes

        last = last_nitho_reward.get(uid, 0)
        if now - last < cooldown:
            await msg.reply_text(f"⏳ Try again in {cooldown - (now - last)}s.")
            return
        last_nitho_reward[uid] = now

        await asyncio.to_thread(add_user, uid, msg.from_user.username or msg.from_user.full_name or str(uid))
        reward = 1
        await asyncio.to_thread(update_balance, uid, reward)

        after = await asyncio.to_thread(get_balance, uid)
        name = await asyncio.to_thread(get_username, uid)
        await msg.reply_text(f"🫣 @{name} earned {reward} coin! You now have {after} coins.")
