import time
from pymongo import MongoClient, ASCENDING
from config import MONGO_URL

_client = None
_db = None
_config_cache = {}


def _get_db():
    global _client, _db
    if _client is None:
        _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    if _db is None:
        _db = _client["unoitachi_games"]
    return _db


def _col(name):
    return _get_db()[name]


# =========================================================
# GAME REGISTRY — auto-detected from codebase
# =========================================================

GAME_REGISTRY = {
    "flip": {
        "name": "Coin Flip",
        "emoji": "🪙",
        "command": "/flip",
        "file": "games.py",
        "category": "games",
        "params": {
            "win_chance": {"type": "float", "min": 0, "max": 100, "default": 50, "label": "Win Chance %"},
            "multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 1.5, "label": "Win Multiplier"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 120, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 10, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 10000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 25, "label": "House Edge %"},
        },
    },
    "roll": {
        "name": "Dice Roll",
        "emoji": "🎲",
        "command": "/roll",
        "file": "games.py",
        "category": "games",
        "params": {
            "fair_win_chance": {"type": "float", "min": 0, "max": 100, "default": 41.67, "label": "Fair Mode Win %"},
            "cheat_win_chance": {"type": "float", "min": 0, "max": 100, "default": 40, "label": "Cheat Mode Win %"},
            "multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 1.5, "label": "Win Multiplier"},
            "cheat_threshold": {"type": "int", "min": 100, "max": 1000000, "default": 10000, "label": "Cheat Threshold"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 1800, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 10, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 50000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 8.33, "label": "House Edge %"},
        },
    },
    "rps": {
        "name": "Rock Paper Scissors",
        "emoji": "✊",
        "command": "/rps",
        "file": "games.py",
        "category": "games",
        "params": {
            "win_chance": {"type": "float", "min": 0, "max": 100, "default": 33.33, "label": "Win Chance %"},
            "multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 1.5, "label": "Win Multiplier"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 1800, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 10, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 50000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 8.33, "label": "House Edge %"},
        },
    },
    "guess": {
        "name": "Number Guess",
        "emoji": "🔢",
        "command": "/guessbet",
        "file": "games.py",
        "category": "games",
        "params": {
            "exact_multiplier": {"type": "float", "min": 1.0, "max": 100.0, "default": 10.0, "label": "Exact Match Multiplier"},
            "close_multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 2.0, "label": "Close Match Multiplier"},
            "close_range": {"type": "int", "min": 1, "max": 20, "default": 3, "label": "Close Range"},
            "number_range": {"type": "int", "min": 2, "max": 100, "default": 50, "label": "Number Range"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 60, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 10, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 50000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 60, "label": "House Edge %"},
        },
    },
    "spin": {
        "name": "Spin the Wheel",
        "emoji": "🎡",
        "command": "/spin",
        "file": "games.py",
        "category": "games",
        "params": {
            "red_chance": {"type": "float", "min": 0, "max": 100, "default": 50, "label": "Red Chance %"},
            "green_chance": {"type": "float", "min": 0, "max": 100, "default": 30, "label": "Green Chance %"},
            "blue_chance": {"type": "float", "min": 0, "max": 100, "default": 15, "label": "Blue Chance %"},
            "jackpot_chance": {"type": "float", "min": 0, "max": 100, "default": 5, "label": "Jackpot Chance %"},
            "jackpot_multiplier": {"type": "float", "min": 1.0, "max": 100.0, "default": 2.0, "label": "Jackpot Multiplier"},
            "blue_multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 1.5, "label": "Blue Multiplier"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 21600, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 100, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 100000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 42.5, "label": "House Edge %"},
        },
    },
    "mines": {
        "name": "Mines",
        "emoji": "💣",
        "command": "/mines",
        "file": "games.py",
        "category": "games",
        "params": {
            "grid_size": {"type": "int", "min": 3, "max": 10, "default": 5, "label": "Grid Size"},
            "max_bombs": {"type": "int", "min": 1, "max": 24, "default": 24, "label": "Max Bombs"},
            "min_exit_tiles": {"type": "int", "min": 1, "max": 10, "default": 3, "label": "Min Exit Tiles"},
            "base_multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 1.25, "label": "Base Multiplier"},
            "max_multiplier": {"type": "float", "min": 1.0, "max": 50.0, "default": 7.0, "label": "Max Multiplier"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 180, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 50, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 100000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 5, "label": "House Edge %"},
        },
    },
    "dig": {
        "name": "Dig",
        "emoji": "⛏️",
        "command": "/dig",
        "file": "games.py",
        "category": "games",
        "params": {
            "success_chance": {"type": "float", "min": 0, "max": 100, "default": 80, "label": "Success Chance %"},
            "min_depth": {"type": "int", "min": 1, "max": 5, "default": 1, "label": "Min Depth"},
            "max_depth": {"type": "int", "min": 1, "max": 20, "default": 10, "label": "Max Depth"},
            "cost_per_depth": {"type": "int", "min": 10, "max": 10000, "default": 100, "label": "Cost Per Depth"},
            "reward_min_mult": {"type": "float", "min": 0.1, "max": 10.0, "default": 1.5, "label": "Reward Min Mult"},
            "reward_max_mult": {"type": "float", "min": 0.5, "max": 20.0, "default": 5.0, "label": "Reward Max Mult"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 300, "label": "Cooldown (sec)"},
        },
    },
    "blackjack": {
        "name": "Blackjack",
        "emoji": "🃏",
        "command": "/blackjack",
        "file": "games.py",
        "category": "games",
        "params": {
            "win_multiplier": {"type": "float", "min": 1.0, "max": 5.0, "default": 1.0, "label": "Win Multiplier"},
            "police_chance": {"type": "float", "min": 0, "max": 50, "default": 7, "label": "Police Chance %"},
            "police_high_bet_bonus": {"type": "float", "min": 0, "max": 50, "default": 3, "label": "High Bet Police +%"},
            "police_fine": {"type": "int", "min": 0, "max": 10000, "default": 500, "label": "Police Fine"},
            "min_card": {"type": "int", "min": 1, "max": 5, "default": 2, "label": "Min Card Value"},
            "max_card": {"type": "int", "min": 5, "max": 21, "default": 11, "label": "Max Card Value"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 300, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 50, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 50000, "label": "Max Bet"},
            "house_edge": {"type": "float", "min": 0, "max": 100, "default": 2, "label": "House Edge %"},
        },
    },
    "heist": {
        "name": "Heist",
        "emoji": "🏦",
        "command": "/heist",
        "file": "games.py",
        "category": "games",
        "params": {
            "win_chance": {"type": "float", "min": 0, "max": 100, "default": 60, "label": "Win Chance %"},
            "entry_cost": {"type": "int", "min": 50, "max": 100000, "default": 500, "label": "Entry Cost"},
            "reward_min": {"type": "int", "min": 100, "max": 1000000, "default": 1000, "label": "Reward Min"},
            "reward_max": {"type": "int", "min": 500, "max": 10000000, "default": 5000, "label": "Reward Max"},
            "police_chance": {"type": "float", "min": 0, "max": 50, "default": 7, "label": "Police Chance %"},
            "police_fine": {"type": "int", "min": 0, "max": 10000, "default": 500, "label": "Police Fine"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 300, "label": "Cooldown (sec)"},
        },
    },
    "fly": {
        "name": "Fly / Crash",
        "emoji": "✈️",
        "command": "/fly",
        "file": "games.py",
        "category": "games",
        "params": {
            "low_crash_chance": {"type": "float", "min": 0, "max": 100, "default": 10, "label": "Low Risk Crash %"},
            "low_min_mult": {"type": "float", "min": 1.0, "max": 5.0, "default": 1.1, "label": "Low Risk Min Mult"},
            "low_max_mult": {"type": "float", "min": 1.0, "max": 10.0, "default": 2.0, "label": "Low Risk Max Mult"},
            "med_crash_chance": {"type": "float", "min": 0, "max": 100, "default": 30, "label": "Medium Risk Crash %"},
            "med_min_mult": {"type": "float", "min": 1.0, "max": 5.0, "default": 1.5, "label": "Medium Risk Min Mult"},
            "med_max_mult": {"type": "float", "min": 1.0, "max": 10.0, "default": 4.0, "label": "Medium Risk Max Mult"},
            "high_crash_chance": {"type": "float", "min": 0, "max": 100, "default": 60, "label": "High Risk Crash %"},
            "high_min_mult": {"type": "float", "min": 1.0, "max": 10.0, "default": 2.5, "label": "High Risk Min Mult"},
            "high_max_mult": {"type": "float", "min": 1.0, "max": 20.0, "default": 6.5, "label": "High Risk Max Mult"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 90, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 10, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 100000, "label": "Max Bet"},
        },
    },
    "defuse": {
        "name": "Defuse",
        "emoji": "🧨",
        "command": "/defuse",
        "file": "games.py",
        "category": "games",
        "params": {
            "win_chance": {"type": "float", "min": 0, "max": 100, "default": 20, "label": "Win Chance %"},
            "wire_count": {"type": "int", "min": 2, "max": 10, "default": 5, "label": "Wire Count"},
            "low_multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 1.5, "label": "Low Risk Multiplier"},
            "low_loss_cut": {"type": "float", "min": 0.0, "max": 2.0, "default": 0.5, "label": "Low Risk Loss Cut"},
            "med_multiplier": {"type": "float", "min": 1.0, "max": 10.0, "default": 2.5, "label": "Medium Risk Multiplier"},
            "med_loss_cut": {"type": "float", "min": 0.0, "max": 2.0, "default": 1.0, "label": "Medium Risk Loss Cut"},
            "high_multiplier": {"type": "float", "min": 1.0, "max": 20.0, "default": 4.0, "label": "High Risk Multiplier"},
            "high_loss_cut": {"type": "float", "min": 0.0, "max": 3.0, "default": 1.5, "label": "High Risk Loss Cut"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 90, "label": "Cooldown (sec)"},
            "min_bet": {"type": "int", "min": 1, "max": 1000000, "default": 10, "label": "Min Bet"},
            "max_bet": {"type": "int", "min": 1, "max": 10000000, "default": 50000, "label": "Max Bet"},
        },
    },
    "duel": {
        "name": "Duel",
        "emoji": "⚔️",
        "command": "/challenge",
        "file": "duel_engine.py",
        "category": "games",
        "params": {
            "entry_cost": {"type": "int", "min": 10, "max": 100000, "default": 500, "label": "Entry Cost"},
            "prize": {"type": "int", "min": 100, "max": 1000000, "default": 2000, "label": "Winner Prize"},
            "tax": {"type": "int", "min": 0, "max": 100000, "default": 500, "label": "Tax"},
            "hp": {"type": "int", "min": 50, "max": 500, "default": 100, "label": "Starting HP"},
            "punch_min": {"type": "int", "min": 1, "max": 50, "default": 10, "label": "Punch Min DMG"},
            "punch_max": {"type": "int", "min": 5, "max": 100, "default": 20, "label": "Punch Max DMG"},
            "slap_min": {"type": "int", "min": 1, "max": 50, "default": 5, "label": "Slap Min DMG"},
            "slap_max": {"type": "int", "min": 5, "max": 100, "default": 25, "label": "Slap Max DMG"},
            "kick_min": {"type": "int", "min": 1, "max": 50, "default": 15, "label": "Kick Min DMG"},
            "kick_max": {"type": "int", "min": 5, "max": 100, "default": 30, "label": "Kick Max DMG"},
            "session_ttl": {"type": "int", "min": 60, "max": 7200, "default": 600, "label": "Session TTL (sec)"},
        },
    },
    "steal": {
        "name": "Steal",
        "emoji": "🦹",
        "command": "/steal",
        "file": "main.py",
        "category": "economy",
        "params": {
            "max_steal": {"type": "int", "min": 100, "max": 1000000, "default": 25000, "label": "Max Steal Amount"},
            "cooldown": {"type": "int", "min": 60, "max": 86400, "default": 7200, "label": "Cooldown (sec)"},
        },
    },
    "draw": {
        "name": "Draw Card (Gacha)",
        "emoji": "🎴",
        "command": "/draw",
        "file": "card_editor.py",
        "category": "cards",
        "params": {
            "cost": {"type": "int", "min": 100, "max": 100000, "default": 1000, "label": "Draw Cost"},
            "common_chance": {"type": "float", "min": 0, "max": 100, "default": 70, "label": "Common Chance %"},
            "rare_chance": {"type": "float", "min": 0, "max": 100, "default": 27, "label": "Rare Chance %"},
            "legendary_chance": {"type": "float", "min": 0, "max": 100, "default": 3, "label": "Legendary Chance %"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 300, "label": "Cooldown (sec)"},
        },
    },
    "earn": {
        "name": "Earn (Daily)",
        "emoji": "💰",
        "command": "/earn",
        "file": "main.py",
        "category": "economy",
        "params": {
            "reward_min": {"type": "int", "min": 10, "max": 100000, "default": 100, "label": "Reward Min"},
            "reward_max": {"type": "int", "min": 50, "max": 1000000, "default": 300, "label": "Reward Max"},
            "cooldown": {"type": "int", "min": 3600, "max": 86400, "default": 86400, "label": "Cooldown (sec)"},
        },
    },
    "raffle": {
        "name": "Raffle",
        "emoji": "🎟️",
        "command": "/enter",
        "file": "games.py",
        "category": "games",
        "params": {
            "entry_cost": {"type": "int", "min": 10, "max": 100000, "default": 200, "label": "Entry Cost"},
            "prize_per_entry": {"type": "int", "min": 100, "max": 1000000, "default": 1000, "label": "Prize Per Entry"},
            "draw_delay": {"type": "int", "min": 5, "max": 300, "default": 30, "label": "Draw Delay (sec)"},
            "cooldown": {"type": "int", "min": 0, "max": 86400, "default": 30, "label": "Cooldown (sec)"},
        },
    },
    "wordgame": {
        "name": "Word Game",
        "emoji": "📝",
        "command": "/startwordgame",
        "file": "word_game.py",
        "category": "games",
        "params": {
            "lives_mult": {"type": "float", "min": 0.5, "max": 3.0, "default": 1.0, "label": "Lives Multiplier"},
            "reward_per_guess": {"type": "int", "min": 0, "max": 1000, "default": 1, "label": "Score Per Guess"},
        },
    },
    "tnd": {
        "name": "Truth & Dare",
        "emoji": "🤫",
        "command": "/tnd",
        "file": "tnd.py",
        "category": "social",
        "params": {
            "reward_per_player": {"type": "int", "min": 0, "max": 10000, "default": 100, "label": "Reward Per Player"},
            "session_ttl": {"type": "int", "min": 300, "max": 14400, "default": 3600, "label": "Session TTL (sec)"},
        },
    },
    "petbattle": {
        "name": "Pet Battle",
        "emoji": "🐾",
        "command": "/petbattle",
        "file": "pets.py",
        "category": "social",
        "params": {
            "winner_reward": {"type": "int", "min": 0, "max": 10000, "default": 200, "label": "Winner Reward"},
        },
    },
    "bossfight": {
        "name": "Boss Fight",
        "emoji": "👹",
        "command": "/bossfight",
        "file": "main.py",
        "category": "games",
        "params": {
            "player_hp": {"type": "int", "min": 50, "max": 500, "default": 100, "label": "Player HP"},
            "boss_hp": {"type": "int", "min": 50, "max": 1000, "default": 150, "label": "Boss HP"},
            "player_min_dmg": {"type": "int", "min": 1, "max": 50, "default": 15, "label": "Player Min DMG"},
            "player_max_dmg": {"type": "int", "min": 5, "max": 100, "default": 35, "label": "Player Max DMG"},
            "boss_min_dmg": {"type": "int", "min": 1, "max": 50, "default": 20, "label": "Boss Min DMG"},
            "boss_max_dmg": {"type": "int", "min": 5, "max": 100, "default": 40, "label": "Boss Max DMG"},
            "reward_min": {"type": "int", "min": 0, "max": 100000, "default": 200, "label": "Reward Min"},
            "reward_max": {"type": "int", "min": 100, "max": 1000000, "default": 500, "label": "Reward Max"},
        },
    },
    "shinobibattle": {
        "name": "Shinobi Battle",
        "emoji": "🥷",
        "command": "/shinobibattle",
        "file": "main.py",
        "category": "games",
        "params": {
            "player_hp": {"type": "int", "min": 50, "max": 500, "default": 100, "label": "Player HP"},
            "enemy_hp": {"type": "int", "min": 50, "max": 500, "default": 120, "label": "Enemy HP"},
            "player_min_dmg": {"type": "int", "min": 1, "max": 50, "default": 20, "label": "Player Min DMG"},
            "player_max_dmg": {"type": "int", "min": 5, "max": 100, "default": 35, "label": "Player Max DMG"},
            "enemy_min_dmg": {"type": "int", "min": 1, "max": 50, "default": 15, "label": "Enemy Min DMG"},
            "enemy_max_dmg": {"type": "int", "min": 5, "max": 100, "default": 30, "label": "Enemy Max DMG"},
            "reward_min": {"type": "int", "min": 0, "max": 100000, "default": 300, "label": "Reward Min"},
            "reward_max": {"type": "int", "min": 100, "max": 1000000, "default": 600, "label": "Reward Max"},
        },
    },
    "shinobichest": {
        "name": "Shinobi Chest",
        "emoji": "📦",
        "command": "/shinobichest",
        "file": "main.py",
        "category": "economy",
        "params": {
            "coins_min": {"type": "int", "min": 10, "max": 10000, "default": 100, "label": "Coins Min"},
            "coins_max": {"type": "int", "min": 100, "max": 100000, "default": 500, "label": "Coins Max"},
            "karma_reward": {"type": "int", "min": 1, "max": 50, "default": 5, "label": "Karma Reward"},
        },
    },
    "shinobialtar": {
        "name": "Shinobi Altar",
        "emoji": "🏛️",
        "command": "/shinobialtar",
        "file": "main.py",
        "category": "cards",
        "params": {
            "karma_min": {"type": "int", "min": 1, "max": 50, "default": 3, "label": "Karma Min"},
            "karma_max": {"type": "int", "min": 5, "max": 100, "default": 10, "label": "Karma Max"},
        },
    },
    "shinobiforge": {
        "name": "Shinobi Forge",
        "emoji": "🔨",
        "command": "/shinobiforge",
        "file": "main.py",
        "category": "cards",
        "params": {
            "bonus_min": {"type": "int", "min": 10, "max": 1000, "default": 50, "label": "Bonus Min"},
            "bonus_max": {"type": "int", "min": 50, "max": 5000, "default": 150, "label": "Bonus Max"},
        },
    },
    "shinobifusion": {
        "name": "Shinobi Fusion",
        "emoji": "✨",
        "command": "/shinobifusion",
        "file": "main.py",
        "category": "cards",
        "params": {
            "bonus_min": {"type": "int", "min": 50, "max": 5000, "default": 100, "label": "Bonus Min"},
            "bonus_max": {"type": "int", "min": 100, "max": 10000, "default": 300, "label": "Bonus Max"},
        },
    },
}


