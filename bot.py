import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
import handlers_core
import handlers_charge
import handlers_games

async def main():
    # تنظیمات لاگینگ برای ترمکس و هاست‌های ابری
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # راه‌اندازی دیتابیس
    await init_db()
    
    # ایجاد نمونه ربات و دیسپچر
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # ثبت روترها (ماژول‌ها)
    dp.include_router(handlers_core.router)
    dp.include_router(handlers_charge.router)
    dp.include_router(handlers_games.router)
    
    logging.info("Starting MEOWBET Bot...")
    
    # حذف وب‌هوک‌های قبلی و شروع پولینگ
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
