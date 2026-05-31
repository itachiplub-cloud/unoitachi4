from database import get_conn

with get_conn() as conn:
    try:
        conn.execute("ALTER TABLE users ADD COLUMN last_draw_time INTEGER DEFAULT 0;")
        conn.commit()
        print("✅ Column 'last_draw_time' added to users table.")
    except Exception as e:
        print(f"⚠️ Error: {e}")
