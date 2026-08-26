import os
import aiosqlite
from config import DB_PATH

async def init_db():
    # تضمین اینکه مسیر دیتابیس همیشه مطلق و امن باشد تا با آپدیت‌ها پاک نشود
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
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
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        # بررسی اینکه آیا کاربر قبلاً وجود دارد یا خیر
        async with db.execute("SELECT user_id, balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            # اگر کاربر جدید بود، با موجودی صفر ثبت شود
            await db.execute(
                "INSERT INTO users (user_id, username, balance, referred_by) VALUES (?, ?, 0.0, ?)",
                (user_id, username, ref_by)
            )
            await db.commit()
        else:
            # اگر کاربر از قبل بود، فقط در صورت داشتن یوزرنیم جدید، آن را آپدیت کن و به هیچ وجه به balance دست نزن
            if username and username != "Unknown":
                await db.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )
                await db.commit()

async def get_balance(user_id: int) -> float:
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return float(row[0] if row[0] is not None else 0.0)
            else:
                # اگر کاربر در دیتابیس نبود، با احتیاط ایجادش کن بدون اینکه خطایی بدهد
                await db.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0.0)", (user_id, "Unknown"))
                await db.commit()
                return 0.0

async def update_balance(user_id: int, amount: float):
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            await db.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, "Unknown", 0.0))
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def add_transaction(user_id: int, amount: float, t_type: str, status: str = "pending", receipt: str = "") -> int:
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "INSERT INTO transactions (user_id, amount, type, status, receipt) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, t_type, status, receipt)
        )
        await db.commit()
        return cursor.lastrowid

async def get_transaction(tx_id: int):
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT id, user_id, amount, type, status, receipt FROM transactions WHERE id = ?", (tx_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"id": row[0], "user_id": row[1], "amount": row[2], "type": row[3], "status": row[4], "receipt": row[5]}
            return None

async def update_transaction_status(tx_id: int, status: str):
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE transactions SET status = ? WHERE id = ?", (status, tx_id))
        await db.commit()

async def get_referrals_count(user_id: int) -> int:
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_setting(key: str) -> str:
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "1.2"

async def set_setting(key: str, value: str):
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def get_all_users() -> list:
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_all_groups() -> list:
    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT group_id FROM groups") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
