import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# تنظیمات پایه
BOT_TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"
ADMIN_CARD = "760188800770"
ADMIN_ID = 6937799221

# دیتابیس مقاوم
import aiosqlite
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
active_pop_games = {}
active_charge_requests = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        return float(val_str.replace("k", "")) * 1000
    return float(val_str)

# کیبورد اصلی شیشه‌ای
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 حساب کاربری و موجودی", callback_data="menu_profile")],
        [
            InlineKeyboardButton(text="💳 شارژ حساب", callback_data="menu_charge"),
            InlineKeyboardButton(text="💵 برداشت وجه", callback_data="menu_withdraw")
        ],
        [InlineKeyboardButton(text="📖 راهنمای بازی‌ها", callback_data="menu_help")]
    ])

# 1. دستور استارت
@router.message(F.text.in_({"/start", "استارت", "منو"}))
async def cmd_start(message: Message):
    await message.reply(
        "Meowie bet🐱\n\n"
        "از کازینو با ربات میویی خسته شدی؟ میتونی با میوبت تک... فرست (نه فوروارد!).",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("menu_"))
async def handle_menu_callbacks(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    user_id = callback.from_user.id

    if action == "profile":
        bal = await get_balance(user_id)
        text = f"👤 **حساب کاربری شما:**\n\n🆔 آیدی: `{user_id}`\n💳 موجودی: `{bal:,.0f} میو`"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="menu_back")]])
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    elif action == "charge":
        active_charge_requests[user_id] = "awaiting_amount"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ لغو", callback_data="menu_back")]])
        await callback.message.edit_text(
            "💰 **شارژ موجودی**\n\nمبلغ شارژت رو به عدد بفرست، مثلاً: `50000` یا `500k`",
            reply_markup=markup, parse_mode="Markdown"
        )

    elif action == "withdraw":
        text = "💵 برای برداشت موجودی، مقدار و شماره کارت خود را برای ادمین ارسال کنید."
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="menu_back")]])
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    elif action == "help":
        text = (
            "📖 **راهنمای جامع بازی‌های میوبت:**\n\n"
            "• **پوپ:** `#پوپ [مبلغ]` (مثل `#پوپ 20k`)\n"
            "• شارژ حساب از منوی شیشه‌ای\n"
            "• انتقال موجودی: `#انتقال [مبلغ] [آیدی]`"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="menu_back")]])
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    elif action == "back":
        await callback.message.edit_text(
            "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت...",
            reply_markup=get_main_menu(), parse_mode="Markdown"
        )
    await callback.answer()

# 2. مکانیزم شارژ حساب (کارت به کارت)
@router.message(F.text & ~F.text.startswith("#"))
async def handle_text_messages(message: Message):
    user_id = message.from_user.id
    if user_id in active_charge_requests and active_charge_requests[user_id] == "awaiting_amount":
        try:
            amount = parse_amount(message.text)
        except ValueError:
            return await message.reply("⚠️ مبلغ نامعتبر است. لطفاً فقط عدد یا به صورت 50k وارد کنید.")

        del active_charge_requests[user_id]
        receipt_id = f"{random.randint(100000, 999999)}#{random.choice(['eed', 'abc', 'xyz'])}"
        
        text = (
            f"🐱 کارت به کارت میویی 💳\n"
            f"┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
            f"💳 **به کارت زیر واریز کن:**\n`{ADMIN_CARD}`\n\n"
            f"💰 مبلغ: `{amount:,.0f} میو`\n\n"
            f"بعد از واریز، رسید رو همینجا بفرست."
        )
        
        # دکمه تایید ادمین برای شارژ آنی
        admin_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأیید و واریز به حساب", callback_data=f"admin_approve_{user_id}_{int(amount)}")]
        ])
        
        await message.reply(text, reply_markup=admin_markup, parse_mode="Markdown")
        
        # ارسال گزارش به ادمین
        try:
            await message.bot.send_message(
                ADMIN_ID,
                f"📥 **درخواست شارژ جدید:**\n👤 کاربر: `{user_id}`\n💰 مبلغ: `{amount:,.0f} میو`\n📌 شناسه: `{receipt_id}`",
                reply_markup=admin_markup, parse_mode="Markdown"
            )
        except Exception:
            pass

