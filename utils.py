import time
from database import get_conn, db_lock

def check_cooldown(uid: int, game: str, cooldown_seconds: int = 300) -> int:
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute("SELECT last_played FROM game_cooldowns WHERE uid = ? AND game = ?", (uid, game)).fetchone()
        if row:
            last = row[0]
            remaining = cooldown_seconds - (now - last)
            return max(0, remaining)
    return 0

def update_cooldown(uid: int, game: str):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO game_cooldowns (uid, game, last_played)
            VALUES (?, ?, ?)
        """, (uid, game, now))
        conn.commit()

