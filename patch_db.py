import os

override_code = """

# --- MONGODB OVERRIDES ---
from mongo_users import *

# Redefine mixed function
def get_all_vehicle_owners():
    try:
        # We need get_conn from this file
        with get_conn() as conn:
            result = conn.execute('''
                SELECT user_id FROM bikes
                UNION
                SELECT user_id FROM cars
            ''').fetchall()
        
        owner_ids = [row[0] for row in result]
        
        # Now fetch from MongoDB
        users = users_col.find({"id": {"$in": owner_ids}})
        return [{"user_id": u["id"], "username": u.get("username", "Unknown")} for u in users]
    except Exception as e:
        print(f"Error in get_all_vehicle_owners: {e}")
        return []
"""

def patch():
    with open('database.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if '# --- MONGODB OVERRIDES ---' not in content:
        with open('database.py', 'a', encoding='utf-8') as f:
            f.write(override_code)
            print('Appended overrides to database.py')
    else:
        print('Overrides already exist.')

if __name__ == '__main__':
    patch()
