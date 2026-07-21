import sqlite3
import time
import threading
import os
import shutil
import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta

# =========================================================
# DATABASE CONFIGURATION
# =========================================================

db_lock = threading.Lock()
DB_PATH = os.getenv("CLAN_DB_PATH", "uno.db")
BACKUP_PATH = DB_PATH + ".backup"
BACKUP_INTERVAL = 1800  # 30 minutes
MAX_BACKUPS = 3

# =========================================================
# OWNER & ADMIN CONFIG
# =========================================================

import json as _json
try:
    with open("config.json", "r") as _f:
        _cfg = _json.load(_f)
except Exception:
    _cfg = {}

OWNER_ID = int(_cfg.get("OWNER_ID", 8055084559))
STATIC_ADMIN_IDS = set(_cfg.get("ADMIN_IDS", []))

def setup_sudo_admins_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sudo_admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at INTEGER,
                reason TEXT
            )
        """)
        conn.commit()

def add_sudo_admin(user_id, added_by=None, reason=None):
    setup_sudo_admins_table()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sudo_admins (user_id, added_by, added_at, reason) VALUES (?, ?, ?, ?)",
            (user_id, added_by, int(time.time()), reason)
        )
        conn.commit()

def remove_sudo_admin(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM sudo_admins WHERE user_id = ?", (user_id,))
        conn.commit()

def get_sudo_admin_ids():
    setup_sudo_admins_table()
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT user_id FROM sudo_admins").fetchall()]

def get_sudo_admin_details():
    setup_sudo_admins_table()
    with get_conn() as conn:
        return conn.execute(
            "SELECT user_id, added_by, added_at, reason FROM sudo_admins ORDER BY added_at DESC"
        ).fetchall()

def get_all_admin_ids():
    sudo_ids = set(get_sudo_admin_ids())
    return STATIC_ADMIN_IDS | sudo_ids

def is_bot_admin(user_id):
    if user_id == OWNER_ID:
        return True
    if user_id in STATIC_ADMIN_IDS:
        return True
    try:
        sudo_ids = set(get_sudo_admin_ids())
        return user_id in sudo_ids
    except Exception:
        return user_id in STATIC_ADMIN_IDS

def is_owner(user_id):
    return user_id == OWNER_ID

def setup_admin_tables():
    setup_sudo_admins_table()
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT PRIMARY KEY
            )
        """)
        conn.commit()

# =========================================================
# DATABASE BACKUP & RESTORE
# =========================================================

def _file_hash(path):
    """Quick hash to detect if backup is stale."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def backup_database():
    """Safe backup: WAL checkpoint + file copy. Keeps up to MAX_BACKUPS rotated copies."""
    try:
        if not os.path.exists(DB_PATH):
            print("⚠️ Backup skipped: main DB does not exist")
            return False

        with db_lock:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            conn.close()

        current_hash = _file_hash(DB_PATH)
        if os.path.exists(BACKUP_PATH):
            backup_hash = _file_hash(BACKUP_PATH)
            if current_hash == backup_hash:
                return True

        shutil.copy2(DB_PATH, BACKUP_PATH)

        wal_file = DB_PATH + "-wal"
        shm_file = DB_PATH + "-shm"
        if os.path.exists(wal_file):
            shutil.copy2(wal_file, BACKUP_PATH + "-wal")
        if os.path.exists(shm_file):
            shutil.copy2(shm_file, BACKUP_PATH + "-shm")

        for i in range(MAX_BACKUPS - 1, 0, -1):
            older = f"{BACKUP_PATH}.{i}"
            newer = f"{BACKUP_PATH}.{i + 1}"
            if os.path.exists(older):
                if os.path.exists(newer):
                    os.remove(newer)
                os.rename(older, newer)

        rotated = f"{BACKUP_PATH}.1"
        if os.path.exists(BACKUP_PATH):
            shutil.copy2(BACKUP_PATH, rotated)

        print(f"✅ Database backup completed: {BACKUP_PATH}")
        return True
    except Exception as e:
        print(f"⚠️ Backup failed: {e}")
        return False


def restore_from_backup():
    """Restore main DB from backup. Returns True if successful."""
    try:
        if not os.path.exists(BACKUP_PATH):
            print("⚠️ No backup file found to restore from")
            return False

        backup_size = os.path.getsize(BACKUP_PATH)
        if backup_size < 100:
            print("⚠️ Backup file too small, likely empty or corrupt")
            return False

        if os.path.exists(DB_PATH):
            corrupted = f"{DB_PATH}.corrupted.{int(time.time())}"
            try:
                os.rename(DB_PATH, corrupted)
                print(f"📦 Moved corrupted DB to {corrupted}")
            except Exception as e:
                print(f"⚠️ Could not move corrupted DB: {e}")

        shutil.copy2(BACKUP_PATH, DB_PATH)

        backup_wal = BACKUP_PATH + "-wal"
        backup_shm = BACKUP_PATH + "-shm"
        if os.path.exists(backup_wal):
            shutil.copy2(backup_wal, DB_PATH + "-wal")
        if os.path.exists(backup_shm):
            shutil.copy2(backup_shm, DB_PATH + "-shm")

        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if result and result[0] == "ok":
                print("✅ Restored from backup — integrity check passed")
                return True
            else:
                print(f"⚠️ Restored backup failed integrity check: {result}")
                os.remove(DB_PATH)
                return False
        except Exception as e:
            print(f"⚠️ Integrity check failed after restore: {e}")
            return False
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False


def _backup_scheduler():
    """Background loop that runs backup every BACKUP_INTERVAL seconds."""
    time.sleep(60)
    while True:
        try:
            backup_database()
        except Exception as e:
            print(f"⚠️ Backup scheduler error: {e}")
        time.sleep(BACKUP_INTERVAL)


def start_backup_scheduler():
    """Start the background backup thread (call once at startup)."""
    t = threading.Thread(target=_backup_scheduler, daemon=True, name="db-backup")
    t.start()
    print(f"🔄 DB backup scheduler started (interval: {BACKUP_INTERVAL}s)")


def get_backup_info():
    """Return info about the current backup state."""
    info = {"backup_exists": os.path.exists(BACKUP_PATH), "backup_size": 0, "backup_age": None}
    if info["backup_exists"]:
        info["backup_size"] = os.path.getsize(BACKUP_PATH)
        mtime = os.path.getmtime(BACKUP_PATH)
        info["backup_age"] = int(time.time() - mtime)
    return info

# =========================================================
# CONNECTION MANAGER (Enhanced from new DB)
# =========================================================

def sync_sqlite_to_mongodb(conn):
    try:
        # Check if modified_users table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='modified_users'")
        if not cursor.fetchone():
            return

        cursor.execute("SELECT uid FROM modified_users")
        rows = cursor.fetchall()
        if not rows:
            return

        uids = list(set([row[0] for row in rows if row[0] is not None]))
        if not uids:
            return

        from mongo_users import users_col

        for uid in uids:
            row = conn.execute("SELECT * FROM users WHERE id = ? OR uid = ?", (uid, uid)).fetchone()
            if row:
                user_dict = dict(row)
                if 'id' not in user_dict or user_dict['id'] is None:
                    user_dict['id'] = uid
                # Make sure fields are BSON serializable and delete DB specific row ID if present
                if 'rowid' in user_dict:
                    del user_dict['rowid']
                users_col.update_one({"id": uid}, {"$set": user_dict}, upsert=True)

        # Clear synced users from modified_users in the same transaction
        conn.execute("DELETE FROM modified_users WHERE uid IN (" + ",".join("?" for _ in uids) + ")", uids)
        conn.commit()
    except Exception as e:
        print(f"⚠️ Error in sync_sqlite_to_mongodb: {e}")

def setup_sync_triggers(conn):
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS modified_users (uid INTEGER PRIMARY KEY)")
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS user_update_trigger
            AFTER UPDATE ON users
            BEGIN
                INSERT OR IGNORE INTO modified_users (uid) VALUES (COALESCE(NEW.id, NEW.uid));
            END;
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS user_insert_trigger
            AFTER INSERT ON users
            BEGIN
                INSERT OR IGNORE INTO modified_users (uid) VALUES (COALESCE(NEW.id, NEW.uid));
            END;
        """)
        conn.commit()
        print("✅ SQLite triggers for user synchronization setup successfully.")
    except Exception as e:
        print(f"⚠️ Error setting up triggers: {e}")

