import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers_core import router as core_router
from handlers_charge import router as charge_router
from database import init_db

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # راه‌اندازی دیتابیس
    await init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # ثبت روترها
    dp.include_router(core_router)
    dp.include_router(charge_router)
    
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
