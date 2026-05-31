from database import get_conn

with get_conn() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            gid INTEGER PRIMARY KEY,
            title TEXT,
            added_at INTEGER
        )
    """)
    conn.commit()

print("✅ 'groups' table created.")
