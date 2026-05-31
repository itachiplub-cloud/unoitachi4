from database import get_conn

with get_conn() as conn:
    broken = conn.execute("""
        SELECT file_id FROM deck
        WHERE file_id IS NULL OR file_id = '' OR file_id = 'None'
    """).fetchall()

    for row in broken:
        conn.execute("DELETE FROM deck WHERE file_id = ?", (row[0],))
    conn.commit()

print(f"🧹 Removed {len(broken)} broken deck entries.")
