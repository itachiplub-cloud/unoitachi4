
QUESTS = [
    {
        "name": "Daily Training",
        "description": "Claim your daily /earn and complete one /draw.",
        "reward": 100
    },
    {
        "name": "Shadow Duel",
        "description": "Win a duel using /challenge or /bossfight.",
        "reward": 200
    },
    {
        "name": "Blessing Seeker",
        "description": "Use /shinobiblessing and receive a random gift.",
        "reward": 150
    },
    {
        "name": "Karma Giver",
        "description": "Give karma to someone using +1 or 👍.",
        "reward": 50
    },
    {
        "name": "Legacy Builder",
        "description": "Check your progress with /shinobilegacy.",
        "reward": 75
    }
]

def get_all_quests():
    return QUESTS

def get_quest_by_name(name):
    for quest in QUESTS:
        if quest["name"].lower() == name.lower():
            return quest
    return None
