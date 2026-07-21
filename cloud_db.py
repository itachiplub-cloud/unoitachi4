import asyncio
import time
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from cloud_config import MONGO_URL, CLOUD_DB_NAME

_client = None
_db = None


def _get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return _client


def get_cloud_db():
    global _db
    if _db is None:
        _db = _get_client()[CLOUD_DB_NAME]
    return _db


def _col(name):
    return get_cloud_db()[name]


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

def setup_cloud_indexes():
    db = get_cloud_db()

    db["users"].create_index([("unique_id", ASCENDING)], unique=True)
    db["users"].create_index([("username", ASCENDING)], sparse=True)

    db["files"].create_index([("owner_id", ASCENDING)])
    db["files"].create_index([("file_id", ASCENDING)], unique=True)
    db["files"].create_index([("uploaded_at", DESCENDING)])
    db["files"].create_index([("tags", TEXT)], default_language="none")

    db["shares"].create_index([("token", ASCENDING)], unique=True)
    db["shares"].create_index([("owner_id", ASCENDING)])
    db["shares"].create_index([("is_active", ASCENDING), ("expiry", ASCENDING)])

    db["sessions"].create_index([("user_id", ASCENDING)])
    db["sessions"].create_index([("session_token", ASCENDING)], unique=True)
    db["sessions"].create_index(
        [("is_active", ASCENDING), ("expires_at", ASCENDING)]
    )

    db["rate_limits"].create_index(
        [("user_id", ASCENDING), ("action", ASCENDING), ("timestamp", ASCENDING)]
    )
    db["rate_limits"].create_index(
        [("timestamp", ASCENDING)], expireAfterSeconds=7200
    )

    db["security"].create_index([("user_id", ASCENDING)], unique=True)

    db["pin_locks"].create_index([("user_id", ASCENDING)], unique=True)
    db["login_locks"].create_index([("user_id", ASCENDING)], unique=True)

    db["channels"].create_index([("chat_id", ASCENDING)], unique=True)
    db["bot_config"].create_index([("key", ASCENDING)], unique=True)
    db["user_verification"].create_index(
        [("user_id", ASCENDING), ("verified_version", ASCENDING)]
    )
    db["audit_logs"].create_index([("timestamp", DESCENDING)])
    db["audit_logs"].create_index([("admin_id", ASCENDING)])
    db["audit_logs"].create_index([("target_user", ASCENDING)])


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_user(unique_id):
    return await asyncio.to_thread(_col("users").find_one, {"unique_id": unique_id})


async def create_user(unique_id, username, password_hash):
    from cloud_config import DEFAULT_STORAGE_QUOTA
    doc = {
        "unique_id": unique_id,
        "username": username,
        "password_hash": password_hash,
        "pin_hash": None,
        "storage_used": 0,
        "storage_quota": DEFAULT_STORAGE_QUOTA,
        "upload_count": 0,
        "created_at": time.time(),
        "last_login": None,
        "is_banned": False,
        "ban_reason": None,
        "ban_until": None,
        "is_locked": False,
        "locked_until": None,
    }
    await asyncio.to_thread(_col("users").insert_one, doc)
    return doc


