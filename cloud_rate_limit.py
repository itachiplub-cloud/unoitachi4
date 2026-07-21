import time
import asyncio
from cloud_db import get_cloud_db
from cloud_config import RATE_LIMITS


def _col():
    return get_cloud_db()["rate_limits"]


def get_rate_limit_config(action):
    return RATE_LIMITS.get(action, 5)


async def check_rate_limit(user_id, action):
    """Returns (allowed: bool, wait_seconds: int)"""
    limit = get_rate_limit_config(action)
    now = time.time()
    window = 60  # per-minute window

    def _query():
        return list(_col().find({
            "user_id": user_id,
            "action": action,
            "timestamp": {"$gt": now - window},
        }))

    records = await asyncio.to_thread(_query)

    if len(records) >= limit:
        oldest = min(r["timestamp"] for r in records)
        wait = int(window - (now - oldest)) + 1
        return False, max(wait, 1)

    return True, 0


async def record_action(user_id, action):
    """Record an action timestamp."""
    doc = {
        "user_id": user_id,
        "action": action,
        "timestamp": time.time(),
        "count": 1,
    }
    await asyncio.to_thread(_col().insert_one, doc)
