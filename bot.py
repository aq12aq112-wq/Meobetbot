import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# ایمپورت تنظیمات و دیتابیس
try:
    from config import BOT_TOKEN
except ImportError:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

from database import init_db, add_user, get_balance

# ایمپورت روترهای مختلف ربات
from handlers_games import router as games_router
from handlers_help import router as help_router

# روتر برای دستور استارت و منوی اصلی
start_router = Router()

@start_router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # ثبت کاربر در دیتابیس در صورت عدم وجود
    await add_user(user_id, username)
    balance = await get_balance(user_id)

    if message.chat.type == "private":
        text = (
            f"🐾 **سلام {message.from_user.first_name} عزیز به ربات میوبت (MEOWBET) خوش آمدید!** 🎰\n\n"
            f"💰 موجودی فعلی شما: `{balance:,.0f} میو`\n\n"
            f"👇 از گزینه‌های زیر یا دستورات درون گروه‌ها استفاده کنید:"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 موجودی", callback_data="btn_balance"),
             InlineKeyboardButton(text="💳 شارژ حساب", callback_data="btn_charge")],
            [InlineKeyboardButton(text="❓ راهنمای بازی‌ها", callback_data="btn_help")]
        ])
        await message.reply(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.reply(f"🐱 {message.from_user.first_name} عزیز، ربات میوبت آماده‌ی بازیه! برای دیدن راهنما کلمه **راهنما** رو بفرست.")

logging.basicConfig(level=logging.INFO)

async def main():
    if not BOT_TOKEN:
        print("❌ خطا: توکن ربات (BOT_TOKEN) یافت نشد!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # راه‌اندازی دیتابیس
    await init_db()
    print("✅ دیتابیس با موفقیت متصل و آماده شد.")

    # اضافه کردن تمام روترها به دیسپچر
    dp.include_router(start_router)
    dp.include_router(games_router)
    dp.include_router(help_router)

    print("🚀 ربات میوبت (MEOWBET) با موفقیت روشن شد و در حال دریافت پیام است...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 ربات متوقف شد.")
