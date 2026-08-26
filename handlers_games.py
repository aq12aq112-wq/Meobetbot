import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, update_balance

router = Router()

# دیکشنری‌های مدیریت بازی‌های فعال
active_dice_games = {}
active_pop_games = {}
active_mines_games = {}
active_crash_games = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        num = float(val_str.replace("k", ""))
        return num * 1000
    return float(val_str)


# ==========================================================
# 1. بخش صرافی و شارژ / انتقال موجودی (Trade & Exchange)
# ==========================================================
@router.message(F.text.regexp(r"^#کارت\s+(.+)$"))
async def set_card_number(message: Message):
    card = message.text.replace("#کارت", "").strip()
    await message.reply(f"💳 شماره کارت شما (`{card}`) با موفقیت ثبت شد. برای شارژ حساب به ادمین پیام دهید.", parse_mode="Markdown")

@router.message(F.text.regexp(r"^#انتقال\s+(\d+)\s+(.+)"))
async def transfer_coins(message: Message):
    parts = message.text.split()
    try:
        amount = parse_amount(parts[1])
        target_id = int(parts[2])
    except ValueError:
        await message.reply("⚠️ فرمت انتقال اشتباه است. مثال: `#انتقال 50k [ID]`", parse_mode="Markdown")
        return

    sender_id = message.from_user.id
    if sender_id == target_id:
        await message.reply("❌ نمی‌توانید به خودتان سکه انتقال دهید!")
        return

    sender_balance = await get_balance(sender_id)
    if sender_balance < amount:
        await message.reply("❌ موجودی کافی برای انتقال ندارید!")
        return

    await update_balance(sender_id, -amount)
    await update_balance(target_id, amount)
    await message.reply(f"✅ مبلغ `{amount:,.0f} میو` با موفقیت به کاربر مورد نظر انتقال یافت.", parse_mode="Markdown")


# ==========================================================
# 2. بازی تاس (زوج و فرد دستی ۳ مرحله‌ای)
# ==========================================================
@router.message(F.text.regexp(r"^#(زوج|فرد)\s+(.+)$"))
async def start_even_odd(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ این بازی فقط در گروه‌ها قابل اجراست!")
        return
    
    parts = message.text.replace("#", "").split()
    choice = parts[0]
    try:
        amount = parse_amount(parts[1])
    except ValueError:
        await message.reply("⚠️ مبلغ وارد شده معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < amount:
        await message.reply(f"❌ موجودی کافی نیست! موجودی: {balance:,.0f} میو")
        return

    await update_balance(user_id, -amount)
    active_dice_games[user_id] = {"choice": choice, "amount": amount, "rolls": []}

    await message.reply(
        f"🎲 **بازی تاس ({choice})**\nمبلغ شرط: `{amount:,.0f} میو`\n"
        f"لطفاً **۳ عدد تاس** 🎲 پشت سر هم بفرستید.",
        parse_mode="Markdown"
    )

@router.message(F.dice)
async def handle_user_dice(message: Message):
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


# ==========================================================
# 3. بازی پوپ مرحله‌ای استاندارد
# ==========================================================
@router.message(F.text.regexp(r"^(?:#)?پوپ\s+(.+)$"))
async def ask_pop_confirmation(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ بازی پوپ فقط در گروه قابل اجراست!")
        return

    try:
        amount = parse_amount(message.text.replace("#", "").split()[1])
    except ValueError:
        await message.reply("⚠️ مبلغ نامعتبر است.")
        return

    user_id = message.from_user.id
    if await get_balance(user_id) < amount:
        await message.reply("❌ موجودی کافی نیست!")
        return

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


# ==========================================================
# 4. بازی مین (Mines) حرفه‌ای
# ==========================================================
@router.message(F.text.regexp(r"^(?:#)?مین\s+(.+)$"))
async def start_mines(message: Message):
    if message.chat.type == "private": return
    try:
        amount = parse_amount(message.text.replace("#", "").split()[1])
    except ValueError: return await message.reply("⚠️ مبلغ نامعتبر.")

    user_id = message.from_user.id
    if await get_balance(user_id) < amount: return await message.reply("❌ موجودی کافی نیست!")

    await update_balance(user_id, -amount)
    active_mines_games[user_id] = {"bet": amount, "found": 0, "mine": random.randint(0, 8)}
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎", callback_data=f"mine_{user_id}_{i}") for i in range(3)],
        [InlineKeyboardButton(text="💎", callback_data=f"mine_{user_id}_{i+3}") for i in range(3)],
        [InlineKeyboardButton(text="💎", callback_data=f"mine_{user_id}_{i+6}") for i in range(3)]
    ])
    await message.reply(f"💣 **بازی مین (مینی‌سویپر)**\nمبلغ: `{amount:,.0f} میو`\nیکی را انتخاب کنید:", reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("mine_"))
async def click_mine(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id, idx = int(parts[1]), int(parts[2])
    if callback.from_user.id != owner_id: return await callback.answer("❌ خطا", show_alert=True)

    game = active_mines_games.pop(owner_id, None)
    if not game: return

    if idx == game["mine"]:
        await callback.message.edit_text("💥 بمب منفجر شد! باختی.")
    else:
        prize = game["bet"] * 1.8
        await update_balance(owner_id, prize)
        await callback.message.edit_text(f"💎 آفرین! الماس پیدا کردی. جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")


# ==========================================================
# 5. بازی انفجار (Crash)
# ==========================================================
@router.message(F.text.regexp(r"^(?:#)?انفجار\s+(.+)$"))
async def play_crash(message: Message):
    if message.chat.type == "private": return
    try:
        amount = parse_amount(message.text.replace("#", "").split()[1])
    except ValueError: return await message.reply("⚠️ مبلغ نامعتبر.")

    user_id = message.from_user.id
    if await get_balance(user_id) < amount: return await message.reply("❌ موجودی کافی نیست!")

    await update_balance(user_id, -amount)
    await message.reply(f"🚀 صعود موشک انفجار با مبلغ `{amount:,.0f} میو` شروع شد...", parse_mode="Markdown")
    
    await asyncio.sleep(2)
    crash_point = round(random.uniform(1.1, 3.5), 2)
    user_won = crash_point > 1.5

    if user_won:
        prize = amount * crash_point
        await update_balance(user_id, prize)
        await message.reply(f"🚀 موشک در ضریب **{crash_point}x** منفجر شد!\n🎉 **برنده شدی!** جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")
    else:
        await message.reply(f"💥 موشک زود منفجر شد (**{crash_point}x**)!\nباختی!", parse_mode="Markdown")

