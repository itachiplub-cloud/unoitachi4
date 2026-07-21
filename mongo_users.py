import os
import time
from pymongo import MongoClient

from config import MONGO_URL

if not MONGO_URL:
    print("Warning: MONGO_URL is not set. Using default local URL.")
    MONGO_URL = "mongodb://localhost:27017"

mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client.get_database("cluster0")
users_col = mongo_db.users

# Create index for faster lookups
users_col.create_index("id", unique=True)
users_col.create_index("username")

def _write_to_sqlite(user_doc):
    if not user_doc:
        return
    import sqlite3
    db_path = os.getenv("CLAN_DB_PATH", "uno.db")
    
    # Dynamically import db_lock to avoid circular import issues
    try:
        from database import db_lock
    except ImportError:
        db_lock = None

    class DummyLock:
        def __enter__(self): pass
        def __exit__(self, exc_type, exc_val, exc_tb): pass

    lock = db_lock if db_lock else DummyLock()

    with lock:
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS modified_users (uid INTEGER PRIMARY KEY)")
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if not columns:
                conn.close()
                return
            uid = user_doc.get("id") or user_doc.get("uid")
            if uid is None:
                conn.close()
                return

            # Ensure user exists in SQLite users table first
            cursor.execute("INSERT OR IGNORE INTO users (id, uid) VALUES (?, ?)", (uid, uid))

            update_cols = []
            update_vals = []
            for col in columns:
                if col in ('id', 'uid'):
                    continue
                if col in user_doc:
                    val = user_doc[col]
                    # Convert dict/list/bool objects to compatible SQLite formats
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    elif isinstance(val, bool):
                        val = 1 if val else 0
                    update_cols.append(f"{col} = ?")
                    update_vals.append(val)

            if update_cols:
                sql = f"UPDATE users SET {', '.join(update_cols)} WHERE id = ? OR uid = ?"
                update_vals.extend([uid, uid])
                cursor.execute(sql, update_vals)

            # Prevent recursive triggers by deleting from modified_users in the same transaction
            cursor.execute("DELETE FROM modified_users WHERE uid = ?", (uid,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error syncing MongoDB to SQLite for UID {user_doc.get('id')}: {e}")

def _get_user(uid):
    user = users_col.find_one({"id": uid})
    if not user:
        user = {
            "id": uid,
            "username": "Unknown",
            "chat_id": None,
            "coins": 0,
            "karma": 0,
            "bank": 0,
            "locked_savings": 0,
            "last_deposit_time": 0,
            "bribed": 0
        }
        users_col.insert_one(user)
    # Always sync retrieved user to SQLite to ensure tables match
    _write_to_sqlite(user)
    return user

def add_user(uid, username, chat_id=None):
    clean = username.lstrip("@ ").strip()
    users_col.update_one(
        {"id": uid},
        {"$set": {"username": clean, "chat_id": chat_id}},
        upsert=True
    )
    _write_to_sqlite(_get_user(uid))

def get_username(uid):
    user = _get_user(uid)
    return user.get("username", "Unknown") if user else "Unknown"

def get_balance(uid):
    user = _get_user(uid)
    return user.get("coins", 0) if user else 0

def set_balance(uid, amount):
    users_col.update_one({"id": uid}, {"$set": {"coins": amount}}, upsert=True)
    _write_to_sqlite(_get_user(uid))
    return True

def update_balance(uid, amount):
    users_col.update_one({"id": uid}, {"$inc": {"coins": amount}}, upsert=True)
    _write_to_sqlite(_get_user(uid))
    return True

def get_bank_balance(uid):
    user = _get_user(uid)
    return user.get("bank", 0) if user else 0

def update_bank(uid, amount):
    users_col.update_one({"id": uid}, {"$inc": {"bank": amount}}, upsert=True)
    _write_to_sqlite(_get_user(uid))
    return True

def set_bank(uid, amount):
    users_col.update_one({"id": uid}, {"$set": {"bank": amount}}, upsert=True)
    _write_to_sqlite(_get_user(uid))
    return True

def get_user_stats(uid):
    user = _get_user(uid)
    if user:
        return {"coins": user.get("coins", 0), "karma": user.get("karma", 0)}
    return None

def get_locked_savings(uid):
    user = _get_user(uid)
    return user.get("locked_savings", 0) if user else 0

def apply_interest(uid, rate=0.05):
    user = users_col.find_one({"id": uid})
    if not user:
        return False
    coins = user.get("coins", 0)
    interest = int(coins * rate)
    if interest > 0:
        users_col.update_one({"id": uid}, {"$inc": {"coins": interest}})
    _write_to_sqlite(_get_user(uid))
    return interest

def transfer_coins(sender_id, receiver_id, amount):
    sender = users_col.find_one({"id": sender_id})
    if not sender or sender.get("coins", 0) < amount:
        return False
    
    users_col.update_one({"id": sender_id}, {"$inc": {"coins": -amount}})
    users_col.update_one({"id": receiver_id}, {"$inc": {"coins": amount}}, upsert=True)
    
    _write_to_sqlite(_get_user(sender_id))
    _write_to_sqlite(_get_user(receiver_id))
    return True

def purge_users():
    users_col.delete_many({})
    import sqlite3
    db_path = os.getenv("CLAN_DB_PATH", "uno.db")
    try:
        from database import db_lock
    except ImportError:
        db_lock = None
    class DummyLock:
        def __enter__(self): pass
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    lock = db_lock if db_lock else DummyLock()
    with lock:
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM modified_users")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error purging SQLite users: {e}")

def get_all_user_ids():
    return [u["id"] for u in users_col.find({}, {"id": 1})]

def get_user_by_username(username):
    clean = username.lstrip("@ ").strip()
    user = users_col.find_one({"username": {"$regex": f"^{clean}$", "$options": "i"}})
    return user["id"] if user else None

def get_all_users():
    users = users_col.find().sort("coins", -1)
    return [(u.get("id"), u.get("username", "Unknown"), u.get("coins", 0)) for u in users]

def remove_user_by_id(uid):
    users_col.delete_one({"id": uid})
    import sqlite3
    db_path = os.getenv("CLAN_DB_PATH", "uno.db")
    try:
        from database import db_lock
    except ImportError:
        db_lock = None
    class DummyLock:
        def __enter__(self): pass
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    lock = db_lock if db_lock else DummyLock()
    with lock:
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("DELETE FROM users WHERE id = ? OR uid = ?", (uid, uid))
            conn.execute("DELETE FROM modified_users WHERE uid = ?", (uid,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error removing SQLite user {uid}: {e}")

def remove_user_by_username(username):
    clean = username.lstrip("@ ").strip()
    user = users_col.find_one({"username": {"$regex": f"^{clean}$", "$options": "i"}})
    uid = user.get("id") if user else None
    
    users_col.delete_many({"username": {"$regex": f"^{clean}$", "$options": "i"}})
    
    import sqlite3
    db_path = os.getenv("CLAN_DB_PATH", "uno.db")
    try:
        from database import db_lock
    except ImportError:
        db_lock = None
    class DummyLock:
        def __enter__(self): pass
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    lock = db_lock if db_lock else DummyLock()
    with lock:
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            if uid is not None:
                conn.execute("DELETE FROM users WHERE id = ? OR uid = ?", (uid, uid))
                conn.execute("DELETE FROM modified_users WHERE uid = ?", (uid,))
            else:
                conn.execute("DELETE FROM users WHERE LOWER(username) = ?", (clean.lower(),))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Error removing SQLite user by username {clean}: {e}")

def get_low_balance_users(threshold=10):
    return [u.get("username", "Unknown") for u in users_col.find({"coins": {"$lt": threshold}})]

def get_leaderboard():
    users = users_col.find().sort("coins", -1).limit(5)
    return [(u.get("username", "Unknown"), u.get("coins", 0)) for u in users]

def mark_bribed(uid):
    users_col.update_one({"id": uid}, {"$set": {"bribed": 1}}, upsert=True)
    _write_to_sqlite(_get_user(uid))

def save_username(uid, username):
    users_col.update_one({"id": uid}, {"$set": {"username": username}}, upsert=True)
    _write_to_sqlite(_get_user(uid))

def ensure_system_account():
    users_col.update_one({"id": 999}, {"$setOnInsert": {"coins": 0, "username": "System"}}, upsert=True)
    _write_to_sqlite(_get_user(999))

def migrate_users_table():
    pass

def backfill_chat_ids(default_chat_id):
    users_col.update_many({"chat_id": {"$exists": False}}, {"$set": {"chat_id": default_chat_id}})
    for uid in get_all_user_ids():
        _write_to_sqlite(_get_user(uid))

def force_patch_all_users(chat_id):
    users_col.update_many({}, {"$set": {"chat_id": chat_id}})
    for uid in get_all_user_ids():
        _write_to_sqlite(_get_user(uid))

def debug_users_by_chat(chat_id):
    users = list(users_col.find({"chat_id": chat_id}))
    print(f"📊 Found {len(users)} users with chat_id {chat_id}")
    for u in users:
        print(f"🧾 {u}")
