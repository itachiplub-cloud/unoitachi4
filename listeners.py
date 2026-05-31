import time
from telegram import Update
from telegram.ext import ContextTypes
from database import get_balance, update_balance, add_user, get_username

last_itachi_reward = {}
last_nitho_reward = {}

import time

async def itachi_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.lower()
    if "itachi" not in text or "best" not in text:
        return

    uid = msg.from_user.id
    now = int(time.time())
    cooldown = 14400  # 4 hours

    last = last_itachi_reward.get(uid, 0)
    if now - last < cooldown:
        await msg.reply_text(f"⏳ Try again in {cooldown - (now - last)}s.")
        return
    last_itachi_reward[uid] = now

    add_user(uid, msg.from_user.username or msg.from_user.full_name or str(uid))

    before = get_balance(uid)
    print(f"DEBUG Itachi before: uid={uid}, balance={before}")

    reward = 1000
    update_balance(uid, reward)

    after = get_balance(uid)
    print(f"DEBUG Itachi after:  uid={uid}, balance={after}")

    name = get_username(uid)
    await msg.reply_text(f"🩷 @{name} earned {reward} coins! You now have {after} coins.")




import time
from telegram import Update
from telegram.ext import ContextTypes
from database import get_balance, update_balance, add_user, get_username

last_nitho_reward = {}

import logging  

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

        add_user(uid, msg.from_user.username or msg.from_user.full_name or str(uid))
        reward = 1
        update_balance(uid, reward)

        after = get_balance(uid)
        name = get_username(uid)
        await msg.reply_text(f"🫣 @{name} earned {reward} coin! You now have {after} coins.")

  