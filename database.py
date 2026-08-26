import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # جدول کاربران با حفظ موجودی قبلی (IF NOT EXISTS)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                referred_by INTEGER DEFAULT 0
            )
        """)
        # جدول گروه‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY
            )
        """)
        # جدول تنظیمات ربات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # تنظیم ضریب پیش‌فرض پوپ اگر وجود نداشت
        await db.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES ('pop_multiplier', '1.2')
        """)
        await db.commit()

async def add_user(user_id: int, username: str, ref_by: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        # چک کنیم کاربر قبلاً هست یا نه تا موجودیش صفر نشه
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            # اگر نبود با موجودی اولیه صفر یا هدیه ثبت بشه
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
                # اگر کاربر در دیتابیس نبود، اتوماتیک با موجودی صفر ثبتش کنیم که ارور نده
                await db.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, "Unknown", 0.0))
                await db.commit()
                return 0.0

async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        # اول مطمئن بشیم کاربر تو جدول هست
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            await db.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, "Unknown", 0.0))
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
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