async def update_user(unique_id, **fields):
    if not fields:
        return
    await asyncio.to_thread(
        _col("users").update_one,
        {"unique_id": unique_id},
        {"$set": fields},
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

async def save_file(owner_id, file_id, file_name, file_type, file_size, caption, tags, folder):
    from cloud_config import MAX_FILE_SIZE
    doc = {
        "owner_id": owner_id,
        "file_id": file_id,
        "file_name": file_name,
        "file_type": file_type,
        "file_size": file_size,
        "caption": caption or "",
        "tags": tags or [],
        "uploaded_at": time.time(),
        "folder": folder or "default",
    }
    await asyncio.to_thread(_col("files").insert_one, doc)
    await asyncio.to_thread(
        _col("users").update_one,
        {"unique_id": owner_id},
        {"$inc": {"storage_used": file_size, "upload_count": 1}},
    )
    return doc


async def get_user_files(owner_id, offset=0, limit=20):
    cursor = _col("files").find({"owner_id": owner_id}).sort("uploaded_at", DESCENDING).skip(offset).limit(limit)
    return await asyncio.to_thread(list, cursor)


async def get_file_by_id(file_id):
    return await asyncio.to_thread(_col("files").find_one, {"file_id": file_id})


async def delete_file(file_id, owner_id):
    file_doc = await asyncio.to_thread(_col("files").find_one, {"file_id": file_id, "owner_id": owner_id})
    if not file_doc:
        return False
    await asyncio.to_thread(_col("files").delete_one, {"_id": file_doc["_id"]})
    await asyncio.to_thread(
        _col("users").update_one,
        {"unique_id": owner_id},
        {"$inc": {"storage_used": -file_doc.get("file_size", 0)}},
    )
    await asyncio.to_thread(
        _col("shares").delete_many, {"file_id": file_id, "owner_id": owner_id}
    )
    return True


async def search_files(owner_id, query):
    cursor = _col("files").find(
        {
            "owner_id": owner_id,
            "$or": [
                {"file_name": {"$regex": query, "$options": "i"}},
                {"caption": {"$regex": query, "$options": "i"}},
                {"tags": {"$in": [query.lower()]}},
            ],
        }
    ).sort("uploaded_at", DESCENDING).limit(50)
    return await asyncio.to_thread(list, cursor)


# ---------------------------------------------------------------------------
# Shares
# ---------------------------------------------------------------------------

async def create_share(owner_id, file_id, is_one_time=False, expiry=None, password_hash=None):
    import secrets
    token = secrets.token_urlsafe(16)
    doc = {
        "owner_id": owner_id,
        "file_id": file_id,
        "token": token,
        "is_one_time": is_one_time,
        "expiry": expiry,
        "password_hash": password_hash,
        "created_at": time.time(),
        "access_count": 0,
        "is_active": True,
    }
    await asyncio.to_thread(_col("shares").insert_one, doc)
    return doc


async def get_share(token):
    return await asyncio.to_thread(_col("shares").find_one, {"token": token, "is_active": True})


async def revoke_share(token, owner_id):
    result = await asyncio.to_thread(
        _col("shares").update_one,
        {"token": token, "owner_id": owner_id, "is_active": True},
        {"$set": {"is_active": False}},
    )
    return result.modified_count > 0


async def get_user_shares(owner_id):
    cursor = _col("shares").find({"owner_id": owner_id, "is_active": True}).sort("created_at", DESCENDING)
    return await asyncio.to_thread(list, cursor)


# ---------------------------------------------------------------------------
# Usage stats
# ---------------------------------------------------------------------------

async def get_user_usage(owner_id):
    user = await asyncio.to_thread(_col("users").find_one, {"unique_id": owner_id})
    if not user:
        return {"storage_used": 0, "file_count": 0, "share_count": 0, "storage_quota": 0}

    file_count = await asyncio.to_thread(_col("files").count_documents, {"owner_id": owner_id})
    share_count = await asyncio.to_thread(_col("shares").count_documents, {"owner_id": owner_id, "is_active": True})

    return {
        "storage_used": user.get("storage_used", 0),
        "file_count": file_count,
        "share_count": share_count,
        "storage_quota": user.get("storage_quota", 0),
    }


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------

async def get_all_users(offset=0, limit=20):
    cursor = _col("users").find().sort("created_at", DESCENDING).skip(offset).limit(limit)
    return await asyncio.to_thread(list, cursor)


async def get_user_count():
    return await asyncio.to_thread(_col("users").count_documents, {})


async def get_total_storage():
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$storage_used"}}}]
    result = await asyncio.to_thread(list, _col("users").aggregate, pipeline)
    if result:
        return result[0].get("total", 0)
    return 0


async def log_audit(admin_id, target_user, action, reason=""):
    doc = {
        "admin_id": admin_id,
        "target_user": target_user,
        "action": action,
        "reason": reason,
        "timestamp": time.time(),
    }
    await asyncio.to_thread(_col("audit_logs").insert_one, doc)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session_sync(user_id, token):
    doc = {
        "user_id": user_id,
        "session_token": token,
        "is_active": True,
        "created_at": time.time(),
        "expires_at": time.time() + 86400 * 7,  # 7 days
    }
    _col("sessions").insert_one(doc)
    return doc


def get_active_session_sync(user_id):
    return _col("sessions").find_one({
        "user_id": user_id,
        "is_active": True,
        "expires_at": {"$gt": time.time()},
    })


def invalidate_session_sync(user_id):
    _col("sessions").update_many(
        {"user_id": user_id, "is_active": True},
        {"$set": {"is_active": False}},
    )


def create_session(user_id, token):
    return create_session_sync(user_id, token)


def get_active_session(user_id):
    return get_active_session_sync(user_id)


def invalidate_session(user_id):
    invalidate_session_sync(user_id)