@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_charge(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ دسترسی غیرمجاز!", show_alert=True)
    
    parts = callback.data.split("_")
    target_user_id = int(parts[2])
    amount = float(parts[3])

    await update_balance(target_user_id, amount)
    await callback.message.edit_text(f"✅ پرداخت تأیید شد.\n💰 `{amount:,.0f} میو` به حساب کاربر واریز شد.", parse_mode="Markdown")
    try:
        await callback.bot.send_message(target_user_id, f"✅ شارژ حساب شما به مبلغ `{amount:,.0f} میو` با موفقیت تأیید و واریز شد!", parse_mode="Markdown")
    except Exception:
        pass


# 3. بازی پوپ حرفه‌ای (دقیقاً مشابه عکس‌ها)
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

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 شروع بازی", callback_data=f"pop_start_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ لغو", callback_data=f"pop_cancel_{user_id}")
        ]
    ])
    
    text = (
        f"Meowie bet🐱\n"
        f"┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
        f"💩 **بازی پوپ**\n"
        f"👤 بازیکن: {message.from_user.mention_html()}\n\n"
        f"💰 مبلغ شرط: `{amount:,.0f} میو`\n"
        f"📊 ۵ مرحله، هر مرحله ۴ خانه\n"
        f"💩 خانه‌های پوپ رو نزن!\n\n"
        f"بازی رو شروع کنی؟"
    )
    await message.reply(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("pop_cancel_"))
async def cancel_pop(callback: CallbackQuery):
    if callback.from_user.id != int(callback.data.split("_")[2]):
        return await callback.answer("❌ برای شما نیست!", show_alert=True)
    await callback.message.edit_text("❌ بازی لغو شد.")

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
        "revealed_rows": {}
    }
    await render_pop(callback.message, owner_id, is_edit=True)

async def render_pop(message: Message, user_id: int, is_edit=False):
    game = active_pop_games.get(user_id)
    if not game: return
    stage, bet = game["current_stage"], game["bet"]
    curr_mult = game["multipliers"][stage] if stage < 5 else 4.0
    curr_prize = bet * game["multipliers"][stage - 1] if stage > 0 else bet

    text = (
        f"Meowie bet🐱\n"
        f"┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
        f"💩 پوپ — 👤 بازیکن\n"
        f"🎮 مرحله {stage+1} از ۵\n"
        f"💰 شرط: `{bet:,.0f} میو`\n"
        f"📈 جایزه فعلی: `{curr_prize:,.0f} میو`"
    )

    keyboard = []
    # ردیف‌ها از پایین به بالا یا بالا به پایین طبق استاندارد
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
    if callback.from_user.id != owner_id: return await callback.answer("❌ این بازی شما نیست!", show_alert=True)

    game = active_pop_games.get(owner_id)
    if not game or game["current_stage"] != stg: return

    row_data = game["stages"][stg]
    game["revealed_rows"][stg] = row_data
    if row_data[col] == 1:
        # باخت
        for r in range(5): game["revealed_rows"][r] = game["stages"][r]
        await render_pop(callback.message, owner_id, is_edit=True)
        await callback.message.answer("💥 به پوپ خوردی و باختی!")
        del active_pop_games[owner_id]
    else:
        game["current_stage"] += 1
        if game["current_stage"] >= 5:
            prize = game["bet"] * 4.0
            await update_balance(owner_id, prize)
            for r in range(5): game["revealed_rows"][r] = game["stages"][r]
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
    for r in range(5): game["revealed_rows"][r] = game["stages"][r]
    await render_pop(callback.message, owner_id, is_edit=True)
    await callback.message.answer(f"💵 برداشت موفق!\n💰 جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")

# اجرای ربات
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 MeowBet Pro Bot is running smoothly!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