@contextmanager
def get_conn():
    """Context manager for SQLite connections with proper error handling and auto-recovery."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        yield conn
        conn.commit()
        try:
            sync_sqlite_to_mongodb(conn)
        except Exception as sync_err:
            print(f"⚠️ Sync to mongo failed: {sync_err}")
    except sqlite3.DatabaseError as e:
        print(f"⚠️ Database error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
            try:
                conn.close()
            except:
                pass
            conn = None
        
        if "file is not a database" in str(e) or "corrupt" in str(e).lower():
            print("⚠️ Database file is corrupted or invalid. Attempting auto-recovery...")
            
            if restore_from_backup():
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA journal_mode=WAL;")
                    yield conn
                    conn.commit()
                    try:
                        sync_sqlite_to_mongodb(conn)
                    except Exception as sync_err:
                        print(f"⚠️ Sync to mongo failed: {sync_err}")
                    return
                except Exception as retry_err:
                    print(f"⚠️ Backup DB also failed: {retry_err}")
            
            if os.path.exists(DB_PATH):
                backup_path = f"{DB_PATH}.corrupted.{int(time.time())}"
                try:
                    os.rename(DB_PATH, backup_path)
                    print(f"📦 Moved failed DB to {backup_path}")
                except Exception as rename_err:
                    print(f"❌ Failed to rename database: {rename_err}")
                    raise e
            
            try:
                print("🔄 Creating new database...")
                conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                yield conn
                conn.commit()
                try:
                    sync_sqlite_to_mongodb(conn)
                except Exception as sync_err:
                    print(f"⚠️ Sync to mongo failed: {sync_err}")
            except Exception as retry_err:
                print(f"❌ Auto-recovery failed: {retry_err}")
                if conn:
                    conn.close()
                raise
        else:
            raise
    finally:
        if conn:
            conn.close()


def setup_groups_table():

    with get_conn() as conn:

        conn.execute("""
        CREATE TABLE IF NOT EXISTS groups (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            group_id INTEGER UNIQUE,
            group_name TEXT,

            added_by INTEGER,
            added_at INTEGER DEFAULT 0

        )
        """)

        conn.commit()

        print("✅ groups table ready")

def auto_fix_users_table():

    REQUIRED_COLUMNS = {

    "uid": "INTEGER",
    "id": "INTEGER",

    "username": "TEXT",
    "chat_id": "INTEGER",

    "coins": "INTEGER DEFAULT 0",
    "karma": "INTEGER DEFAULT 0",
    "bank": "INTEGER DEFAULT 0",

    "locked_savings": "INTEGER DEFAULT 0",
    "last_deposit_time": "INTEGER DEFAULT 0",

    "bribed": "INTEGER DEFAULT 0",
    "last_active": "INTEGER DEFAULT 0",

    "last_daily": "INTEGER DEFAULT 0",
    "last_weekly": "INTEGER DEFAULT 0",
    "last_monthly": "INTEGER DEFAULT 0",

    "last_draw_time": "INTEGER DEFAULT 0",
    "last_earn_time": "INTEGER DEFAULT 0",
    "last_work_time": "INTEGER DEFAULT 0",
    "last_rob_time": "INTEGER DEFAULT 0",
    "last_gamble_time": "INTEGER DEFAULT 0",
    "last_heist_time": "INTEGER DEFAULT 0",
    "last_crime_time": "INTEGER DEFAULT 0",
    "last_beg_time": "INTEGER DEFAULT 0",
    "last_hunt_time": "INTEGER DEFAULT 0",
    "last_dig_time": "INTEGER DEFAULT 0",
    "last_fish_time": "INTEGER DEFAULT 0",
    "last_mine_time": "INTEGER DEFAULT 0",
    "last_search_time": "INTEGER DEFAULT 0",

    "last_daily_claim": "INTEGER DEFAULT 0",
    "last_weekly_claim": "INTEGER DEFAULT 0",
    "last_monthly_claim": "INTEGER DEFAULT 0",

    "bank_balance": "INTEGER DEFAULT 0",
    "wallet": "INTEGER DEFAULT 0",

    "energy": "INTEGER DEFAULT 100",
    "health": "INTEGER DEFAULT 100",

    "experience": "INTEGER DEFAULT 0",
    "xp": "INTEGER DEFAULT 0",
    "level": "INTEGER DEFAULT 1",

    "inventory": "TEXT",
    "bio": "TEXT",

    "streak": "INTEGER DEFAULT 0",

    "inventory_limit": "INTEGER DEFAULT 50"
}

    with get_conn() as conn:

        # Create table if missing
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY
        )
        """)

        # Current columns
        existing = [
            c[1]
            for c in conn.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        ]

        # Add missing columns
        for col, dtype in REQUIRED_COLUMNS.items():

            if col not in existing:

                try:
                    conn.execute(f"""
                        ALTER TABLE users
                        ADD COLUMN {col} {dtype}
                    """)

                    print(f"✅ Added missing column: {col}")

                except Exception as e:
                    print(f"⚠️ Failed adding {col}: {e}")

        # Sync uid/id
        try:

            conn.execute("""
                UPDATE users
                SET id = uid
                WHERE id IS NULL
            """)

            conn.execute("""
                UPDATE users
                SET uid = id
                WHERE uid IS NULL
            """)

        except Exception as e:
            print(f"⚠️ ID sync failed: {e}")

        conn.commit()

        print("✅ users table auto-fix completed")
