import sqlite3, time, threading

from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from sqlalchemy import Text, ForeignKey, Numeric

db_lock = threading.Lock()

def get_conn():
    conn = sqlite3.connect("uno.db", timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")  # Write-Ahead Logging
    return conn

def setup_core_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                chat_id INTEGER,
                coins INTEGER DEFAULT 0,
                karma INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                locked_savings INTEGER DEFAULT 0,
                last_deposit_time INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deck (
                file_id TEXT PRIMARY KEY,
                json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                uid INTEGER,
                file_id TEXT,
                name TEXT,
                power TEXT,
                value INTEGER,
                rarity TEXT,
                drawn_at INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT UNIQUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tax_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER,
                timestamp INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_logs (
                uid INTEGER,
                game_name TEXT,
                timestamp INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_scores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                points INTEGER DEFAULT 0
            )
        """)
    with get_conn() as conn:
        conn.execute("""
           CREATE TABLE IF NOT EXISTS groups (
               gid INTEGER PRIMARY KEY,
               title TEXT,
               added_at INTEGER
            )
        """)
    conn.commit()

def get_all_group_ids():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT chat_id FROM groups").fetchall()]



def add_user(uid, username, chat_id=None):
    clean = username.lstrip("@ ").strip()
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, username, chat_id) VALUES (?, ?, ?)", (uid, clean, chat_id))
        conn.execute("UPDATE users SET username = ?, chat_id = ? WHERE id = ?", (clean, chat_id, uid))
        conn.commit()


def get_username(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()
        return row[0] if row and row[0] else "Unknown"

def get_balance(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT coins FROM users WHERE id = ?", (uid,)).fetchone()
        return row[0] if row else 0

def set_balance(uid, amount):
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET coins = ? WHERE id = ?", (amount, uid))
            conn.commit()

def update_balance(uid, amount):
    for attempt in range(3):
        try:
            with db_lock:
                with get_conn() as conn:
                    conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, uid))
                    conn.commit()
                    print(f"âœ… Updated balance for UID {uid} by â‚¹{amount}")
                    return True
        except sqlite3.OperationalError:
            print(f"âš ï¸ Attempt {attempt+1}: DB locked for UID {uid}, retrying...")
            time.sleep(1)
    print(f"âŒ Failed to update balance for UID {uid}")
    return False

def get_bank_balance(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT bank FROM users WHERE id = ?", (uid,)).fetchone()
        return row[0] if row else 0

def update_bank(uid, amount):
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET bank = bank + ? WHERE id = ?", (amount, uid))
            conn.commit()

def set_bank(uid, amount):
    for attempt in range(3):
        try:
            with db_lock:
                conn = get_conn()
                conn.execute("UPDATE users SET bank = ? WHERE id = ?", (amount, uid))
                conn.commit()
                conn.close()
                print(f"âœ… Bank cleared for UID {uid}")
                return True
        except sqlite3.OperationalError:
            print(f"âš ï¸ Attempt {attempt+1}: DB locked during set_bank, retrying...")
            time.sleep(1)
    print(f"âŒ Failed to clear bank for UID {uid}")
    return False

def deposit_tax(amount):
    for attempt in range(3):
        try:
            with db_lock:
                with get_conn() as conn:
                    conn.execute("INSERT INTO tax_bank (amount, timestamp) VALUES (?, ?)", (amount, int(time.time())))
                    conn.commit()
                    print(f"âœ… Deposited â‚¹{amount} into tax bank")
                    return True
        except sqlite3.OperationalError:
            print(f"âš ï¸ Attempt {attempt+1}: DB locked during tax deposit, retrying...")
            time.sleep(1)
    print(f"âŒ Failed to deposit tax after retries")
    return False

def add_admin(username):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (username) VALUES (?)", (username,))
        conn.commit()

def remove_admin(username):
    with get_conn() as conn:
        conn.execute("DELETE FROM admins WHERE username = ?", (username,))
        conn.commit()

def get_admin_list():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT username FROM admins").fetchall()]


def setup_bank_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                chat_id INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner_uid INTEGER,
                created_at INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_members (
                uid INTEGER PRIMARY KEY,
                bank_id INTEGER,
                joined_at INTEGER
            )
        """)
        conn.commit()

def migrate_users_table():
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN chat_id INTEGER")
            conn.commit()
            print("âœ… chat_id column added to users table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("â„¹ï¸ chat_id column already exists.")
            else:
                raise

def backfill_chat_ids(default_chat_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET chat_id = ?
            WHERE chat_id IS NULL
        """, (default_chat_id,))
        conn.commit()
        print(f"ðŸ§¹ Backfilled chat_id for legacy users with {default_chat_id}")


def force_patch_all_users(chat_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET chat_id = ?", (chat_id,))
        conn.commit()
        print(f"ðŸ› ï¸ Force patched all users with chat_id {chat_id}")

def debug_users_by_chat(chat_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT id, username, chat_id FROM users WHERE chat_id = ?", (chat_id,)).fetchall()
        print(f"ðŸ“Š Found {len(rows)} users with chat_id {chat_id}")
        for row in rows:
            print(f"ðŸ§¾ {row}")


def ensure_system_bank():
    with get_conn() as conn:
        row = conn.execute("SELECT bank_id FROM banks WHERE name = 'System Vault'").fetchone()
        if not row:
            conn.execute("""
                INSERT INTO banks (name, owner_uid, created_at)
                VALUES ('System Vault', 0, strftime('%s', 'now'))
            """)
            conn.commit()


def setup_bank_extra_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_reserves (
                bank_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER,
                uid INTEGER,
                action TEXT,
                amount INTEGER,
                timestamp INTEGER
            )
        """)
        conn.commit()

def setup_banktax_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banktax (
                id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def ensure_system_account():
    with db_lock:
        with get_conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO users (id, coins)
                VALUES (?, ?)
            """, (999, 0))
            conn.commit()


import sqlite3
from contextlib import contextmanager
import os

DB_PATH = os.getenv("CLAN_DB_PATH", "clan_bot.db")

@contextmanager
def get_conn():
    """
    Contextâ€manager for SQLite connections.
    Commits on exit and closes automatically.
    """
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def setup_clan_tables():
    """
    Creates (and migrates) all clan-related tables:
      - clans
      - clan_members
      - clan_goals
      - clan_votes
    Ensures composite PKs and backfills missing columns.
    """
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            founder_id  INTEGER NOT NULL,
            created_at  INTEGER NOT NULL
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_members (
            clan_id    INTEGER NOT NULL,
            uid        INTEGER NOT NULL,
            username   TEXT    NOT NULL DEFAULT '',
            title      TEXT    NOT NULL DEFAULT 'Member',
            joined_at  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(clan_id, uid)
        )
        """)

        existing_cols = {col[1] for col in conn.execute("PRAGMA table_info(clan_members)").fetchall()}
        if 'username' not in existing_cols:
            conn.execute("""
            ALTER TABLE clan_members
            ADD COLUMN username TEXT NOT NULL DEFAULT ''
            """)
        if 'title' not in existing_cols:
            conn.execute("""
            ALTER TABLE clan_members
            ADD COLUMN title TEXT NOT NULL DEFAULT 'Member'
            """)
        if 'joined_at' not in existing_cols:
            conn.execute("""
            ALTER TABLE clan_members
            ADD COLUMN joined_at INTEGER NOT NULL DEFAULT 0
            """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_goals (
            clan_id   INTEGER NOT NULL,
            goal_name TEXT    NOT NULL,
            progress  INTEGER NOT NULL DEFAULT 0,
            target    INTEGER NOT NULL,
            PRIMARY KEY(clan_id, goal_name)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_votes (
            clan_id    INTEGER NOT NULL,
            voter_uid  INTEGER NOT NULL,
            target_uid INTEGER NOT NULL,
            PRIMARY KEY(clan_id, voter_uid, target_uid)
        )
        """)


def initialize_database():
    """
    Call this on bot start to ensure your schema is upâ€toâ€date.
    """
    setup_clan_tables()


if __name__ == "__main__":
    initialize_database()
    print(f"âœ… Clan database initialised at '{DB_PATH}'")

# === Game & Word Scores ===
def track_game(uid, game_name):
    with get_conn() as conn:
        conn.execute("INSERT INTO game_logs (uid, game_name, timestamp) VALUES (?, ?, ?)", (uid, game_name, int(time.time())))
        conn.commit()

def get_user_stats(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT coins, karma FROM users WHERE id=?", (uid,)).fetchone()
        return {"coins": row[0], "karma": row[1]} if row else None

def get_locked_savings(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT locked_savings FROM users WHERE id=?", (uid,)).fetchone()
        return row[0] if row else 0

def apply_interest(uid, rate=0.05):
    with db_lock:
        with get_conn() as conn:
            row = conn.execute("SELECT coins FROM users WHERE id=?", (uid,)).fetchone()
            if not row:
                return False
            interest = int(row[0] * rate)
            conn.execute("UPDATE users SET coins = coins + ? WHERE id=?", (interest, uid))
            conn.commit()
            return interest

def setup_word_scores():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_scores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                points INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def transfer_coins(sender_id, receiver_id, amount):
    with db_lock:
        with get_conn() as conn:
            sender = conn.execute("SELECT coins FROM users WHERE id = ?", (sender_id,)).fetchone()
            receiver = conn.execute("SELECT coins FROM users WHERE id = ?", (receiver_id,)).fetchone()

            if not sender or not receiver or sender[0] < amount:
                return False

            conn.execute("UPDATE users SET coins = coins - ? WHERE id = ?", (amount, sender_id))
            conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, receiver_id))
            conn.commit()
            return True

def purge_users():
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM users")
            conn.commit()

def get_all_user_ids():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT id FROM users").fetchall()]

def get_user_by_username(username):
    clean = username.lstrip("@ ").strip()
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE LOWER(username)=LOWER(?)", (clean,)).fetchone()
        return row[0] if row else None

def get_all_users():
    with get_conn() as conn:
        return conn.execute("SELECT id, username, coins FROM users ORDER BY coins DESC").fetchall()

def remove_user_by_id(uid):
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
            conn.commit()

def remove_user_by_username(username):
    clean = username.lstrip("@ ").strip()
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM users WHERE LOWER(username)=LOWER(?)", (clean,))
            conn.commit()

def get_low_balance_users(threshold=10):
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT username FROM users WHERE coins < ?", (threshold,)).fetchall()]

def get_leaderboard():
    with get_conn() as conn:
        return conn.execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 5").fetchall()

def get_ref_reward():
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'ref_reward'").fetchone()
        return int(row[0]) if row else 50  # Default reward


def setup_mines_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mines_games (
                uid INTEGER PRIMARY KEY,
                bet INTEGER,
                bombs INTEGER,
                revealed TEXT,
                bomb_positions TEXT,
                started_at INTEGER
            )
        """)
        conn.commit()

def setup_mines_cooldown_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mines_cooldowns (
                uid INTEGER PRIMARY KEY,
                last_played INTEGER
            )
        """)
        conn.commit()


def setup_showroom_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS showroom_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                price INTEGER,
                photo_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_showroom (
                uid INTEGER,
                item_id INTEGER,
                bought_at INTEGER
            )
        """)
        conn.commit()

def setup_game_cooldowns():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_cooldowns (
                uid INTEGER,
                game TEXT,
                last_played INTEGER,
                PRIMARY KEY (uid, game)
            )
        """)
        conn.commit()


def setup_user_stats():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                uid INTEGER PRIMARY KEY,
                coins_earned INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def add_earnings(uid: int, amount: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_stats (uid, coins_earned)
            VALUES (?, ?)
            ON CONFLICT(uid) DO UPDATE SET coins_earned = coins_earned + ?
        """, (uid, amount, amount))
        conn.commit()

def setup_marketplace():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_listings (
                listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_id INTEGER,
                price INTEGER,
                listed_at INTEGER
            )
        """)
        conn.commit()

def setup_pet_system():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_pets (
                uid INTEGER PRIMARY KEY,
                pet_name TEXT,
                pet_type TEXT,
                level INTEGER DEFAULT 1,
                hunger INTEGER DEFAULT 100
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pet_battles (
                uid INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0
            )
        """)
        conn.commit()