# =========================================================
# PRESET DIFFICULTIES
# =========================================================

PRESETS = {
    "easy": {
        "label": "🟢 Easy",
        "description": "Low risk, low reward",
        "overrides": {
            "house_edge": 2, "win_chance": 60, "multiplier": 1.3,
            "low_crash_chance": 5, "med_crash_chance": 15, "high_crash_chance": 40,
            "police_chance": 3, "reward_min_mult": 2.0,
        },
    },
    "medium": {
        "label": "🟡 Medium",
        "description": "Balanced risk and reward",
        "overrides": {
            "house_edge": 10, "win_chance": 45, "multiplier": 1.5,
            "low_crash_chance": 10, "med_crash_chance": 30, "high_crash_chance": 60,
            "police_chance": 7, "reward_min_mult": 1.5,
        },
    },
    "high": {
        "label": "🟠 High",
        "description": "High risk, high reward",
        "overrides": {
            "house_edge": 20, "win_chance": 30, "multiplier": 2.0,
            "low_crash_chance": 20, "med_crash_chance": 50, "high_crash_chance": 75,
            "police_chance": 12, "reward_min_mult": 1.0,
        },
    },
    "extreme": {
        "label": "🔴 Extreme",
        "description": "Maximum risk, maximum reward",
        "overrides": {
            "house_edge": 35, "win_chance": 15, "multiplier": 3.0,
            "low_crash_chance": 30, "med_crash_chance": 60, "high_crash_chance": 85,
            "police_chance": 20, "reward_min_mult": 0.5,
        },
    },
    "custom": {
        "label": "⚫ Custom",
        "description": "Manual configuration",
        "overrides": {},
    },
}


