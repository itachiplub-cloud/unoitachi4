from database import get_conn

def add_memory(uid: int, role: str, content: str):
    """
    Save a user or bot message for future context.
    role: "user" or "bot"
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_memory (uid, role, content) VALUES (?, ?, ?)",
            (uid, role, content),
        )
        conn.commit()

def get_memory(uid: int, limit: int = 5) -> list[dict]:
    """
    Retrieve the last `limit` memory items for uid,
    ordered oldest→newest.
    Returns a list of {"role": ..., "content": ...}.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT role, content
              FROM user_memory
             WHERE uid = ?
          ORDER BY id DESC
             LIMIT ?
            """,
            (uid, limit),
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def trim_memory(uid: int, keep: int = 20):
    """
    Keep only the most recent `keep` entries for this user.
    Call this periodically or right after adding new memory.
    """
    with get_conn() as conn:
        conn.execute(
            """
            DELETE FROM user_memory
             WHERE id NOT IN (
               SELECT id
                 FROM user_memory
                WHERE uid = ?
             ORDER BY id DESC
                LIMIT ?
             )
            """,
            (uid, keep)
        )
        conn.commit()
