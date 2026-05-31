import time
import random
from database import get_conn, update_balance



def setup_bank_tables():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                name TEXT PRIMARY KEY,
                type TEXT,
                cost INTEGER,
                yield INTEGER,
                risk TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_assets (
                uid INTEGER,
                asset_name TEXT,
                quantity INTEGER,
                last_collected INTEGER,
                FOREIGN KEY(asset_name) REFERENCES assets(name)
            )
        """)
    insert_sample_assets()

def setup_badge_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                uid INTEGER PRIMARY KEY,
                badge TEXT
            )
        """)

def setup_dynamic_prices():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asset_prices (
                name TEXT,
                timestamp INTEGER,
                price INTEGER
            )
        """)

def setup_achievements_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                uid INTEGER,
                first_investment INTEGER,
                assets_owned INTEGER,
                max_income INTEGER,
                diversified INTEGER
            )
        """)

def setup_quest_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                uid INTEGER,
                quest_name TEXT,
                completed INTEGER DEFAULT 0
            )
        """)

def setup_group_goals_table():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_goals (
                goal_name TEXT PRIMARY KEY,
                target INTEGER,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0
            )
        """)


def insert_sample_assets():
    assets = [
        ("Gold Bar", "gold", 500, 10, "low"),
        ("Crypto Coin", "crypto", 300, 25, "high"),
        ("Rental Property", "property", 1000, 50, "medium"),
        ("Dragon Egg", "fantasy", 1500, 100, "legendary"),
        ("Silver Coin", "silver", 200, 5, "low"),
        ("NFT Sword", "crypto", 800, 40, "high"),
        ("BITCOIN", "crypto", 200000, 200000, "high")

    ]
    with get_conn() as conn:
        for a in assets:
            exists = conn.execute("SELECT 1 FROM assets WHERE name=?", (a[0],)).fetchone()
            if not exists:
                conn.execute("INSERT INTO assets (name, type, cost, yield, risk) VALUES (?, ?, ?, ?, ?)", a)

def get_asset_market():
    with get_conn() as conn:
        return conn.execute("SELECT name, type, cost, yield, risk FROM assets").fetchall()

def get_user_assets(uid):
    with get_conn() as conn:
        return conn.execute("""
            SELECT a.name, a.type, a.cost, a.yield, a.risk, ua.quantity
            FROM user_assets ua
            JOIN assets a ON ua.asset_name = a.name
            WHERE ua.uid = ?
        """, (uid,)).fetchall()

def buy_asset(uid, asset_name, quantity):
    now = int(time.time())
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT quantity FROM user_assets WHERE uid=? AND asset_name=?", (uid, asset_name)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_assets SET quantity = quantity + ?, last_collected = ? WHERE uid=? AND asset_name=?",
                (quantity, now, uid, asset_name)
            )
        else:
            conn.execute(
                "INSERT INTO user_assets (uid, asset_name, quantity, last_collected) VALUES (?, ?, ?, ?)",
                (uid, asset_name, quantity, now)
            )

def seed_asset_prices():
    now = int(time.time())
    assets = get_asset_market()
    with get_conn() as conn:
        for name, *_ in assets:
            latest = conn.execute(
                "SELECT 1 FROM asset_prices WHERE name=? ORDER BY timestamp DESC LIMIT 1",
                (name,)
            ).fetchone()
            if not latest:
                base_price = conn.execute("SELECT cost FROM assets WHERE name=?", (name,)).fetchone()[0]
                conn.execute("INSERT INTO asset_prices (name, timestamp, price) VALUES (?, ?, ?)", (name, now, base_price))

def fluctuate_asset_prices():
    now = int(time.time())
    with get_conn() as conn:
        assets = conn.execute("SELECT name FROM assets").fetchall()
        for (name,) in assets:
            last_price = conn.execute(
                "SELECT price FROM asset_prices WHERE name=? ORDER BY timestamp DESC LIMIT 1",
                (name,)
            ).fetchone()[0]
            change = random.randint(-30, 50)
            new_price = max(100, last_price + change)
            conn.execute("INSERT INTO asset_prices (name, timestamp, price) VALUES (?, ?, ?)", (name, now, new_price))

def scheduled_asset_appreciation():
    now = int(time.time())
    with get_conn() as conn:
        assets = conn.execute("SELECT name, cost FROM assets").fetchall()
        for name, cost in assets:
            bump = random.randint(5, 25)
            new_cost = cost + bump
            conn.execute("UPDATE assets SET cost=? WHERE name=?", (new_cost, name))
            conn.execute("INSERT INTO asset_prices (name, timestamp, price) VALUES (?, ?, ?)", (name, now, new_cost))

