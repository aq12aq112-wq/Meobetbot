import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# اطلاعات پایه ربات، کارت و ادمین
BOT_TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"
ADMIN_CARD = "760188800770"
ADMIN_ID = 6937799221

# دیتابیس ساده و مقاوم
import aiosqlite
DB_PATH = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 10000.0,
                card TEXT DEFAULT ''
            )
        """)
        await db.commit()

async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 10000.0))
                await db.commit()
                return 10000.0
            return row[0]

async def update_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 10000.0)", (user_id,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

router = Router()
active_dice_games = {}
active_pop_games = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        return float(val_str.replace("k", "")) * 1000
    return float(val_str)

# 1. دستورات عمومی و استارت
@router.message(F.text.in_({"/start", "استارت"}))
async def cmd_start(message: Message):
    bal = await get_balance(message.from_user.id)
    await message.reply(
        f"🤖 **به ربات میوبت (MEOWBET) خوش آمدید!**\n\n"
        f"💳 موجودی فعلی: `{bal:,.0f} میو`\n"
        f"💳 شماره کارت شارژ: `{ADMIN_CARD}`\n\n"
        f"📖 برای دیدن راهنما کلمه `راهنما` را ارسال کنید.",
        parse_mode="Markdown"
    )

@router.message(F.text.in_({"راهنما", "/help", "❓ راهنما"}))
async def cmd_help(message: Message):
    text = (
        "📖 **راهنمای جامع بازی‌های میوبت**\n\n"
        "• موجودی: `موجودی`\n"
        "• تاس: `#زوج [مبلغ]` یا `#فرد [مبلغ]` (سپس ۳ تاس بفرستید)\n"
        "• پوپ: `#پوپ [مبلغ]` (۵ مرحله‌ای)\n"
        "• شارژ حساب: واریز به کارت و ارسال فیش به ادمین\n"
        "• انتقال: `#انتقال [مبلغ] [آیدی کاربر]`\n"
        "• پنل ادمین: دستور `/admin` (مخصوص مدیریت)"
    )
    await message.reply(text, parse_mode="Markdown")

@router.message(F.text.in_({"موجودی", "/balance"}))
async def cmd_balance(message: Message):
    bal = await get_balance(message.from_user.id)
    await message.reply(f"💳 موجودی حساب شما: `{bal:,.0f} میو`", parse_mode="Markdown")

# 2. پنل مدیریت
@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ شما دسترسی ادمین ندارید!")
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار ربات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⚙️ مدیریت حساب‌ها", callback_data="admin_users")]
    ])
    await message.reply("👑 **خوش آمدید، مدیر عزیز!**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ غیرمجاز", show_alert=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(balance) FROM users") as cursor:
            row = await cursor.fetchone()
            users_count = row[0]
            total_balance = row[1] or 0

    await callback.message.edit_text(
        f"📊 **آمار کلی ربات میوبت:**\n\n"
        f"👥 تعداد کل کاربران: `{users_count}` نفر\n"
        f"💰 مجموع موجودی کاربران: `{total_balance:,.0f} میو`",
        parse_mode="Markdown"
    )

# 3. بازی تاس دستی ۳ مرحله‌ای
@router.message(F.text.regexp(r"^#(زوج|فرد)\s+(.+)$"))
async def start_even_odd(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ این بازی فقط در گروه‌ها قابل اجراست!")
    
    parts = message.text.replace("#", "").split()
    choice = parts[0]
    try:
        amount = parse_amount(parts[1])
    except ValueError:
        return await message.reply("⚠️ مبلغ وارد شده معتبر نیست.")

    user_id = message.from_user.id
    if await get_balance(user_id) < amount:
        return await message.reply("❌ موجودی کافی نیست!")

    await update_balance(user_id, -amount)
    active_dice_games[user_id] = {"choice": choice, "amount": amount, "rolls": []}
    await message.reply(f"🎲 شرط `{choice}` به مبلغ `{amount:,.0f} میو` ثبت شد.\nلطفاً **۳ عدد تاس** 🎲 پشت سر هم بفرستید.", parse_mode="Markdown")

@router.message(F.dice)
async def handle_dice(message: Message):
    user_id = message.from_user.id
    if user_id not in active_dice_games or not message.dice:
        return

    game = active_dice_games[user_id]
    game["rolls"].append(message.dice.value)

    if len(game["rolls"]) < 3:
        await message.reply(f"🎲 تاس {len(game['rolls'])} ثبت شد. {3 - len(game['rolls'])} تاس دیگر بفرستید.")
    else:
        total = sum(game["rolls"])
        is_even = total % 2 == 0
        won = (game["choice"] == "زوج" and is_even) or (game["choice"] == "فرد" and not is_even)
        rolls_str = " + ".join(map(str, game["rolls"]))

        if won:
            prize = game["amount"] * 1.95
            await update_balance(user_id, prize)
            await message.reply(f"🎲 تاس‌ها: `{rolls_str} = {total}`\n🎉 **برنده شدی!** جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")
        else:
            await message.reply(f"🎲 تاس‌ها: `{rolls_str} = {total}`\n💥 **باختی!**", parse_mode="Markdown")
        del active_dice_games[user_id]

# 4. بازی پوپ مرحله‌ای
@router.message(F.text.regexp(r"^(?:#)?پوپ\s+(.+)$"))
async def ask_pop(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ بازی پوپ فقط در گروه قابل اجراست!")
    try:
        amount = parse_amount(message.text.replace("#", "").split()[1])
    except ValueError:
        return await message.reply("⚠️ مبلغ نامعتبر.")

    user_id = message.from_user.id
    if await get_balance(user_id) < amount:
        return await message.reply("❌ موجودی کافی نیست!")

    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ شروع بازی", callback_data=f"pop_start_{user_id}_{amount}"),
        InlineKeyboardButton(text="❌ لغو", callback_data=f"pop_cancel_{user_id}")
    ]])
    await message.reply(f"💩 **بازی پوپ**\nمبلغ: `{amount:,.0f} میو`", reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("pop_start_"))
async def start_pop(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id, amount = int(parts[2]), float(parts[3])
    if callback.from_user.id != owner_id:
        return await callback.answer("❌ برای شما نیست!", show_alert=True)

    await update_balance(owner_id, -amount)
    stages_config = [[0,0,0,1], [0,0,0,1], [0,0,1,1], [0,0,1,1], [0,1,1,1]]
    stages = [row.copy() for row in stages_config]
    for r in stages: random.shuffle(r)

    active_pop_games[owner_id] = {
        "bet": amount, "current_stage": 0, "stages": stages,
        "multipliers": [1.2, 1.5, 2.0, 3.0, 4.0],
        "history": ["⚪"]*5, "revealed_rows": {}
    }
    await render_pop(callback.message, owner_id, is_edit=True)

async def render_pop(message: Message, user_id: int, is_edit=False):
    game = active_pop_games.get(user_id)
    if not game: return
    stage, bet = game["current_stage"], game["bet"]
    curr_mult = game["multipliers"][stage] if stage < 5 else 4.0
    curr_prize = bet * game["multipliers"][stage - 1] if stage > 0 else bet

    text = f"💩 **پوپ مرحله‌ای**\nمرحله {stage+1}/5 | ضریب: `{curr_mult}x`\nجایزه: `{curr_prize:,.0f} میو`"
    keyboard = []
    for r in range(5):
        row_btns = []
        for c in range(4):
            if r in game["revealed_rows"]:
                icon = "💩" if game["revealed_rows"][r][c] == 1 else "🟢"
                row_btns.append(InlineKeyboardButton(text=icon, callback_data="none"))
            elif r == stage:
                row_btns.append(InlineKeyboardButton(text="⚪", callback_data=f"pop_click_{user_id}_{r}_{c}"))
            else:
                row_btns.append(InlineKeyboardButton(text="🔒", callback_data="none"))
        keyboard.append(row_btns)
    if stage > 0 and stage < 5:
        keyboard.append([InlineKeyboardButton(text=f"💵 برداشت ({curr_prize:,.0f} میو)", callback_data=f"pop_cash_{user_id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if is_edit: await message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    else: await message.reply(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("pop_click_"))
async def click_pop(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id, stg, col = int(parts[2]), int(parts[3]), int(parts[4])
    if callback.from_user.id != owner_id: return await callback.answer("❌ خطا", show_alert=True)

    game = active_pop_games.get(owner_id)
    if not game or game["current_stage"] != stg: return

    row_data = game["stages"][stg]
    game["revealed_rows"][stg] = row_data
    if row_data[col] == 1:
        game["history"][stg] = "💩"
        for r in range(5): game["revealed_rows"][r] = game["stages"][r]
        await render_pop(callback.message, owner_id, is_edit=True)
        await callback.message.answer("💥 به پوپ خوردی و باختی!")
        del active_pop_games[owner_id]
    else:
        game["history"][stg] = "🟢"
        game["current_stage"] += 1
        if game["current_stage"] >= 5:
            prize = game["bet"] * 4.0
            await update_balance(owner_id, prize)
            await render_pop(callback.message, owner_id, is_edit=True)
            await callback.message.answer(f"🏆 برنده نهایی! جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")
            del active_pop_games[owner_id]
        else:
            await render_pop(callback.message, owner_id, is_edit=True)

@router.callback_query(F.data.startswith("pop_cash_"))
async def cash_pop(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id: return
    game = active_pop_games.pop(owner_id, None)
    if not game: return
    prize = game["bet"] * game["multipliers"][game["current_stage"] - 1]
    await update_balance(owner_id, prize)
    await callback.message.edit_text(f"💵 برداشت موفق: `{prize:,.0f} میو`", parse_mode="Markdown")

# راه اندازی اصلی
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 MeowBot is up and running successfully with config!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

