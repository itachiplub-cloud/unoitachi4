import asyncio
import sqlite3
import time
import random
import json

from config import DB_PATH as DB_NAME

import os

def get_conn():
    """
    Opens a connection to the cards SQLite database with auto-recovery.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        # Test the connection to ensure it is a valid database
        conn.execute("SELECT 1")
        return conn
    except sqlite3.DatabaseError as e:
        print(f"⚠️ Database error on {DB_NAME}: {e}")
        if "file is not a database" in str(e) or "corrupt" in str(e).lower():
            print(f"⚠️ Database {DB_NAME} is corrupted. Attempting auto-recovery...")
            if os.path.exists(DB_NAME):
                backup_path = f"{DB_NAME}.corrupted.{int(time.time())}"
                try:
                    os.rename(DB_NAME, backup_path)
                    print(f"📦 Backed up corrupted database to {backup_path}")
                except Exception as rename_err:
                    print(f"❌ Failed to rename corrupted database: {rename_err}")
                    raise e
            
            try:
                print(f"🔄 Creating new database {DB_NAME}...")
                conn = sqlite3.connect(DB_NAME)
                return conn
            except Exception as retry_err:
                print(f"❌ Auto-recovery failed: {retry_err}")
                raise
        else:
            raise

def setup_tables():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY,
                username TEXT,
                karma INTEGER DEFAULT 0,
                last_active INTEGER DEFAULT 0
            )
        """)
        c.execute("CREATE TABLE IF NOT EXISTS balance (uid INTEGER PRIMARY KEY, coins INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS deck (file_id TEXT PRIMARY KEY, json TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS transfer_log (sender INTEGER, receiver INTEGER, amount INTEGER, timestamp INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS earn_log (uid INTEGER PRIMARY KEY, last_earned INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS duel_stats (uid INTEGER PRIMARY KEY, wins INTEGER, losses INTEGER, draws INTEGER)")
        conn.commit()

def setup_card_table():
    with get_conn() as conn:
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