# =========================================================
# VALIDATION FUNCTIONS
# =========================================================

def validate_database():
    """Validate if the database is a valid SQLite database."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except sqlite3.DatabaseError:
        print("⚠️ Database file is corrupted. Recreating...")
        if os.path.exists(DB_PATH):
            backup_path = f"{DB_PATH}.backup.{int(time.time())}"
            os.rename(DB_PATH, backup_path)
            print(f"📦 Backed up corrupted database to {backup_path}")
        return False

# =========================================================
# CORE TABLES SETUP (Merged from both)
# =========================================================

def setup_core_tables():
    """Setup core tables with proper error handling."""
    if not validate_database():
        print("🔄 Creating new database...")
    
    with get_conn() as conn:
        # Users table - merged with all columns from both versions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY,
                id INTEGER UNIQUE,
                username TEXT,
                chat_id INTEGER,
                coins INTEGER DEFAULT 0,
                karma INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                locked_savings INTEGER DEFAULT 0,
                last_deposit_time INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0,
                bribed INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT 0,
                last_active INTEGER DEFAULT 0
            )
        """)
        
        # Deck table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deck (
                file_id TEXT PRIMARY KEY,
                json TEXT
            )
        """)
        
        # User cards table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER,
                file_id TEXT,
                name TEXT,
                power TEXT,
                value INTEGER,
                rarity TEXT,
                drawn_at INTEGER
            )
        """)
        
        # Admins table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT UNIQUE
            )
        """)
        
        # Tax bank table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tax_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER,
                timestamp INTEGER
            )
        """)
        
        # Game logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_logs (
                id INTEGER,
                game_name TEXT,
                timestamp INTEGER
            )
        """)
        
        # Word scores table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_scores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                points INTEGER DEFAULT 0
            )
        """)
        
        # Groups table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                gid INTEGER PRIMARY KEY,
                title TEXT,
                added_at INTEGER
            )
        """)
        
        # Known groups table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS known_groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                added_at INTEGER
            )
        """)
        
        # Earn times table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS earn_times (
                id INTEGER PRIMARY KEY,
                last_claimed INTEGER
            )
        """)
        
        # Referrals table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                new_id INTEGER PRIMARY KEY,
                referrer_id INTEGER,
                timestamp INTEGER
            )
        """)
        
        # Active users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS active_users (
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                last_seen INTEGER,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Streaks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS streaks (
                id INTEGER PRIMARY KEY,
                streak_day INTEGER DEFAULT 0,
                last_claimed INTEGER DEFAULT 0
            )
        """)
        
        # Transfers table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender INTEGER,
                receiver INTEGER,
                amount INTEGER,
                timestamp INTEGER
            )
        """)
        
        # Duel stats table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duel_stats (
                id INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0
            )
        """)
        
        # Settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Insert default settings if not exists
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ref_reward', '50')")
        
        print("✅ Core tables setup completed")

# =========================================================
# BANK TABLES (Merged)
# =========================================================

def setup_bank_tables():
    """Setup bank tables."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banks (
                bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner_id INTEGER,
                created_at INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_members (
                id INTEGER PRIMARY KEY,
                bank_id INTEGER,
                joined_at INTEGER
            )
        """)
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
                id INTEGER,
                action TEXT,
                amount INTEGER,
                timestamp INTEGER
            )
        """)
        print("✅ Bank tables setup completed")

def setup_banktax_table():
    """Setup bank tax table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banktax (
                id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT OR IGNORE INTO banktax (id, coins) VALUES (1, 0)")
        print("✅ Bank tax table setup completed")

def ensure_system_account():
    """Ensure system account exists."""
    with db_lock:
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users (uid, id, coins) VALUES (?, ?, ?)", (999, 999, 0))

def ensure_system_bank():
    """Ensure system bank exists."""
    with get_conn() as conn:
        row = conn.execute("SELECT bank_id FROM banks WHERE name = 'System Vault'").fetchone()
        if not row:
            conn.execute("""
                INSERT INTO banks (name, owner_id, created_at)
                VALUES ('System Vault', 0, strftime('%s', 'now'))
            """)

# =========================================================
# CLAN TABLES
# =========================================================

def setup_clan_tables():
    """Setup clan-related tables."""
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
            id        INTEGER NOT NULL,
            username   TEXT    NOT NULL DEFAULT '',
            title      TEXT    NOT NULL DEFAULT 'Member',
            joined_at  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(clan_id, id)
        )
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
            voter_id  INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            PRIMARY KEY(clan_id, voter_id, target_id)
        )
        """)
        print("✅ Clan tables setup completed")

