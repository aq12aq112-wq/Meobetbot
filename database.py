import aiosqlite
import os

DB_PATH = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 10000.0
            )
        """)
        await db.commit()

async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                # اگر کاربر جدید بود، موجودی اولیه بده
                await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 10000.0))
                await db.commit()
                return 10000.0
            return row[0]

async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        # ابتدا مطمئن شویم کاربر در جدول وجود دارد
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 10000.0)", (user_id,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()
