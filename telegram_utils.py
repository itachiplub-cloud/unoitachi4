from telegram.ext import ContextTypes

async def get_group_user_ids(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> set:
    members = set()

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            members.add(admin.user.id)
    except Exception as e:
        print(f"⚠️ Failed to fetch admins: {e}")

    return members
