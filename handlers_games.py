import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, update_balance, get_setting

router = Router()
active_pop_games = {}
active_dice_games = {}
active_rps_games = {}
active_bj_games = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        num = float(val_str.replace("k", ""))
        return num * 1000
    return float(val_str)

# ==================== 💩 بازی پوپ ====================
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
            InlineKeyboardButton(text="❌ لغو بازی", callback_data=f"pop_cancel_{user_id}")
        ]
    ])
    await message.reply(f"🎰 **تایید بازی پوپ**\nمبلغ: `{amount:,.0f} میو`\nآیا مطمئن هستید؟", reply_markup=markup, parse_mode="Markdown")

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

    # ساخت ۵ مرحله، هر کدام ۱ پوپ (1) و ۳ امن (0)
    stages = []
    for _ in range(5):
        row = [0, 0, 0, 1]
        random.shuffle(row)
        stages.append(row)

    active_pop_games[owner_id] = {
        "bet": amount,
        "current_stage": 0,
        "stages": stages,
        "multipliers": [1.2, 1.5, 2.0, 3.0, 4.0],
        "history": ["⚪", "⚪", "⚪", "⚪", "⚪"]
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
        f"「 🎰 **میوبت | پوپ** 」\n\n"
        f"لوله وضعیت: `{pipe_str}`\n"
        f"💩 مرحله {stage + 1} از ۵\n"
        f"💰 شرط: `{bet:,.0f} میو` | ضریب: `{curr_mult}x`\n"
        f"🏆 جایزه فعلی: `{curr_prize:,.0f} میو`"
    )

    keyboard = []
    for r in range(5):
        row_btns = []
        for c in range(4):
            if r == stage:
                row_btns.append(InlineKeyboardButton(text="⚪", callback_data=f"pop_click_{user_id}_{r}_{c}"))
            elif r < stage:
                row_btns.append(InlineKeyboardButton(text="✅", callback_data="pop_passed"))
            else:
                row_btns.append(InlineKeyboardButton(text="🔒", callback_data="pop_locked"))
        keyboard.append(row_btns)

    if stage > 0:
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

    is_poop = game["stages"][stg][col] == 1
    if is_poop:
        game["history"][stg] = "💩"
        pipe_str = "".join(game["history"])
        await callback.message.edit_text(f"💥 **باختی!**\nلوله: `{pipe_str}`\nمبلغ `{game['bet']:,.0f} میو` سوخت شد.", parse_mode="Markdown")
        del active_pop_games[owner_id]
        await callback.answer("باختی!", show_alert=True)
    else:
        game["history"][stg] = "🟢"
        game["current_stage"] += 1
        if game["current_stage"] >= 5:
            prize = game["bet"] * game["multipliers"][4]
            await update_balance(owner_id, prize)
            pipe_str = "".join(game["history"])
            await callback.message.edit_text(f"🏆 **برنده شدی!**\nلوله: `{pipe_str}`\nجایزه: **{prize:,.0f} میو**", parse_mode="Markdown")
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
    await callback.message.edit_text(f"💵 **برداشت موفق!**\nمبلغ **{prize:,.0f} میو** واریز شد.", parse_mode="Markdown")
    del active_pop_games[owner_id]
    await callback.answer("برداشت شد!")


# ==================== ✌️ بازی سنگ کاغذ قیچی ====================
@router.message(F.text.regexp(r"^#(سنگ|کاغذ|قیچی)\s+(.+)$"))
async def play_rps(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ بازی سنگ کاغذ قیچی فقط در گروه قابل اجراست!")
        return

    text_parts = message.text.replace("#", "").split()
    user_choice = text_parts[0]
    try:
        amount = parse_amount(text_parts[1])
    except ValueError:
        await message.reply("⚠️ مبلغ معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < amount:
        await message.reply(f"❌ موجودی کافی نیست! موجودی: {balance:,.0f} میو")
        return

    await update_balance(user_id, -amount)
    
    # انتخاب ربات
    choices = {"سنگ": "قیچی", "کاغذ": "سنگ", "قیچی": "کاغذ"}
    bot_choice = random.choice(list(choices.keys()))

    if user_choice == bot_choice:
        await update_balance(user_id, amount) # برگشت پول
        res = "🤝 **مساوی!** پولت برگشت خورد."
    elif choices[user_choice] == bot_choice:
        prize = amount * 1.9 # ضریب قابل تنظیم
        await update_balance(user_id, prize)
        res = f"🎉 **برنده شدی!** ربات `{bot_choice}` آورد.\nجایزه: **{prize:,.0f} میو**"
    else:
        res = f"💥 **باختی!** ربات `{bot_choice}` آورد.\nمبلغ `{amount:,.0f} میو` سوخت شد."

    await message.reply(f"✌️ **سنگ کاغذ قیچی**\nانتخاب شما: `{user_choice}`\n\n{res}", parse_mode="Markdown")


# ==================== 🃏 بازی بلک‌جک (21) ====================
@router.message(F.text.regexp(r"^#بلکجک\s+(.+)$"))
async def play_blackjack(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ بازی بلک‌جک فقط در گروه قابل اجراست!")
        return

    try:
        amount = parse_amount(message.text.replace("#بلکجک", "").strip())
    except ValueError:
        await message.reply("⚠️ مبلغ معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < amount:
        await message.reply(f"❌ موجودی کافی نیست!")
        return

    await update_balance(user_id, -amount)
    
    player_card = random.randint(2, 11)
    bot_card = random.randint(5, 11)

    if player_card > bot_card:
        prize = amount * 2.0
        await update_balance(user_id, prize)
        await message.reply(f"🃏 **بلک‌جک**\nکارت شما: `{player_card}` | کارت ربات: `{bot_card}`\n🎉 **برنده شدی!** جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")
    elif player_card == bot_card:
        await update_balance(user_id, amount)
        await message.reply(f"🃏 **بلک‌جک**\nمساوی شد! کارت‌ها: `{player_card}`. پولت برگشت.", parse_mode="Markdown")
    else:
        await message.reply(f"🃏 **بلک‌جک**\nکارت شما: `{player_card}` | کارت ربات: `{bot_card}`\n💥 **باختی!**", parse_mode="Markdown")