# =========================================================
# GAME TABLES
# =========================================================

def setup_game_tables():
    """Setup all game-related tables."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mines_games (
                id INTEGER PRIMARY KEY,
                bet INTEGER,
                bombs INTEGER,
                revealed TEXT,
                bomb_positions TEXT,
                started_at INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mines_cooldowns (
                id INTEGER PRIMARY KEY,
                last_played INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_cooldowns (
                id INTEGER,
                game TEXT,
                last_played INTEGER,
                PRIMARY KEY (id, game)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY,
                coins_earned INTEGER DEFAULT 0
            )
        """)
        print("✅ Game tables setup completed")

def setup_game_cooldowns():
    """Setup game cooldowns table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_cooldowns (
                id INTEGER,
                game TEXT,
                last_played INTEGER,
                PRIMARY KEY (id, game)
            )
        """)
        print("✅ Game cooldowns table setup completed")

def setup_mines_table():
    """Setup mines game table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mines_games (
                id INTEGER PRIMARY KEY,
                bet INTEGER,
                bombs INTEGER,
                revealed TEXT,
                bomb_positions TEXT,
                started_at INTEGER
            )
        """)
        print("✅ Mines table setup completed")

def setup_mines_cooldown_table():
    """Setup mines cooldown table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mines_cooldowns (
                id INTEGER PRIMARY KEY,
                last_played INTEGER
            )
        """)
        print("✅ Mines cooldown table setup completed")

def setup_user_stats():
    """Setup user stats table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY,
                coins_earned INTEGER DEFAULT 0
            )
        """)
        print("✅ User stats table setup completed")

# =========================================================
# SHOWROOM TABLES
# =========================================================

