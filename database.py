import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                ref_by INTEGER DEFAULT 0
            )
        """)
        # جدول تراکنش‌های شارژ
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                receipt TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        # جدول تاریخچه بازی‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_name TEXT,
                amount REAL,
                result TEXT,
                profit REAL
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, username, balance, ref_by FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"user_id": row[0], "username": row[1], "balance": row[2], "ref_by": row[3]}
            return None

async def add_user(user_id: int, username: str, ref_by: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(user_id)
        if not user:
            await db.execute("INSERT INTO users (user_id, username, balance, ref_by) VALUES (?, ?, 0.0, ?)", (user_id, username, ref_by))
            await db.commit()

async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_balance(user_id: int) -> float:
    user = await get_user(user_id)
    return user["balance"] if user else 0.0

async def add_transaction(user_id: int, amount: float, receipt: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO transactions (user_id, amount, receipt, status) VALUES (?, ?, ?, 'pending')", (user_id, amount, receipt))
        await db.commit()
        return cursor.lastrowid

async def get_transaction(tx_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tx_id, user_id, amount, receipt, status FROM transactions WHERE tx_id = ?", (tx_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"tx_id": row[0], "user_id": row[1], "amount": row[2], "receipt": row[3], "status": row[4]}
            return None

async def update_transaction_status(tx_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE transactions SET status = ? WHERE tx_id = ?", (status, tx_id))
        await db.commit()

async def get_referrals_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE ref_by = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
