import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# ایمپورت تنظیمات و دیتابیس
try:
    from config import BOT_TOKEN
except ImportError:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

from database import init_db

# ایمپورت روترهای مختلف ربات
from handlers_games import router as games_router
from handlers_help import router as help_router
# اگر هندلر دیگه‌ای مثل شارژ یا موجودی داری، می‌تونی این بالا ایمپورت کنی
# from handlers_charge import router as charge_router

logging.basicConfig(level=logging.INFO)

async def main():
    if not BOT_TOKEN:
        print("❌ خطا: توکن ربات (BOT_TOKEN) یافت نشد! لطفاً در فایل config.py یا متغیرهای محیطی تنظیمش کنید.")
        return

    # راه‌اندازی ربات و دیسپچر
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ساخت و بررسی جداول دیتابیس در شروع کار
    await init_db()
    print("✅ دیتابیس با موفقیت متصل و آماده شد.")

    # اضافه کردن روترها به دیسپچر
    dp.include_router(games_router)
    dp.include_router(help_router)
    # اگر روتر شارژ یا موجودی داری این خط رو فعال کن:
    # dp.include_router(charge_router)

    print("🚀 ربات میوبت (MEOWBET) با موفقیت روشن شد و در حال دریافت پیام است...")

    # حذف وب‌هوک قبلی و شروع پولینگ
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 ربات متوقف شد.")