def setup_showroom_tables():
    """Setup showroom and marketplace tables."""
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
                id INTEGER,
                item_id INTEGER,
                bought_at INTEGER,
                PRIMARY KEY (id, item_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_listings (
                listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_id INTEGER,
                price INTEGER,
                listed_at INTEGER
            )
        """)
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
        print("✅ Showroom tables setup completed")

def ensure_market_trades_table():
    setup_showroom_tables()

def ensure_user_showroom_table():
    setup_showroom_tables()

def ensure_user_listings_table():
    setup_showroom_tables()

def setup_marketplace():
    setup_showroom_tables()

# =========================================================
# PET TABLES
# =========================================================

def setup_pet_tables():
    """Setup pet system tables."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_pets (
                id INTEGER PRIMARY KEY,
                pet_name TEXT,
                pet_type TEXT,
                level INTEGER DEFAULT 1,
                hunger INTEGER DEFAULT 100
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pet_battles (
                id INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0
            )
        """)
        print("✅ Pet tables setup completed")

def setup_pet_system():
    setup_pet_tables()

# =========================================================
# LOANS TABLE
# =========================================================

def setup_loans_table():
    """Setup loans table."""
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY,
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
        print("✅ Loans table setup completed")

def ensure_loans_table():
    setup_loans_table()

# =========================================================
# USER MEMORY TABLE
# =========================================================

def setup_user_memory_table():
    """Setup user memory table for AI context."""

    with get_conn() as conn:

        conn.execute("""

        CREATE TABLE IF NOT EXISTS user_memory (

            memory_id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            role TEXT NOT NULL,
            content TEXT NOT NULL,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP

        )

        """)

        conn.commit()

        print("✅ User memory table setup completed")


def ensure_user_memory_table():
    setup_user_memory_table()
# =========================================================
# GROUP CONFIGURATION
# =========================================================

def setup_group_config_table():
    """Create table for per‑group configuration key/value pairs."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_config (
                gid INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (gid, key)
            )
        """)
        print("✅ Group config table setup completed")

def set_group_config(gid: int, key: str, value: str):
    """Insert or update a configuration value for a specific group."""
    with db_lock:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO group_config (gid, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(gid, key) DO UPDATE SET value=excluded.value",
                (gid, key, value)
            )

def get_group_config(gid: int, key: str, default: str = None) -> str:
    """Retrieve a configuration value for a specific group."""
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM group_config WHERE gid = ? AND key = ?", (gid, key)).fetchone()
        return row[0] if row else default

# =========================================================
# WORD SCORES
# =========================================================

def setup_word_scores():
    """Setup word scores table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_scores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                points INTEGER DEFAULT 0
            )
        """)
        print("✅ Word scores table setup completed")

# =========================================================
# GIVEAWAY CARD TABLES
# =========================================================

def setup_giveaway_card_tables():
    """Setup giveaway card tables."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                name TEXT,
                power TEXT,
                value INTEGER,
                rarity TEXT,
                quantity INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_giveaways (
                id INTEGER,
                card_id INTEGER,
                received_at INTEGER,
                PRIMARY KEY (id, card_id)
            )
        """)
        print("✅ Giveaway card tables setup completed")

def migrate_giveaway_card_table():
    """Migrate giveaway card table if needed."""
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE giveaway_cards ADD COLUMN quantity INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        print("✅ Giveaway card table migration completed")

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

# =========================================================

def initialize_database():
    """Initialize all database tables."""
    print("🚀 Initializing database...")

    try:

        # =================================================
        # CORE TABLES
        # =================================================

        setup_core_tables()

        # =================================================
        # ENSURE EXTRA TABLES
        # =================================================

        ensure_table("groups", """

        CREATE TABLE IF NOT EXISTS groups (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            group_id INTEGER UNIQUE,
            group_name TEXT,

            added_by INTEGER,
            added_at INTEGER DEFAULT 0

        )

        """)

        ensure_table("admins", """

        CREATE TABLE IF NOT EXISTS admins (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER UNIQUE,
            username TEXT,

            added_at INTEGER DEFAULT 0

        )

        """)

        ensure_table("economy", """

        CREATE TABLE IF NOT EXISTS economy (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER UNIQUE,

            wallet INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0

        )

        """)

        # =================================================
        # AUTO FIX USERS TABLE
        # =================================================

        REQUIRED_COLUMNS = {

            "uid": "INTEGER",
            "id": "INTEGER",

            "username": "TEXT",
            "chat_id": "INTEGER",

            "coins": "INTEGER DEFAULT 0",
            "karma": "INTEGER DEFAULT 0",
            "bank": "INTEGER DEFAULT 0",

            "locked_savings": "INTEGER DEFAULT 0",

            "last_deposit_time": "INTEGER DEFAULT 0",
            "last_active": "INTEGER DEFAULT 0",

            "last_daily": "INTEGER DEFAULT 0",
            "last_weekly": "INTEGER DEFAULT 0",
            "last_monthly": "INTEGER DEFAULT 0",

            "last_draw_time": "INTEGER DEFAULT 0",
            "last_earn_time": "INTEGER DEFAULT 0",
            "last_work_time": "INTEGER DEFAULT 0",
            "last_rob_time": "INTEGER DEFAULT 0",
            "last_gamble_time": "INTEGER DEFAULT 0",
            "last_heist_time": "INTEGER DEFAULT 0",
            "last_crime_time": "INTEGER DEFAULT 0",
            "last_beg_time": "INTEGER DEFAULT 0",
            "last_hunt_time": "INTEGER DEFAULT 0",
            "last_dig_time": "INTEGER DEFAULT 0",
            "last_fish_time": "INTEGER DEFAULT 0",
            "last_mine_time": "INTEGER DEFAULT 0",
            "last_search_time": "INTEGER DEFAULT 0",

            "last_daily_claim": "INTEGER DEFAULT 0",
            "last_weekly_claim": "INTEGER DEFAULT 0",
            "last_monthly_claim": "INTEGER DEFAULT 0",

            "bank_balance": "INTEGER DEFAULT 0",
            "wallet": "INTEGER DEFAULT 0",

            "energy": "INTEGER DEFAULT 100",
            "health": "INTEGER DEFAULT 100",

            "experience": "INTEGER DEFAULT 0",
            "xp": "INTEGER DEFAULT 0",
            "level": "INTEGER DEFAULT 1",

            "inventory": "TEXT",
            "bio": "TEXT",

            "streak": "INTEGER DEFAULT 0",

            "inventory_limit": "INTEGER DEFAULT 50",

            "bribed": "INTEGER DEFAULT 0"
        }

        with get_conn() as conn:

            # Make sure users table exists
            conn.execute("""

            CREATE TABLE IF NOT EXISTS users (

                uid INTEGER PRIMARY KEY

            )

            """)

            # Current columns
            existing = [

                c[1]

                for c in conn.execute(
                    "PRAGMA table_info(users)"
                ).fetchall()

            ]

            # Add missing columns
            for col, dtype in REQUIRED_COLUMNS.items():

                try:

                    if col not in existing:

                        conn.execute(f"""

                            ALTER TABLE users
                            ADD COLUMN {col} {dtype}

                        """)

                        print(f"✅ Added column: {col}")

                except Exception as e:

                    print(f"⚠️ Failed adding {col}: {e}")

            # Sync uid/id
            try:

                conn.execute("""

                    UPDATE users
                    SET id = uid
                    WHERE id IS NULL

                """)

                conn.execute("""

                    UPDATE users
                    SET uid = id
                    WHERE uid IS NULL

                """)

                conn.commit()

                print("✅ ID ↔ UID sync completed")

            except Exception as e:

                print(f"⚠️ Sync failed: {e}")

        # =================================================
        # OTHER TABLES
        # =================================================

        setup_clan_tables()
        setup_game_tables()
        setup_game_cooldowns()
        setup_showroom_tables()
        setup_pet_tables()
        setup_loans_table()
        setup_user_memory_table()
        setup_group_config_table()
        setup_bank_tables()
        setup_banktax_table()
        setup_giveaway_card_tables()
        setup_word_scores()

        ensure_system_account()
        ensure_system_bank()

        with get_conn() as conn:
            setup_sync_triggers(conn)

        print("✅ Database initialization completed successfully!")

    except Exception as e:

        print(f"❌ Failed to initialize database: {e}")

        raise
# =========================================================
# CORE DATABASE FUNCTIONS (Merged)
# =========================================================

def get_all_group_ids():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT gid FROM groups").fetchall()]

def add_user(id, username, chat_id=None):
    clean = username.lstrip("@ ").strip() if username else str(id)
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, username, chat_id) VALUES (?, ?, ?)", (id, clean, chat_id))
        conn.execute("UPDATE users SET username = ?, chat_id = ? WHERE id = ?", (clean, chat_id, id))

def save_username(id: int, username: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (username, id))

def get_username(id):
    with get_conn() as conn:
        row = conn.execute("SELECT username FROM users WHERE id = ?", (id,)).fetchone()
        return row[0] if row and row[0] else "Unknown"

def get_balance(id):
    with get_conn() as conn:
        row = conn.execute("SELECT coins FROM users WHERE id = ?", (id,)).fetchone()
        return row[0] if row else 0

def set_balance(id, amount):
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET coins = ? WHERE id = ?", (amount, id))

def update_balance(id, amount):
    for attempt in range(3):
        try:
            with db_lock:
                with get_conn() as conn:
                    conn.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (amount, id))
                    print(f"✅ Updated balance for UID {id} by ₹{amount}")
                    return True
        except sqlite3.OperationalError:
            print(f"⚠️ Attempt {attempt+1}: DB locked for UID {id}, retrying...")
            time.sleep(0.1)
    print(f"❌ Failed to update balance for UID {id}")
    return False

def get_bank_balance(id):
    with get_conn() as conn:
        row = conn.execute("SELECT bank FROM users WHERE id = ?", (id,)).fetchone()
        return row[0] if row else 0

def update_bank(id, amount):
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET bank = bank + ? WHERE id = ?", (amount, id))

def set_bank(id, amount):
    for attempt in range(3):
        try:
            with db_lock:
                with get_conn() as conn:
                    conn.execute("UPDATE users SET bank = ? WHERE id = ?", (amount, id))
                    print(f"✅ Bank set to {amount} for UID {id}")
                    return True
        except sqlite3.OperationalError:
            print(f"⚠️ Attempt {attempt+1}: DB locked during set_bank, retrying...")
            time.sleep(0.1)
    print(f"❌ Failed to set bank for UID {id}")
    return False

def is_bribed(id):
    with get_conn() as conn:
        row = conn.execute("SELECT bribed FROM users WHERE id = ?", (id,)).fetchone()
        return bool(row[0]) if row else False

def set_bribed(id, status=True):
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET bribed = ? WHERE id = ?", (1 if status else 0, id))

def set_bribe(id, status=True):
    return set_bribed(id, status)

def add_earnings(id, amount):
    with db_lock:
        with get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO user_stats (id, coins_earned) VALUES (?, 0)", (id,))
            conn.execute("UPDATE user_stats SET coins_earned = coins_earned + ? WHERE id = ?", (amount, id))
            print(f"✅ Added earnings ₹{amount} for UID {id}")

def deposit_tax(amount):
    for attempt in range(3):
        try:
            with db_lock:
                with get_conn() as conn:
                    conn.execute("INSERT INTO tax_bank (amount, timestamp) VALUES (?, ?)", (amount, int(time.time())))
                    print(f"✅ Deposited ₹{amount} into tax bank")
                    return True
        except sqlite3.OperationalError:
            print(f"⚠️ Attempt {attempt+1}: DB locked during tax deposit, retrying...")
            time.sleep(0.1)
    print(f"❌ Failed to deposit tax after retries")
    return False

def add_admin(username):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (username) VALUES (?)", (username,))

def remove_admin(username):
    with get_conn() as conn:
        conn.execute("DELETE FROM admins WHERE username = ?", (username,))

def get_admin_list():
    with get_conn() as conn:
        return [row[0] for row in conn.execute("SELECT username FROM admins").fetchall()]

def get_all_user_ids():
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM users").fetchall()
        return [r[0] for r in rows]

def get_user_by_username(username):
    username = username.lstrip("@")
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

def get_all_users():
    with get_conn() as conn:
        rows = conn.execute("SELECT id, username, coins FROM users").fetchall()
        return rows

def remove_user_by_id(id):
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM users WHERE id=?", (id,))

def remove_user_by_username(username):
    username = username.lstrip("@")
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM users WHERE username=?", (username,))

def transfer_coins(sender_id, receiver_id, amount):
    if amount <= 0:
        return False
    sender_balance = get_balance(sender_id)
    if sender_balance < amount:
        return False
    with db_lock:
        with get_conn() as conn:
            conn.execute("UPDATE users SET coins = coins - ? WHERE id=?", (amount, sender_id))
            conn.execute("UPDATE users SET coins = coins + ? WHERE id=?", (amount, receiver_id))
    return True

def get_leaderboard(limit=10):
    with get_conn() as conn:
        rows = conn.execute("SELECT id, username, coins FROM users ORDER BY coins DESC LIMIT ?", (limit,)).fetchall()
        return rows

def purge_users():
    with db_lock:
        with get_conn() as conn:
            conn.execute("DELETE FROM users")

def get_low_balance_users(limit=100):
    with get_conn() as conn:
        rows = conn.execute("SELECT id, username, coins FROM users ORDER BY coins ASC LIMIT ?", (limit,)).fetchall()
        return rows

def get_ref_reward():
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='ref_reward'").fetchone()
        return int(row[0]) if row else 50

def set_ref_reward(amount):
    with db_lock:
        with get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ref_reward', ?)", (str(amount),))

def add_bribed_column():
    with get_conn() as conn:

        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='users'
        """).fetchone()

        if not tables:
            print("⚠️ users table does not exist yet")
            return

        columns = conn.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

        if not any(col[1] == "bribed" for col in columns):

            conn.execute("""
                ALTER TABLE users
                ADD COLUMN bribed INTEGER DEFAULT 0
            """)

            print("✅ bribed column added")

