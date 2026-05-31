from database import get_conn

with get_conn() as conn:
    schema = conn.execute("PRAGMA table_info(users)").fetchall()
    for col in schema:
        print(col)
