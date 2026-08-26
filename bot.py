import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db

# ایمپورت روترهای ماژول‌های مختلف
from handlers_core import router as core_router
from handlers_charge import router as charge_router
from handlers_games import router as games_router
from handlers_help import router as help_router
from handlers_admin import router as admin_router

async def main():
    # راه‌اندازی دیتابیس و جداول
    await init_db()
    
    # تنظیمات ربات و دیسپچر
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ثبت تمامی روترها به ترتیب درست
    dp.include_router(core_router)
    dp.include_router(charge_router)
    dp.include_router(games_router)
    dp.include_router(help_router)
    dp.include_router(admin_router)

    # پاک کردن وب‌هوک قبلی و شروع پولینگ
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Bot is up and running successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