def migrate_users_table():
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN chat_id INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_daily INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_active INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN bribed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

def backfill_chat_ids(default_chat_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET chat_id = ? WHERE chat_id IS NULL", (default_chat_id,))
        print(f"🧹 Backfilled chat_id for legacy users with {default_chat_id}")

def force_patch_all_users(chat_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET chat_id = ?", (chat_id,))
        print(f"🛠️ Force patched all users with chat_id {chat_id}")

def debug_users_by_chat(chat_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT id, username, chat_id FROM users WHERE chat_id = ?", (chat_id,)).fetchall()
        print(f"📊 Found {len(rows)} users with chat_id {chat_id}")
        for row in rows:
            print(f"🧾 {row}")

# =========================================================
# ECONOMY COMMANDS FUNCTIONS
# =========================================================

def track_game(id, game_name):
    """Track when a user plays a game for cooldown purposes."""
    with get_conn() as conn:
        conn.execute("INSERT INTO game_logs (id, game_name, timestamp) VALUES (?, ?, ?)", (id, game_name, int(time.time())))

def get_user_stats(uid):
    """Get user statistics."""
    with get_conn() as conn:
        row = conn.execute("SELECT coins, karma FROM users WHERE uid = ?", (uid,)).fetchone()
        if row:
            return {"coins": row[0], "karma": row[1]}
        return {"coins": 0, "karma": 0}

def get_locked_savings(uid):
    """Get user's locked savings."""
    with get_conn() as conn:
        row = conn.execute("SELECT locked_savings FROM users WHERE uid = ?", (uid,)).fetchone()
        return row[0] if row else 0

def apply_interest(uid, rate=0.05):
    """Apply interest to user's bank balance."""
    with db_lock:
        with get_conn() as conn:
            row = conn.execute("SELECT bank, last_deposit_time FROM users WHERE uid = ?", (uid,)).fetchone()
            if row and row[0] > 0:
                now = int(time.time())
                if now - row[1] >= 86400:
                    interest = int(row[0] * rate)
                    conn.execute("UPDATE users SET bank = bank + ?, last_deposit_time = ? WHERE uid = ?", (interest, now, uid))
                    return interest
            return 0

def can_earn(uid):
    """Check if user can earn daily reward."""
    with get_conn() as conn:
        row = conn.execute("SELECT last_claimed FROM earn_times WHERE id = ?", (uid,)).fetchone()
        if not row:
            return True
        return int(time.time()) - row[0] >= 86400

def update_earn_time(uid):
    """Update last earn time for user."""
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO earn_times (id, last_claimed) VALUES (?, ?)", (uid, int(time.time())))

def get_tax_pool():
    """Get total tax pool amount."""
    with get_conn() as conn:
        row = conn.execute("SELECT SUM(amount) FROM tax_bank").fetchone()
        return row[0] if row and row[0] else 0

# =========================================================
# CARD UTILS FUNCTIONS (Merged)
# =========================================================

def track_user(uid, username):
    """Track user in database - uses 'id' column not 'uid'."""
    timestamp = int(time.time())
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM users WHERE uid = ?", (uid,)).fetchone()
        if existing:
            conn.execute("UPDATE users SET username = ?, last_active = ? WHERE uid = ?", (username, timestamp, uid))
        else:
            conn.execute("INSERT INTO users (uid, username, last_active, coins, karma) VALUES (?, ?, ?, 0, 0)", (uid, username, timestamp))

def get_karma(uid):
    """Get user's karma."""
    with get_conn() as conn:
        row = conn.execute("SELECT karma FROM users WHERE uid = ?", (uid,)).fetchone()
        return row[0] if row else 0

def format_karma(karma):
    """Format karma value."""
    if karma >= 1000:
        return f"{karma//1000}k"
    return str(karma)

def get_duel_rank(limit=10):
    """Get duel rank leaderboard."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id, wins FROM duel_stats ORDER BY wins DESC LIMIT ?", (limit,)).fetchall()
        return [(row[0], row[1]) for row in rows]

def get_user_relics(uid):
    """Get user's relics."""
    with get_conn() as conn:
        rows = conn.execute("SELECT name, power, value FROM user_cards WHERE id = ? AND rarity = 'Relic'", (uid,)).fetchall()
        return [{"name": row[0], "power": row[1], "value": row[2]} for row in rows]

def get_user_artefacts(uid):
    """Get user's artefacts."""
    with get_conn() as conn:
        rows = conn.execute("SELECT name, power, value FROM user_cards WHERE id = ? AND rarity = 'Artefact'", (uid,)).fetchall()
        return [{"name": row[0], "power": row[1], "value": row[2]} for row in rows]

def log_transfer(sender, receiver, amount):
    """Log coin transfer."""
    with get_conn() as conn:
        conn.execute("INSERT INTO transfers (sender, receiver, amount, timestamp) VALUES (?, ?, ?, ?)", (sender, receiver, amount, int(time.time())))

def get_transfer_logs(limit=50):
    """Get transfer logs."""
    with get_conn() as conn:
        rows = conn.execute("SELECT sender, receiver, amount, timestamp FROM transfers ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return rows

def list_all_cards():
    """List all cards in deck."""
    import json
    with get_conn() as conn:
        rows = conn.execute("SELECT json FROM deck").fetchall()
        cards = []
        for row in rows:
            try:
                cards.append(json.loads(row[0]))
            except:
                continue
        return cards

def remove_card_by_name(name):
    """Remove card by name."""
    import json
    with get_conn() as conn:
        rows = conn.execute("SELECT file_id, json FROM deck").fetchall()
        for file_id, raw in rows:
            try:
                data = json.loads(raw)
                if data.get("name", "").lower() == name.lower():
                    conn.execute("DELETE FROM deck WHERE file_id = ?", (file_id,))
                    conn.execute("DELETE FROM user_cards WHERE LOWER(name) = ?", (name.lower(),))
                    return True
            except:
                continue
    return False

def get_deck_size(uid):
    """Get number of cards a user has."""
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM user_cards WHERE id = ?", (uid,)).fetchone()
        return row[0] if row else 0

def init_db():
    """Initialize database for card utils."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER,
                file_id TEXT,
                name TEXT,
                power TEXT,
                value INTEGER,
                rarity TEXT,
                drawn_at INTEGER
            )
        """)

def create_duel_table():
    """Create duel table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS duel_stats (
                uid INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0            )
        """)

def setup_tables():
    """Setup all card-related tables."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender INTEGER,
                receiver INTEGER,
                amount INTEGER,
                timestamp INTEGER
            )
        """)

def ensure_last_active_column():
    """Ensure last_active column exists."""
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_active INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

def ensure_karma_column():
    """Ensure karma column exists."""
    with get_conn() as conn:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN karma INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

def setup_tax_bank():
    """Setup tax bank table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tax_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER,
                timestamp INTEGER
            )
        """)