def create_streak_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS streaks (
                uid INTEGER PRIMARY KEY,
                streak_day INTEGER,
                last_claimed INTEGER
            )
        """)
        conn.commit()

def create_duel_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duels (
                challenger INTEGER,
                opponent INTEGER,
                result TEXT,
                timestamp INTEGER
            )
        """)
        conn.commit()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY,
                username TEXT,
                coins INTEGER DEFAULT 0,
                karma INTEGER DEFAULT 0
               
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
            CREATE TABLE IF NOT EXISTS duels (
                challenger TEXT,
                opponent TEXT,
                result TEXT,
                timestamp INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS streaks (
                uid INTEGER PRIMARY KEY,
                streak_day INTEGER,
                last_claimed INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS blessings (
                uid INTEGER,
                blessing TEXT,
                received_at INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tomb (
                uid INTEGER,
                name TEXT,
                rarity TEXT,
                sacrificed_at INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS relics (
                uid INTEGER,
                name TEXT,
                power TEXT,
                value INTEGER,
                rarity TEXT,
                forged_at INTEGER
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_artefacts (
                uid INTEGER,
                name TEXT,
                effect TEXT,
                acquired_at INTEGER
            )
        """)

        conn.commit()


def draw_card():
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()

    valid_cards = []
    for file_id, raw_json in rows:
        if not file_id or file_id == "None" or len(file_id) < 10:
            continue
        try:
            card = json.loads(raw_json)
            card["file_id"] = file_id
            valid_cards.append(card)
        except:
            continue

    if not valid_cards:
        return {
            "file_id": "None",
            "name": "Broken Card",
            "power": "0",
            "value": 0,
            "rarity": "common",
            "cost": 0
        }

    return random.choice(valid_cards)


def draw_card_by_rarity():
    rarity = random.choices(
        population=["legendary", "rare", "common"],
        weights=[3, 27, 70],
        k=1
    )[0]

    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()

    valid_cards = []
    for file_id, raw_json in rows:
        if not file_id or file_id == "None" or len(file_id) < 10:
            continue
        try:
            card = json.loads(raw_json)
            if card.get("rarity", "common").lower() == rarity:
                card["file_id"] = file_id
                valid_cards.append(card)
        except:
            continue

    if not valid_cards:
        return {
            "file_id": "None",
            "name": "Broken Card",
            "power": "0",
            "value": 0,
            "rarity": rarity,
            "cost": 0
        }

    return random.choice(valid_cards)



def get_karma(uid):
    with get_conn() as conn:
        result = conn.execute("SELECT karma FROM users WHERE uid=?", (uid,)).fetchone()
        return result[0] if result else 0

def update_karma(uid, new_value):
    with get_conn() as conn:
        conn.execute("UPDATE users SET karma=? WHERE uid=?", (new_value, uid))
        conn.commit()

def format_karma(k):
    if k < 100:
        return f"⭐ {k}"
    elif k < 1_000:
        return f"🌟 {k}"
    elif k < 1_000_000:
        return f"🔥 {k // 1_000}K"
    else:
        return f"⚡ {k:.2e}"

def ensure_karma_column():
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN karma INTEGER DEFAULT 0")
            print("✅ karma column added.")
        except sqlite3.OperationalError:
            print("⚠️ karma column already exists or failed.")
        conn.commit()

def get_balance(uid):
    with get_conn() as conn:
        result = conn.execute("SELECT coins FROM balance WHERE uid=?", (uid,)).fetchone()
        return result[0] if result else 0

def update_balance(uid, amount, overwrite=False):
    with get_conn() as conn:
        current = amount if overwrite else get_balance(uid) + amount
        conn.execute("REPLACE INTO balance (uid, coins) VALUES (?, ?)", (uid, current))

def setup_earn_times_table():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS earn_times (
            uid INTEGER PRIMARY KEY,
            last_claimed INTEGER
        )
        """)
        conn.commit()

setup_earn_times_table()

def add_card(file_id, json_data):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO deck (file_id, json) VALUES (?, ?)", (file_id, json_data))
        return True

def get_card_by_index(index):
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()
        print(f"[DEBUG] Total cards in DB: {len(rows)}")
        if 0 <= index < len(rows):
            try:
                card = json.loads(rows[index][1])
                print(f"[DEBUG] Card #{index} loaded: {card}")
                return card
            except Exception as e:
                print(f"[ERROR] Failed to load card #{index}: {e}")
                return None
        return None

def remove_card_by_index(index):
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()
        if 0 <= index < len(rows):
            file_id, raw_json = rows[index]
            try:
                card = json.loads(raw_json)
                name = card.get("name", "")
                conn.execute("DELETE FROM deck WHERE file_id=?", (file_id,))
                conn.commit()
                return name
            except:
                return None
        return None


def remove_card(file_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM deck WHERE file_id=?", (file_id,))

def remove_card_by_name(name):
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()
        for file_id, raw_json in rows:
            try:
                card = json.loads(raw_json)
                if card.get("name", "").lower() == name.lower():
                    conn.execute("DELETE FROM deck WHERE file_id=?", (file_id,))
                    conn.commit()
                    return True
            except Exception as e:
                continue
    return False


def get_deck_size(uid=None):
    with get_conn() as conn:
        if uid is None:
            result = conn.execute("SELECT COUNT(*) FROM deck").fetchone()
        else:
            result = conn.execute("SELECT COUNT(*) FROM user_cards WHERE uid=?", (uid,)).fetchone()
        return result[0] if result else 0


def list_all_cards():
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck ORDER BY rowid").fetchall()
        cards = []
        for file_id, raw_json in rows:
            try:
                card = json.loads(raw_json)
                card["file_id"] = file_id  # ✅ Preserve file_id for editing
                cards.append(card)
            except:
                continue
        return cards


def get_random_card():
    """
    Returns a card based on rarity probabilities.
    If no matching rarity is found, falls back to random from all.
    Rarity chances:
        - Common:    70%
        - Rare:      27%
        - Legendary: 3%
    """

    cards = list_all_cards()
    if not cards:
        return {
            "name": "Void Pulse",
            "power": "none",
            "value": 0,
            "rarity": "common",
            "cost": 0,
            "file_id": None
        }

    roll = random.uniform(0, 100)
    if roll <= 3:
        rarity = "legendary"
    elif roll <= 30:  # 3 + 27
        rarity = "rare"
    else:
        rarity = "common"

    filtered = [c for c in cards if c.get("rarity", "").lower() == rarity]
    if filtered:
        return random.choice(filtered)

    return random.choice(cards)


def get_user_relics(uid):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT name, power, value, rarity
            FROM relics
            WHERE uid=?
        """, (uid,)).fetchall()

    relics = []
    for name, power, value, rarity in rows:
        relics.append({
            "name": name,
            "power": power,
            "value": value,
            "rarity": rarity
        })
    return relics


def get_user_artefacts(uid):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT name, effect
            FROM user_artefacts
            WHERE uid=?
        """, (uid,)).fetchall()

    artefacts = []
    for name, effect in rows:
        artefacts.append({
            "name": name,
            "effect": effect
        })
    return artefacts


def apply_rarity_bonus(card):
    rarity = card.get("rarity", "common").lower()
    base_value = card.get("value", 0)
    boost_map = {
        "uncommon": 0.10,
        "rare": 0.25,
        "epic": 0.40,
        "legendary": 0.60,
        "mythic": 0.75,
        "divine": 0.90,
        "shadow": 1.20
    }
    bonus = int(base_value * boost_map.get(rarity, 0))
    card["value"] = base_value + bonus
    return card

def can_earn(uid, cooldown=86400):  
    with get_conn() as conn:
        result = conn.execute("SELECT last_earned FROM earn_log WHERE uid=?", (uid,)).fetchone()
        now = int(time.time())
        if not result or now - result[0] >= cooldown:
            conn.execute("REPLACE INTO earn_log (uid, last_earned) VALUES (?, ?)", (uid, now))
            return True
        return False

def update_earn_time(uid, timestamp=None):
    with get_conn() as conn:
        if timestamp is None:
            timestamp = int(time.time())
        conn.execute("REPLACE INTO earn_log (uid, last_earned) VALUES (?, ?)", (uid, timestamp))

def log_transfer(sender, receiver, amount):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transfer_log (sender, receiver, amount, timestamp) VALUES (?, ?, ?, ?)",
            (sender, receiver, amount, int(time.time()))
        )

def get_transfer_logs(limit=10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT sender, receiver, amount, timestamp FROM transfer_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()

def track_user(uid, username):
    timestamp = int(time.time())

    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY,
                username TEXT,
                karma INTEGER DEFAULT 0,
                last_active INTEGER,
                coins INTEGER DEFAULT 0
            )
        """)

        conn.execute("""
            INSERT OR REPLACE INTO users (uid, username, karma, last_active, coins)
            VALUES (
                ?, ?, 
                COALESCE((SELECT karma FROM users WHERE uid=?), 0),
                ?, 
                COALESCE((SELECT coins FROM users WHERE uid=?), 0)
            )
        """, (uid, username, uid, timestamp, uid))


def get_recent_users(seconds=300):
    now = int(time.time())
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username FROM users WHERE ? - last_active < ?",
            (now, seconds)
        ).fetchall()
        return [f"@{r[0]}" for r in rows if r[0]]

def get_username(uid):
    with get_conn() as conn:
        result = conn.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
        return result[0] if result and result[0] else "None"

def ensure_last_active_column():
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_active INTEGER DEFAULT 0")
            print("✅ last_active column added.")
        except sqlite3.OperationalError:
            print("⚠️ last_active column already exists or failed.")
        conn.commit()


async def track_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        chat_id = chat.id
        title = chat.title or "Unnamed"

        def _track_group_sync():
            with get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS known_groups (
                        chat_id INTEGER PRIMARY KEY,
                        title TEXT
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO known_groups (chat_id, title)
                    VALUES (?, ?)
                """, (chat_id, title))
                conn.commit()

        await asyncio.to_thread(_track_group_sync)


async def track_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type in ["group", "supergroup"]:
        chat_id = chat.id
        user_id = user.id
        username = user.username or user.first_name
        now = int(time.time())

        def _track_activity_sync():
            with get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_users (
                        chat_id INTEGER,
                        user_id INTEGER,
                        username TEXT,
                        last_seen INTEGER,
                        PRIMARY KEY (chat_id, user_id)
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO active_users (chat_id, user_id, username, last_seen)
                    VALUES (?, ?, ?, ?)
                """, (chat_id, user_id, username, now))
                conn.commit()

        await asyncio.to_thread(_track_activity_sync)





def get_duel_rank(identifier=None, limit=10):
    with get_conn() as conn:
        if identifier is None:
            rows = conn.execute("""
                SELECT challenger, COUNT(*) AS wins
                FROM duels
                WHERE result = 'win'
                GROUP BY challenger
                ORDER BY wins DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return rows

        if isinstance(identifier, int):
            rows = conn.execute("""
                SELECT COUNT(*) AS wins,
                       SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) AS losses,
                       SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) AS draws
                FROM duels
                WHERE challenger = ? OR opponent = ?
            """, (identifier, identifier)).fetchone()
            return rows

        if isinstance(identifier, str):
            row = conn.execute("SELECT id FROM users WHERE username = ?", (identifier,)).fetchone()
            if not row:
                return (0, 0, 0)
            uid = row[0]
            return get_duel_rank(uid)

        return (0, 0, 0)


def setup_tax_bank():
    """Create table to store all taxed coins."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tax_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER,
                timestamp INTEGER
            )
        """)
        conn.commit()

def deposit_tax(amount: int):
    """Add a taxed amount into the tax_bank."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tax_bank (amount, timestamp) VALUES (?, ?)",
            (amount, int(time.time()))
        )
        conn.commit()

def distribute_tax_rewards() -> str:
    """
    Sum the tax_bank, split equally to top 5 coin holders,
    then clear the pool.
    """
    from database import get_all_user_ids, update_balance, get_balance

    with get_conn() as conn:
        total = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()[0] or 0
        if total == 0:
            return "🚫 Tax pool is empty."

        all_ids = get_all_user_ids()
        board = sorted(
            [(uid, get_balance(uid)) for uid in all_ids],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        if not board:
            return "🚫 No users to reward."

        share = total // len(board)
        for uid, _ in board:
            update_balance(uid, share)

        conn.execute("DELETE FROM tax_bank")
        conn.commit()

    return f"🏆 Distributed {total} coins: {share} each to top {len(board)} users."


def get_tax_pool():
    with get_conn() as conn:
        result = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()
        return result[0] if result and result[0] else 0


def add_to_tax_pool(amount: int):
    import sqlite3
    from config import BANK_DB_PATH
    conn = sqlite3.connect(BANK_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tax_pool (
            id INTEGER PRIMARY KEY,
            total_tax INTEGER
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO tax_pool (id, total_tax) VALUES (1, 0)")
    cursor.execute("UPDATE tax_pool SET total_tax = total_tax + ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()

    print(f"✅ Added ₹{amount} to tax pool")


def init_tax_pool():
   
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tax_pool (
                id INTEGER PRIMARY KEY,
                total_tax INTEGER
            )
        """)
        conn.execute("INSERT OR IGNORE INTO tax_pool (id, total_tax) VALUES (1, 0)")


def sell_asset(uid: int, sale_price: int):
    tax = int(sale_price * 0.05)
    net_amount = sale_price - tax

    update_balance(uid, net_amount)
    add_to_tax_pool(tax)

def get_duel_stats(uid):
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duel_stats (
                uid INTEGER PRIMARY KEY,
                wins INTEGER,
                losses INTEGER,
                draws INTEGER
            )
        """)
        row = conn.execute("SELECT wins, losses, draws FROM duel_stats WHERE uid=?", (uid,)).fetchone()
        if row:
            return {"wins": row[0], "losses": row[1], "draws": row[2]}
        else:
            return {"wins": 0, "losses": 0, "draws": 0}

def update_duel_stats(uid, own_power, enemy_power):
    stats = get_duel_stats(uid)
    if own_power > enemy_power:
        stats["wins"] += 1
    elif own_power < enemy_power:
        stats["losses"] += 1
    else:
        stats["draws"] += 1

    with get_conn() as conn:
        conn.execute(
            "REPLACE INTO duel_stats (uid, wins, losses, draws) VALUES (?, ?, ?, ?)",
            (uid, stats["wins"], stats["losses"], stats["draws"])
        )


def get_user_inventory(uid: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT name, power, value, rarity
            FROM user_cards
            WHERE uid = ?
        """, (uid,)).fetchall()

    inventory = []
    for name, power, value, rarity in rows:
        inventory.append({
            "name": name,
            "power": power,
            "value": value,
            "rarity": rarity
        })

    return inventory


def save_card_to_user(uid: int, card: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_cards (uid, file_id, name, power, value, rarity, drawn_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            card.get("file_id", ""),  # Optional: use empty string if no image
            card.get("name"),
            card.get("power"),
            card.get("value"),
            card.get("rarity"),
            int(time.time())
        ))
        conn.commit()