# =========================================================
# DATABASE OPERATIONS
# =========================================================

def setup_game_config_indexes():
    col = _col("game_configs")
    col.create_index([("game_id", ASCENDING)], unique=True)
    col.create_index([("updated_at", ASCENDING)])


def get_game_config(game_id):
    cached = _config_cache.get(game_id)
    if cached and (time.time() - cached["_ts"]) < 300:
        return cached["config"]

    doc = _col("game_configs").find_one({"game_id": game_id})
    if doc:
        config = doc["config"]
        _config_cache[game_id] = {"config": config, "_ts": time.time()}
        return config
    return None


def save_game_config(game_id, config, preset="custom"):
    now = time.time()
    _col("game_configs").update_one(
        {"game_id": game_id},
        {"$set": {
            "game_id": game_id,
            "config": config,
            "preset": preset,
            "updated_at": now,
        }},
        upsert=True,
    )
    _config_cache[game_id] = {"config": config, "_ts": now}


def load_all_game_configs():
    configs = {}
    for doc in _col("game_configs").find():
        configs[doc["game_id"]] = doc["config"]
    return configs


def get_default_config(game_id):
    reg = GAME_REGISTRY.get(game_id)
    if not reg:
        return {}
    return {k: v["default"] for k, v in reg["params"].items()}