# =========================================================
# SHOWROOM HELPER FUNCTIONS
# =========================================================

def get_user_showroom(user_id):
    with get_conn() as conn:
        result = conn.execute("SELECT bike_id, model, price FROM bikes WHERE user_id = ?", (user_id,))
        return [dict(row) for row in result.fetchall()]

def remove_bike_by_id(bike_id):
    with get_conn() as conn:
        result = conn.execute("DELETE FROM bikes WHERE bike_id = ?", (bike_id,))
        return result.rowcount > 0

def get_all_vehicle_owners():
    try:
        with get_conn() as conn:
            result = conn.execute('''
                SELECT user_id FROM bikes
                UNION
                SELECT user_id FROM cars
            ''').fetchall()
        owner_ids = [row[0] for row in result]
        from mongo_users import users_col
        users = users_col.find({"id": {"$in": owner_ids}})
        return [{"user_id": u["id"], "username": u.get("username", "Unknown")} for u in users]
    except Exception as e:
        print(f"Error in get_all_vehicle_owners: {e}")
        return []

def ensure_table(table_name, query):

    with get_conn() as conn:

        conn.execute(query)

        conn.commit()

        print(f"✅ Ensured table: {table_name}")


# =========================================================
# BANK UTILS FUNCTIONS (for compatibility)
# =========================================================

