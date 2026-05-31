import datetime
from database import get_conn

def setup_user_daily_stats():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_stats (
                id INTEGER,
                date TEXT,
                games_played INTEGER DEFAULT 0,
                coins_earned INTEGER DEFAULT 0,
                cards_received INTEGER DEFAULT 0,
                wisdom_points INTEGER DEFAULT 0,
                time_spent INTEGER DEFAULT 0,
                PRIMARY KEY (id, date)
            )
        """)

def track_user_activity(id, field, amount=1):
    today = datetime.date.today().isoformat()
    with get_conn() as conn:
        conn.execute(f"""
            INSERT INTO user_daily_stats (id, date, {field})
            VALUES (?, ?, ?)
            ON CONFLICT(id, date) DO UPDATE SET
                {field} = {field} + ?
        """, (id, today, amount, amount))
        conn.commit()

def get_user_daily_summary(id):
    today = datetime.date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("""
            SELECT games_played, coins_earned, cards_received, wisdom_points, time_spent
            FROM user_daily_stats
            WHERE id = ? AND date = ?
        """, (id, today)).fetchone()
    return row or (0, 0, 0, 0, 0)
