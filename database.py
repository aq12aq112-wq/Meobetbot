import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                referred_by INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # جدول تراکنش‌ها برای بخش شارژ و برداشت
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                status TEXT,
                receipt TEXT
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES ('pop_multiplier', '1.2')
        """)
        await db.commit()

async def add_user(user_id: int, username: str, ref_by: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, balance, referred_by) VALUES (?, ?, ?, ?)",
                (user_id, username, 0.0, ref_by)
            )
            await db.commit()

async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                await db.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, "Unknown", 0.0))
                await db.commit()
                return 0.0

async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            await db.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, "Unknown", 0.0))
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

# توابع مربوط به تراکنش‌ها که خطای ایمپورت رو می‌دادن
async def add_transaction(user_id: int, amount: float, t_type: str, status: str = "pending", receipt: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transactions (user_id, amount, type, status, receipt) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, t_type, status, receipt)
        )
        await db.commit()
        return cursor.lastrowid

async def get_transaction(tx_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, user_id, amount, type, status, receipt FROM transactions WHERE id = ?", (tx_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"id": row[0], "user_id": row[1], "amount": row[2], "type": row[3], "status": row[4], "receipt": row[5]}
            return None

async def update_transaction_status(tx_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE transactions SET status = ? WHERE id = ?", (status, tx_id))
        await db.commit()

async def get_referrals_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "1.2"

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def get_all_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_all_groups() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT group_id FROM groups") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