def setup_dynamic_prices():
    """Setup dynamic prices table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asset_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price INTEGER,
                timestamp INTEGER
            )
        """)

def seed_asset_prices():
    """Seed initial asset prices."""
    pass

def setup_badge_table():
    """Setup badge table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                uid INTEGER PRIMARY KEY,
                badge TEXT
            )
        """)

def setup_achievements_table():
    """Setup achievements table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                uid INTEGER PRIMARY KEY,
                first_investment INTEGER,
                total_assets INTEGER,
                max_income INTEGER,
                diversified INTEGER
            )
        """)

def setup_quest_table():
    """Setup quest table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                uid INTEGER,
                quest_name TEXT,
                completed INTEGER DEFAULT 0,
                PRIMARY KEY (uid, quest_name)
            )
        """)

def setup_group_goals_table():
    """Setup group goals table."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_name TEXT,
                target INTEGER,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0
            )
        """)


def fix_users_uid_column():
    with get_conn() as conn:

        columns = [
            column[1]
            for column in conn.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        ]

        if "id" not in columns:

            conn.execute("""
                ALTER TABLE users
                ADD COLUMN id INTEGER
            """)

            conn.execute("""
                UPDATE users
                SET id = id
            """)

            print("✅ users.id column added successfully")

        try:
            conn.execute("""
                ALTER TABLE users
                ADD COLUMN last_active INTEGER DEFAULT 0
            """)
        except:
            pass

        try:
            conn.execute("""
                ALTER TABLE users
                ADD COLUMN karma INTEGER DEFAULT 0
            """)
        except:
            pass

# =========================================================
# DEBUG FUNCTIONS
# =========================================================

def debug_user_schema():
    with get_conn() as conn:
        rows = conn.execute("PRAGMA table_info(users)").fetchall()
        for row in rows:
            print(dict(row))

def debug_tax_pool_schema():
    with get_conn() as conn:
        rows = conn.execute("PRAGMA table_info(tax_bank)").fetchall()
        for row in rows:
            print(dict(row))

# =========================================================
# MONGODB OVERRIDES
# =========================================================

from mongo_users import *

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    initialize_database()
    fix_users_uid_column()
    print("✅ Database initialization complete!")

# =========================================================
# ASYNC WRAPPERS
# =========================================================

import asyncio

async def async_get_balance(uid):
    return await asyncio.to_thread(get_balance, uid)

async def async_update_balance(uid, amount):
    return await asyncio.to_thread(update_balance, uid, amount)

async def async_run(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

async def async_get_conn():
    return await asyncio.to_thread(get_conn)

# =========================================================
# DATABASE INDEXES
# =========================================================

def setup_indexes():
    try:
        with get_conn() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_coins ON users(coins DESC)",
                "CREATE INDEX IF NOT EXISTS idx_users_id ON users(id)",
                "CREATE INDEX IF NOT EXISTS idx_users_uid ON users(uid)",
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active DESC)",
                "CREATE INDEX IF NOT EXISTS idx_user_cards_uid ON user_cards(uid)",
                "CREATE INDEX IF NOT EXISTS idx_user_cards_file_id ON user_cards(file_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_cards_drawn_at ON user_cards(drawn_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_deck_file_id ON deck(file_id)",
                "CREATE INDEX IF NOT EXISTS idx_loans_id ON loans(id)",
                "CREATE INDEX IF NOT EXISTS idx_loans_repaid ON loans(repaid)",
                "CREATE INDEX IF NOT EXISTS idx_tax_bank_id ON tax_bank(id)",
                "CREATE INDEX IF NOT EXISTS idx_game_cooldowns_uid_game ON game_cooldowns(uid, game)",
                "CREATE INDEX IF NOT EXISTS idx_user_memory_uid ON user_memory(uid)",
                "CREATE INDEX IF NOT EXISTS idx_banks_bank_id ON banks(bank_id)",
                "CREATE INDEX IF NOT EXISTS idx_bank_members_uid ON bank_members(uid)",
                "CREATE INDEX IF NOT EXISTS idx_bank_members_bank_id ON bank_members(bank_id)",
                "CREATE INDEX IF NOT EXISTS idx_word_scores_user_id ON word_scores(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_daily_stats_id_date ON user_daily_stats(id, date)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_uid)",
                "CREATE INDEX IF NOT EXISTS idx_referrals_new_uid ON referrals(new_uid)",
                "CREATE INDEX IF NOT EXISTS idx_user_listings_seller ON user_listings(seller_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_listings_listing_id ON user_listings(listing_id)",
                "CREATE INDEX IF NOT EXISTS idx_market_trades_buyer ON market_trades(buyer_id)",
                "CREATE INDEX IF NOT EXISTS idx_showroom_items_item_id ON showroom_items(item_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_showroom_uid ON user_showroom(uid)",
                "CREATE INDEX IF NOT EXISTS idx_clan_members_clan_id ON clan_members(clan_id)",
                "CREATE INDEX IF NOT EXISTS idx_clan_members_uid ON clan_members(uid)",
            ]
            for idx in indexes:
                conn.execute(idx)
            conn.commit()
            print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️ Error creating indexes: {e}")