from user_stats import track_user_activity

def log_game(uid):
    track_user_activity(uid, "games_played")

def log_coins(uid, amount):
    track_user_activity(uid, "coins_earned", amount)

def log_card(uid):
    track_user_activity(uid, "cards_received")

def log_wisdom(uid):
    track_user_activity(uid, "wisdom_points")

def log_time(uid, seconds):
    track_user_activity(uid, "time_spent", seconds)