def init_all_defaults():
    for game_id in GAME_REGISTRY:
        if get_game_config(game_id) is None:
            default = get_default_config(game_id)
            save_game_config(game_id, default, preset="medium")
            print(f"  ✅ Initialized default config for {game_id}")


# =========================================================
# VALIDATION
# =========================================================

def validate_config(game_id, new_values):
    reg = GAME_REGISTRY.get(game_id)
    if not reg:
        return False, f"Unknown game: {game_id}"

    errors = []
    for key, val in new_values.items():
        param = reg["params"].get(key)
        if not param:
            errors.append(f"Unknown parameter: {key}")
            continue

        if param["type"] == "int":
            try:
                val = int(val)
            except (ValueError, TypeError):
                errors.append(f"{param['label']}: must be an integer")
                continue
            if val < param["min"] or val > param["max"]:
                errors.append(f"{param['label']}: must be between {param['min']} and {param['max']}")
        elif param["type"] == "float":
            try:
                val = float(val)
            except (ValueError, TypeError):
                errors.append(f"{param['label']}: must be a number")
                continue
            if val < param["min"] or val > param["max"]:
                errors.append(f"{param['label']}: must be between {param['min']} and {param['max']}")

    if errors:
        return False, "\n".join(errors)
    return True, "Valid"


