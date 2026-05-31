"""
Database layer for managing your sticker‑pool.
This module ensures the `stickers` table exists on import
and provides CRUD functions for file_ids.
"""

import sqlite3
import os
import time
import shutil
from contextlib import contextmanager

DB_PATH = "stickers.db"

@contextmanager
def _get_connection():
    """
    Opens a thread‐safe connection to the SQLite database with auto-recovery.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Test the connection to ensure it is a valid database
        conn.execute("SELECT 1")
        yield conn
        conn.commit()
    except sqlite3.DatabaseError as e:
        print(f"⚠️ Database error on {DB_PATH}: {e}")
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            conn = None
        
        if "file is not a database" in str(e) or "corrupt" in str(e).lower():
            print(f"⚠️ Database {DB_PATH} is corrupted. Attempting auto-recovery...")
            
            # Wait a bit to ensure file handles are released
            time.sleep(1)
            
            if os.path.exists(DB_PATH):
                backup_path = f"{DB_PATH}.corrupted.{int(time.time())}"
                try:
                    # Try to copy first, then delete (more reliable than rename on Windows)
                    shutil.copy2(DB_PATH, backup_path)
                    print(f"📦 Backed up corrupted database to {backup_path}")
                    
                    # Try to remove the corrupted file
                    try:
                        os.remove(DB_PATH)
                        print(f"🗑️ Removed corrupted database file")
                    except PermissionError:
                        print(f"⚠️ Could not remove {DB_PATH}, will try to create new one with different name")
                        # Use a temporary name for new database
                        temp_db_path = f"{DB_PATH}.temp"
                        DB_PATH_GLOBAL = temp_db_path
                        try:
                            conn = sqlite3.connect(temp_db_path, timeout=10, check_same_thread=False)
                            yield conn
                            conn.commit()
                            # Rename temp to actual after successful creation
                            if os.path.exists(DB_PATH):
                                os.remove(DB_PATH)
                            os.rename(temp_db_path, DB_PATH)
                            return
                        except:
                            pass
                        
                except Exception as backup_err:
                    print(f"❌ Failed to backup corrupted database: {backup_err}")
                    # Try to just remove the file
                    try:
                        os.remove(DB_PATH)
                        print(f"🗑️ Force removed corrupted database file")
                    except:
                        pass
            
            try:
                print(f"🔄 Creating new database {DB_PATH}...")
                conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                yield conn
                conn.commit()
            except Exception as retry_err:
                print(f"❌ Auto-recovery failed: {retry_err}")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                raise
        else:
            raise
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def init_db() -> None:
    """
    Creates the `stickers` table if it doesn't already exist.
    Call this once (it runs automatically on import).
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stickers (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id   TEXT UNIQUE NOT NULL
                )
            """)
            print("✅ Stickers database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize stickers database: {e}")
        raise


def add_file_id(file_id: str) -> bool:
    """
    Inserts a new `file_id` into the pool.
    If it already exists, nothing happens.
    Returns True if added, False if already exists.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO stickers (file_id) VALUES (?)",
                (file_id,)
            )
            return cursor.rowcount > 0
    except Exception as e:
        print(f"⚠️ Failed to add file_id: {e}")
        return False


def list_file_ids() -> list[str]:
    """
    Returns a list of all saved sticker file_ids.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_id FROM stickers ORDER BY id")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"⚠️ Failed to list file_ids: {e}")
        return []


def remove_file_id(file_id: str) -> bool:
    """
    Deletes the given `file_id` from the pool.
    Returns True if removed, False if not found.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM stickers WHERE file_id = ?",
                (file_id,)
            )
            return cursor.rowcount > 0
    except Exception as e:
        print(f"⚠️ Failed to remove file_id: {e}")
        return False


def clear_pool() -> bool:
    """
    Empties the entire sticker pool.
    Returns True if successful.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stickers")
            return True
    except Exception as e:
        print(f"⚠️ Failed to clear pool: {e}")
        return False


def get_sticker_count() -> int:
    """
    Returns the total number of stickers in the pool.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stickers")
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"⚠️ Failed to get sticker count: {e}")
        return 0


def get_random_sticker() -> str | None:
    """
    Returns a random sticker file_id from the pool.
    Returns None if pool is empty.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_id FROM stickers ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"⚠️ Failed to get random sticker: {e}")
        return None


def sticker_exists(file_id: str) -> bool:
    """
    Checks if a sticker already exists in the pool.
    """
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM stickers WHERE file_id = ?", (file_id,))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"⚠️ Failed to check sticker existence: {e}")
        return False


def repair_database():
    """
    Force repair the database by deleting and recreating it.
    """
    global DB_PATH
    
    print(f"🔧 Attempting to repair database: {DB_PATH}")
    
    # Close any existing connections (garbage collection)
    import gc
    gc.collect()
    
    # Wait for any locks to clear
    time.sleep(2)
    
    # Try to delete the file
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"🗑️ Removed corrupted {DB_PATH}")
        except PermissionError:
            print(f"⚠️ Cannot remove {DB_PATH} - file is locked")
            print("Please:")
            print("1. Close your bot completely")
            print("2. Close any SQLite browsers")
            print("3. Manually delete the file: " + os.path.abspath(DB_PATH))
            print("4. Restart your bot")
            return False
        except Exception as e:
            print(f"❌ Failed to remove {DB_PATH}: {e}")
            return False
    
    # Reinitialize the database
    try:
        init_db()
        print(f"✅ Successfully repaired {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ Failed to repair database: {e}")
        return False


# Initialize the database on module import with retry logic
def _safe_init():
    """Safely initialize the database with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            init_db()
            return
        except Exception as e:
            print(f"⚠️ Initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(2)
                repair_database()
            else:
                print(f"❌ Failed to initialize stickers database after {max_retries} attempts")
                raise


# Run initialization
_safe_init()