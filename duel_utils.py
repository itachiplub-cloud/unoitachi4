import asyncio
from card_utils import (
    get_random_card,
    apply_rarity_bonus,
    update_duel_stats,
)
from database import update_balance

DUEL_REWARD = 50  
async def run_duel(context, chat_id, player1_id, player2_id):
    spell1 = apply_rarity_bonus(get_random_card())
    spell2 = apply_rarity_bonus(get_random_card())

    name1 = spell1.get("name", "Mystic")
    name2 = spell2.get("name", "Arcana")
    power1 = spell1.get("value", 0)
    power2 = spell2.get("value", 0)

    winner_id = None
    if power1 > power2:
        winner_id = player1_id
    elif power2 > power1:
        winner_id = player2_id

    await asyncio.to_thread(update_duel_stats, player1_id, power1, power2)
    await asyncio.to_thread(update_duel_stats, player2_id, power2, power1)

    if winner_id:
        await asyncio.to_thread(update_balance, winner_id, DUEL_REWARD)

    result = (
        f"🧙 Player 1 cast <b>{name1}</b> ({power1})\n"
        f"🧙 Player 2 cast <b>{name2}</b> ({power2})\n\n"
    )
    result += (
        f"🏆 <b>Winner:</b> <a href='tg://user?id={winner_id}'>The mightier mage!</a>\n"
        f"💰 Reward: {DUEL_REWARD} coins"
        if winner_id else
        "⚖️ <b>It's a draw!</b> Balanced battle between equals."
    )

    await context.bot.send_message(chat_id=chat_id, text=result, parse_mode="HTML")
