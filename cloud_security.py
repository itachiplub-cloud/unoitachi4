import time
import asyncio
from cloud_db import get_cloud_db
from cloud_config import (
    SPAM_WARNINGS,
    SPAM_MUTE_DURATION,
    SPAM_BAN_DURATION,
    PIN_LOCK_ATTEMPTS,
    PIN_LOCK_DURATION,
    PIN_DAILY_LOCKOUT_ATTEMPTS,
    PIN_DAILY_LOCKOUT_DURATION,
    LOGIN_LOCK_ATTEMPTS,
    LOGIN_LOCK_DURATION,
)


def _col(name):
    return get_cloud_db()[name]


# ---------------------------------------------------------------------------
# Spam / anti-flood
# ---------------------------------------------------------------------------

async def record_spam_offence(user_id):
    """Track spam offences. Returns (offence_count, action_taken)"""
    now = time.time()
    col = _col("security")

    def _find():
        return col.find_one({"user_id": user_id})

    doc = await asyncio.to_thread(_find)

    if not doc:
        doc = {"user_id": user_id, "offence_count": 0, "muted_until": None, "banned_until": None, "last_offence": None}
        await asyncio.to_thread(col.insert_one, doc)

    offence_count = doc.get("offence_count", 0) + 1
    action_taken = None

    update_fields = {"offence_count": offence_count, "last_offence": now}

    if offence_count > SPAM_WARNINGS + 1:
        update_fields["banned_until"] = now + SPAM_BAN_DURATION
        action_taken = "banned"
    elif offence_count > SPAM_WARNINGS:
        update_fields["muted_until"] = now + SPAM_MUTE_DURATION
        action_taken = "muted"
    else:
        action_taken = "warned"

    await asyncio.to_thread(
        col.update_one,
        {"user_id": user_id},
        {"$set": update_fields},
    )
    return offence_count, action_taken


async def is_muted(user_id):
    doc = await asyncio.to_thread(_col("security").find_one, {"user_id": user_id})
    if not doc:
        return False
    muted_until = doc.get("muted_until")
    if muted_until and muted_until > time.time():
        return True
    return False


async def is_banned(user_id):
    doc = await asyncio.to_thread(_col("security").find_one, {"user_id": user_id})
    if not doc:
        return False
    banned_until = doc.get("banned_until")
    if banned_until and banned_until > time.time():
        return True
    return False


# ---------------------------------------------------------------------------
# PIN lock
# ---------------------------------------------------------------------------

async def check_pin_lock(user_id):
    """Returns (locked: bool, remaining_seconds: int)"""
    doc = await asyncio.to_thread(_col("pin_locks").find_one, {"user_id": user_id})
    if not doc:
        return False, 0

    now = time.time()

    locked_until = doc.get("locked_until", 0)
    if locked_until and locked_until > now:
        return True, int(locked_until - now)

    daily_lockout_until = doc.get("daily_lockout_until", 0)
    if daily_lockout_until and daily_lockout_until > now:
        return True, int(daily_lockout_until - now)

    return False, 0


async def record_pin_failure(user_id):
    """Record failed PIN attempt. Returns (locked: bool, lock_duration: int)"""
    now = time.time()
    col = _col("pin_locks")

    doc = await asyncio.to_thread(col.find_one, {"user_id": user_id})
    if not doc:
        doc = {
            "user_id": user_id,
            "failed_attempts": 0,
            "locked_until": None,
            "daily_failures": 0,
            "daily_lockout_until": None,
        }
        await asyncio.to_thread(col.insert_one, doc)

    failed = doc.get("failed_attempts", 0) + 1
    daily_failures = doc.get("daily_failures", 0) + 1
    update = {"failed_attempts": failed, "daily_failures": daily_failures}

    if failed >= PIN_LOCK_ATTEMPTS:
        update["locked_until"] = now + PIN_LOCK_DURATION
        update["failed_attempts"] = 0
        await asyncio.to_thread(col.update_one, {"user_id": user_id}, {"$set": update})
        return True, PIN_LOCK_DURATION

    if daily_failures >= PIN_DAILY_LOCKOUT_ATTEMPTS:
        update["daily_lockout_until"] = now + PIN_DAILY_LOCKOUT_DURATION
        update["daily_failures"] = 0
        await asyncio.to_thread(col.update_one, {"user_id": user_id}, {"$set": update})
        return True, PIN_DAILY_LOCKOUT_DURATION

    await asyncio.to_thread(col.update_one, {"user_id": user_id}, {"$set": update})
    return False, 0


async def reset_pin_lock(user_id):
    await asyncio.to_thread(
        _col("pin_locks").update_one,
        {"user_id": user_id},
        {"$set": {
            "failed_attempts": 0,
            "locked_until": None,
            "daily_failures": 0,
            "daily_lockout_until": None,
        }},
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Login lock
# ---------------------------------------------------------------------------

async def check_login_lock(user_id):
    """Returns (locked: bool, remaining_seconds: int)"""
    doc = await asyncio.to_thread(_col("login_locks").find_one, {"user_id": user_id})
    if not doc:
        return False, 0

    locked_until = doc.get("locked_until", 0)
    now = time.time()
    if locked_until and locked_until > now:
        return True, int(locked_until - now)
    return False, 0


async def record_login_failure(user_id):
    """Record failed login. Returns (locked: bool, lock_duration: int)"""
    now = time.time()
    col = _col("login_locks")

    doc = await asyncio.to_thread(col.find_one, {"user_id": user_id})
    if not doc:
        doc = {"user_id": user_id, "failed_attempts": 0, "locked_until": None}
        await asyncio.to_thread(col.insert_one, doc)

    failed = doc.get("failed_attempts", 0) + 1

    if failed >= LOGIN_LOCK_ATTEMPTS:
        await asyncio.to_thread(
            col.update_one,
            {"user_id": user_id},
            {"$set": {"failed_attempts": 0, "locked_until": now + LOGIN_LOCK_DURATION}},
        )
        return True, LOGIN_LOCK_DURATION

    await asyncio.to_thread(
        col.update_one,
        {"user_id": user_id},
        {"$set": {"failed_attempts": failed}},
    )
    return False, 0


async def reset_login_lock(user_id):
    await asyncio.to_thread(
        _col("login_locks").update_one,
        {"user_id": user_id},
        {"$set": {"failed_attempts": 0, "locked_until": None}},
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Combined helpers
# ---------------------------------------------------------------------------

async def reset_all_locks(user_id):
    """Reset all security locks for user (admin emergency command)."""
    await asyncio.to_thread(
        _col("security").update_one,
        {"user_id": user_id},
        {"$set": {"muted_until": None, "banned_until": None, "offence_count": 0}},
        upsert=True,
    )
    await reset_pin_lock(user_id)
    await reset_login_lock(user_id)


async def check_and_handle_flood(user_id):
    """Check for command flood / spam pattern."""
    now = time.time()
    col = _col("security")

    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "recent_count": {"$sum": "$offence_count"}}},
    ]

    def _aggregate():
        return list(col.aggregate(pipeline))

    results = await asyncio.to_thread(_aggregate)
    if results and results[0].get("recent_count", 0) > 5:
        await asyncio.to_thread(
            col.update_one,
            {"user_id": user_id},
            {"$set": {"banned_until": now + SPAM_BAN_DURATION}},
            upsert=True,
        )
        return True
    return False