def apply_preset(game_id, preset_name):
    preset = PRESETS.get(preset_name)
    if not preset:
        return False, f"Unknown preset: {preset_name}"

    defaults = get_default_config(game_id)
    overrides = {**defaults, **preset["overrides"]}

    valid, msg = validate_config(game_id, overrides)
    if not valid:
        return False, msg

    save_game_config(game_id, overrides, preset=preset_name)
    return True, f"Applied {preset['label']} preset to {game_id}"


def update_game_param(game_id, param_name, value):
    current = get_game_config(game_id)
    if current is None:
        current = get_default_config(game_id)

    new_values = {param_name: value}
    valid, msg = validate_config(game_id, new_values)
    if not valid:
        return False, msg

    reg = GAME_REGISTRY[game_id]
    param = reg["params"][param_name]
    if param["type"] == "int":
        current[param_name] = int(value)
    else:
        current[param_name] = float(value)

    save_game_config(game_id, current, preset="custom")
    return True, f"Updated {param_name} = {current[param_name]}"


# =========================================================
# HELP SYSTEM AUTO-REGISTRATION
# =========================================================

_ADMIN_COMMANDS = {}


def register_admin_command(cmd, handler, description="", syntax="", example="", permission="owner_sudo", category="general", notes=""):
    _ADMIN_COMMANDS[cmd] = {
        "handler": handler,
        "description": description,
        "syntax": syntax,
        "example": example,
        "permission": permission,
        "category": category,
        "notes": notes,
    }


def get_all_admin_commands():
    return dict(_ADMIN_COMMANDS)


def get_commands_by_category(category):
    return {k: v for k, v in _ADMIN_COMMANDS.items() if v["category"] == category}


def search_admin_commands(query):
    q = query.lower().strip()
    results = {}
    for cmd, info in _ADMIN_COMMANDS.items():
        if q in cmd.lower() or q in info["description"].lower() or q in info["category"].lower():
            results[cmd] = info
    return results