from datetime import datetime, timedelta

bribe_status = {}  

def set_bribe(uid):
    until = datetime.now() + timedelta(minutes=10)
    bribe_status[uid] = until

def is_bribed(uid):
    return datetime.now() < bribe_status.get(uid, datetime.min)


def mark_bribed(uid: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET bribed = 1 WHERE id = ?", (uid,))
        conn.commit()

def add_bribed_column():
    with get_conn() as conn:
        columns = conn.execute("PRAGMA table_info(users)").fetchall()
        if not any(col[1] == "bribed" for col in columns):
            conn.execute("ALTER TABLE users ADD COLUMN bribed INTEGER DEFAULT 0")
            conn.commit()

def debug_user_schema():
    with get_conn() as conn:
        rows = conn.execute("PRAGMA table_info(users)").fetchall()
        for row in rows:
            print(row)


def debug_tax_pool_schema():
    with get_conn() as conn:
        rows = conn.execute("PRAGMA table_info(tax_pool)").fetchall()
        for row in rows:
            print(row)

def add_amount_column_to_tax_pool():
    with db_lock:
        with get_conn() as conn:
            conn.execute("ALTER TABLE tax_pool ADD COLUMN amount INTEGER DEFAULT 0")
            conn.commit()

def save_username(uid: int, username: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET username = ?
            WHERE uid = ?
        """, (username, uid))
        conn.commit()



group_config = {}  

def set_group_config(chat_id, key, value):
    if chat_id not in group_config:
        group_config[chat_id] = {}
    group_config[chat_id][key] = value

def get_group_config(chat_id, key):
    return group_config.get(chat_id, {}).get(key)



def ensure_market_trades_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER,
                seller_id INTEGER,
                item_id INTEGER,
                price INTEGER,
                timestamp INTEGER
            )
        """)
        conn.commit()


def get_user_showroom(user_id):
    with get_conn() as conn:
        result = conn.execute("""
            SELECT bike_id, model, price FROM bikes
            WHERE user_id = ?
        """, (user_id,))
        return [dict(row) for row in result.fetchall()]

def remove_bike_by_id(bike_id):
    with get_conn() as conn:
        result = conn.execute("DELETE FROM bikes WHERE bike_id = ?", (bike_id,))
        return result.rowcount > 0


def get_all_vehicle_owners():
    with get_conn() as conn:
        result = conn.execute("""
            SELECT DISTINCT u.user_id, u.username
            FROM users u
            WHERE u.user_id IN (
                SELECT user_id FROM bikes
                UNION
                SELECT user_id FROM cars
            )
        """)
        return [dict(row) for row in result.fetchall()]



class Loan(Base):
    __tablename__ = "loans"
    uid = Column(BigInteger, primary_key=True)
    amount = Column(Float)
    interest = Column(Float)
    total_due = Column(Float)
    loan_time = Column(DateTime)
    repaid = Column(Boolean, default=False)
    daily_deduction_started = Column(Boolean, default=False)
    last_deduction_time = Column(DateTime, nullable=True)


def ensure_loans_table():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            uid INTEGER PRIMARY KEY,
            amount INTEGER NOT NULL,
            interest INTEGER NOT NULL,
            total_due INTEGER NOT NULL,
            loan_time TEXT NOT NULL,
            repaid INTEGER DEFAULT 0,
            daily_deduction_started INTEGER DEFAULT 0,
            last_deduction_time TEXT,
            deductions_done INTEGER DEFAULT 0
        )
        """)
        conn.commit()


import sqlite3

def get_conn():
    conn = sqlite3.connect("uno.db")  
    conn.row_factory = sqlite3.Row    
    return conn

with get_conn() as conn:
    conn.execute("DROP TABLE IF EXISTS groups")
    conn.execute("""
        CREATE TABLE groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT
        )
    """)
    conn.commit()


def ensure_user_memory_table():
    """
    Creates the user_memory table if it doesn't exist.
    Call this on startup, before you start handling updates.
    """
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            uid         INTEGER NOT NULL,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()


def ensure_user_showroom_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_showroom (
                uid INTEGER,
                item_id INTEGER,
                bought_at INTEGER,
                PRIMARY KEY (uid, item_id)
            )
        """)
        conn.commit()


def ensure_user_listings_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_listings (
                listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_id INTEGER,
                price INTEGER,
                listed_at INTEGER
            )
        """)
        conn.commit()

