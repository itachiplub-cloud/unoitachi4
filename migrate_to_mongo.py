import sqlite3
import os
from pymongo import MongoClient

def migrate():
    print("Starting migration from SQLite (uno.db) to MongoDB...")
    
    # SQLite connection
    if not os.path.exists("uno.db"):
        print("uno.db not found. Nothing to migrate.")
        return
        
    conn = sqlite3.connect("uno.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # MongoDB connection
    MONGO_URL = os.getenv("MONGO_URL")
    if not MONGO_URL:
        from dotenv import load_dotenv
        load_dotenv()
        MONGO_URL = os.getenv("MONGO_URL")
        
    if not MONGO_URL:
        print("MONGO_URL not found in environment or .env file.")
        return
        
    client = MongoClient(MONGO_URL)
    db = client.get_database("cluster0")
    users_col = db.users
    
    try:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            user_dict = dict(row)
            uid = user_dict.get("id")
            if uid is None:
                continue
                
            # Prepare document
            doc = {
                "id": uid,
                "username": user_dict.get("username", "Unknown"),
                "chat_id": user_dict.get("chat_id"),
                "coins": user_dict.get("coins", 0),
                "karma": user_dict.get("karma", 0),
                "bank": user_dict.get("bank", 0),
                "locked_savings": user_dict.get("locked_savings", 0),
                "last_deposit_time": user_dict.get("last_deposit_time", 0),
                "bribed": user_dict.get("bribed", 0)
            }
            
            # Upsert into MongoDB
            users_col.update_one({"id": uid}, {"$set": doc}, upsert=True)
            migrated_count += 1
            
        print(f"Successfully migrated {migrated_count} users to MongoDB.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