def assign_investor_badge(uid):
    assets = get_user_assets(uid)
    total_value = sum(cost * qty for _, _, cost, _, _, qty in assets)
    if total_value >= 10000:
        badge = "💎 Vault Keeper"
    elif total_value >= 5000:
        badge = "🏦 Shadow Banker"
    elif total_value >= 2500:
        badge = "📈 Crypto Monk"
    elif total_value >= 1000:
        badge = "🥇 Gold Tycoon"
    else:
        badge = "💼 Novice Investor"
    with get_conn() as conn:
        conn.execute("REPLACE INTO badges (uid, badge) VALUES (?, ?)", (uid, badge))
        conn.commit()

def update_achievements(uid):
    assets = get_user_assets(uid)
    total_assets = sum(qty for *_, qty in assets)
    daily_income = sum(int(yield_ or 0) * int(qty or 0) for name, type_, cost, yield_, risk, qty in assets)
    asset_types = set(type_ for _, type_, *_, qty in assets if qty > 0)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM achievements WHERE uid=?", (uid,)).fetchone()
        if not row:
            conn.execute("INSERT INTO achievements VALUES (?, ?, ?, ?, ?)",
                         (uid, int(time.time()), total_assets, daily_income, len(asset_types)))
        else:
            conn.execute("""
                UPDATE achievements SET
                    assets_owned=?,
                    max_income=?,
                    diversified=?
                WHERE uid=?
            """, (total_assets, daily_income, len(asset_types), uid))

ASSET_LORE = {
    "Dragon Egg": "Forged in the volcanic heart of Mt. Amaterasu, this egg pulses with ancient chakra.",
    "NFT Sword": "A blade encoded with blockchain fury, wielded by the algorithmic ronin.",
    "Crypto Coin": "A volatile relic from the digital underworld, blessed by market spirits.",
    "Gold Bar": "Mined from the vaults of Konoha, this bar glows with economic stability.",
    "Rental Property": "A stable income source built on the foundations of shinobi real estate.",
    "Silver Coin": "A humble yet reliable token from the merchant clans of the Hidden Market."
}

def apply_flash_discount(asset_name, percent):
    with get_conn() as conn:
        conn.execute("UPDATE assets SET cost = cost - (cost * ? / 100) WHERE name=?", (percent, asset_name))

def remove_flash_discount(asset_name: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT cost FROM assets WHERE name = ?", (asset_name,)).fetchone()
        if not row:
            return False
        base_cost = row[0]
        ts = int(time.time())
        conn.execute("INSERT INTO asset_prices (name, price, timestamp) VALUES (?, ?, ?)", (asset_name, base_cost, ts))
        conn.commit()
    return True

def auto_collect_income():
    now = int(time.time())
    updated_users = []

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT ua.uid, a.yield, ua.quantity, ua.asset_name, ua.last_collected
            FROM user_assets ua
            JOIN assets a ON ua.asset_name = a.name
        """).fetchall()

    for uid, yield_, qty, name, last_collected in rows:
        if now - last_collected >= 86400:
            income = yield_ * qty
            update_balance(uid, income)
            with get_conn() as conn:
                conn.execute("UPDATE user_assets SET last_collected=? WHERE uid=? AND asset_name=?", (now, uid, name))
                conn.commit()
            updated_users.append(uid)

    for uid in updated_users:
        assign_investor_badge(uid)


QUESTS = [
    ("First Investment", lambda uid: len(get_user_assets(uid)) >= 1),
    ("Diversify Portfolio", lambda uid: len(set(a[1] for a in get_user_assets(uid))) >= 3),
    ("Passive Tycoon", lambda uid: sum(a[3] * a[5] for a in get_user_assets(uid)) >= 500),
    ("Shinobi Banker", lambda uid: sum(a[2] * a[5] for a in get_user_assets(uid)) >= 5000),
    ("Intermediate", lambda uid: sum(a[3] * a[5] for a in get_user_assets(uid)) >= 10000),
    ("Richest", lambda uid: sum(a[2] * a[5] for a in get_user_assets(uid)) >= 500000),

]

__all__ = [
    "setup_bank_tables", "get_asset_market", "buy_asset", "get_user_assets",
    "setup_dynamic_prices", "seed_asset_prices", "fluctuate_asset_prices",
    "assign_investor_badge", "update_achievements", "ASSET_LORE",
    "setup_badge_table", "setup_achievements_table", "apply_flash_discount",
    "auto_collect_income", "scheduled_asset_appreciation",
    "setup_quest_table", "setup_group_goals_table",
    "remove_flash_discount", "QUESTS"
]
