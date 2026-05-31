from telegram.ext import ContextTypes

async def get_group_user_ids(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> set:
    members = set()

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            members.add(admin.user.id)
    except Exception as e:
        print(f"⚠️ Failed to fetch admins: {e}")

    try:
        # This part depends on your bot having access to message history
        # You can skip or customize this based on your bot's permissions
        history = await context.bot.get_chat_history(chat_id, limit=100)
        for msg in history:
            if msg.from_user:
                members.add(msg.from_user.id)
    except Exception as e:
        print(f"⚠️ Failed to fetch chat history: {e}")

    return members
