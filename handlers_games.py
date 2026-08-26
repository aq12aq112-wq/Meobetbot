import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, update_balance

router = Router()

# دیکشنری برای مدیریت بازی‌های فعال تاس و پوپ کاربران
active_dice_games = {}
active_pop_games = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        num = float(val_str.replace("k", ""))
        return num * 1000
    return float(val_str)

# ==================== ۱. بازی تاس (۳ مرحله‌ای دستی) ====================
@router.message(F.text.regexp(r"^#(زوج|فرد)\s+(.+)$"))
async def start_even_odd(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ این بازی فقط در گروه‌ها قابل اجراست!")
        return
    
    text_parts = message.text.replace("#", "").split()
    choice = text_parts[0]
    try:
        amount = parse_amount(text_parts[1])
    except ValueError:
        await message.reply("⚠️ مبلغ وارد شده معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < amount:
        await message.reply(f"❌ موجودی کافی نیست! موجودی: {balance:,.0f} میو")
        return

    # کسر مبلغ از کاربر به صورت امانت تا پایان بازی
    await update_balance(user_id, -amount)

    # ثبت بازی فعال برای این کاربر
    active_dice_games[user_id] = {
        "choice": choice,
        "amount": amount,
        "rolls": []
    }

    await message.reply(
        f"🎲 [{message.from_user.mention_html()}] عزیز، درخواست شما ثبت شد!\n"
        f"لطفاً **۳ عدد تاس** 🎲 پشت سر هم بفرستید تا مجموع آن‌ها محاسبه شود.",
        parse_mode="HTML"
    )

@router.message(F.dice)
async def handle_user_dice(message: Message):
    user_id = message.from_user.id
    if user_id not in active_dice_games:
        return # اگر بازی تاس فعالی نداشت، کاری نداشته باش

    # بررسی اینکه آیا کاربر تاس فرستاده است (مقدار dice وجود دارد)
    if not message.dice:
        return

    game = active_dice_games[user_id]
    dice_value = message.dice.value
    game["rolls"].append(dice_value)

    current_roll_count = len(game["rolls"])

    if current_roll_count < 3:
        await message.reply(f"🎲 تاس شماره {current_roll_count} ثبت شد (`{dice_value}`). {3 - current_roll_count} تاس دیگر بفرستید.", parse_mode="Markdown")
    else:
        # ۳ تاس کامل شد
        total_sum = sum(game["rolls"])
        is_even = total_sum % 2 == 0
        user_choice = game["choice"]
        amount = game["amount"]

        user_won = (user_choice == "زوج" and is_even) or (user_choice == "فرد" and not is_even)
        rolls_str = " + ".join(map(str, game["rolls"]))

        if user_won:
            prize = amount * 1.95
            await update_balance(user_id, prize)
            await message.reply(
                f"🎲 تاس‌ها: `{rolls_str} = {total_sum}` ({'زوج' if is_even else 'فرد'})\n"
                f"🎉 **تبریک می‌گم بردید!**\nمبلغ `{prize:,.0f} میو` به موجودی شما اضافه شد.",
                parse_mode="Markdown"
            )
        else:
            await message.reply(
                f"🎲 تاس‌ها: `{rolls_str} = {total_sum}` ({'زوج' if is_even else 'فرد'})\n"
                f"💥 **باختی!** مبلغ `{amount:,.0f} میو` سوخت شد.",
                parse_mode="Markdown"
            )

        # پاک کردن بازی از لیست فعال‌ها
        del active_dice_games[user_id]


# ==================== ۲. بازی پوپ (پپ‌های استاندارد ۱، ۱، ۲، ۲، ۳) ====================
@router.message(F.text.regexp(r"^(?:#)?پوپ\s+(.+)$"))
async def ask_pop_confirmation(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ بازی پوپ فقط داخل گروه‌ها قابل اجراست!")
        return

    args = message.text.replace("#", "").split()
    try:
        amount = parse_amount(args[1])
    except ValueError:
        await message.reply("⚠️ مبلغ وارد شده معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < amount:
        await message.reply(f"❌ موجودی کافی نیست! موجودی: {balance:,.0f} میو")
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ شروع بازی", callback_data=f"pop_start_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ لغو", callback_data=f"pop_cancel_{user_id}")
        ]
    ])
    await message.reply(f"💩 **بازی پوپ**\nمبلغ: `{amount:,.0f} میو`\nآماده‌ای؟", reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("pop_cancel_"))
async def cancel_pop(callback: CallbackQuery):
    if callback.from_user.id != int(callback.data.split("_")[2]):
        await callback.answer("❌ برای شما نیست!", show_alert=True)
        return
    await callback.message.edit_text("❌ بازی لغو شد.")

@router.callback_query(F.data.startswith("pop_start_"))
async def start_pop(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id = int(parts[2])
    amount = float(parts[3])

    if callback.from_user.id != owner_id:
        await callback.answer("❌ برای شما نیست!", show_alert=True)
        return

    balance = await get_balance(owner_id)
    if balance < amount:
        await callback.message.edit_text("❌ موجودی کافی نیست!")
        return

    await update_balance(owner_id, -amount)

    # ساختار دقیق پپ‌ها برای ۵ ردیف:
    # ردیف ۱: 1 پوپ (3 امن)
    # ردیف ۲: 1 پوپ (3 امن)
    # ردیف ۳: 2 پوپ (2 امن)
    # ردیف ۴: 2 پوپ (2 امن)
    # ردیف ۵: 3 پوپ (1 امن)
    stages_config = [
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 1, 1],
        [0, 0, 1, 1],
        [0, 1, 1, 1]
    ]
    
    stages = []
    for row in stages_config:
        r = row.copy()
        random.shuffle(r)
        stages.append(r)

    active_pop_games[owner_id] = {
        "bet": amount,
        "current_stage": 0,
        "stages": stages,
        "multipliers": [1.2, 1.5, 2.0, 3.0, 4.0],
        "history": ["⚪", "⚪", "⚪", "⚪", "⚪"],
        "revealed_rows": {}
    }
    await render_pop(callback.message, owner_id, is_edit=True)
    await callback.answer("بازی شروع شد!")

async def render_pop(message: Message, user_id: int, is_edit=False):
    game = active_pop_games.get(user_id)
    if not game:
        return
    stage = game["current_stage"]
    bet = game["bet"]
    mults = game["multipliers"]
    curr_mult = mults[stage] if stage < 5 else mults[4]
    curr_prize = bet * mults[stage - 1] if stage > 0 else bet
    pipe_str = "".join(game["history"])

    text = (
        f"💩 **میوبت | پوپ مرحله‌ای**\n\n"
        f"وضعیت: `{pipe_str}`\n"
        f"مرحله {stage + 1} از ۵ | ضریب: `{curr_mult}x`\n"
        f"جایزه فعلی: `{curr_prize:,.0f} میو`"
    )

    keyboard = []
    for r in range(5):
        row_btns = []
        for c in range(4):
            if r in game["revealed_rows"]:
                val = game["revealed_rows"][r][c]
                icon = "💩" if val == 1 else "🟢"
                row_btns.append(InlineKeyboardButton(text=icon, callback_data="pop_passed"))
            elif r == stage:
                row_btns.append(InlineKeyboardButton(text="⚪", callback_data=f"pop_click_{user_id}_{r}_{c}"))
            else:
                row_btns.append(InlineKeyboardButton(text="🔒", callback_data="pop_locked"))
        keyboard.append(row_btns)

    if stage > 0 and stage < 5:
        keyboard.append([InlineKeyboardButton(text=f"💵 برداشت ({curr_prize:,.0f} میو)", callback_data=f"pop_cash_{user_id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if is_edit:
        await message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.reply(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("pop_click_"))
async def click_pop(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id = int(parts[2])
    stg = int(parts[3])
    col = int(parts[4])

    if callback.from_user.id != owner_id:
        await callback.answer("❌ برای شما نیست!", show_alert=True)
        return

    game = active_pop_games.get(owner_id)
    if not game or game["current_stage"] != stg:
        await callback.answer("⚠️ نامعتبر است.", show_alert=True)
        return

    row_data = game["stages"][stg]
    game["revealed_rows"][stg] = row_data
    is_poop = row_data[col] == 1

    if is_poop:
        game["history"][stg] = "💩"
        pipe_str = "".join(game["history"])
        for r in range(5):
            if r not in game["revealed_rows"]:
                game["revealed_rows"][r] = game["stages"][r]

        await render_pop(callback.message, owner_id, is_edit=True)
        await callback.message.answer(f"💥 **باختی!** به پوپ خوردی.\nلوله: `{pipe_str}`", parse_mode="Markdown")
        del active_pop_games[owner_id]
        await callback.answer("باختی!", show_alert=True)
    else:
        game["history"][stg] = "🟢"
        game["current_stage"] += 1
        if game["current_stage"] >= 5:
            prize = game["bet"] * game["multipliers"][4]
            await update_balance(owner_id, prize)
            pipe_str = "".join(game["history"])
            await render_pop(callback.message, owner_id, is_edit=True)
            await callback.message.answer(f"🏆 **برنده نهایی شدی!**\nلوله: `{pipe_str}`\nجایزه: **{prize:,.0f} میو**", parse_mode="Markdown")
            del active_pop_games[owner_id]
            await callback.answer("برنده شدی!", show_alert=True)
        else:
            await callback.answer("امن بود! 🟢", show_alert=False)
            await render_pop(callback.message, owner_id, is_edit=True)

@router.callback_query(F.data.startswith("pop_cash_"))
async def cash_pop(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id:
        await callback.answer("❌ برای شما نیست!", show_alert=True)
        return
    game = active_pop_games.get(owner_id)
    if not game:
        return
    prize = game["bet"] * game["multipliers"][game["current_stage"] - 1]
    await update_balance(owner_id, prize)
    await callback.message.edit_text(f"💵 **برداشت موفق!** مبلغ **{prize:,.0f} میو** واریز شد.", parse_mode="Markdown")
    del active_pop_games[owner_id]
    await callback.answer("برداشت شد!")
