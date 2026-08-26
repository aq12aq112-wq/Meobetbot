import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, update_balance

router = Router()
active_pop_games = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace(",", "").strip()
    if "k" in val_str:
        num = float(val_str.replace("k", ""))
        return num * 1000
    return float(val_str)

# ۱. مرحله اول: دستور پوپ -> ارسال پیام تایید مبلغ و شروع بازی
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
        await message.reply(f"❌ موجودی شما کافی نیست!\nموجودی فعلی: {balance:,.0f} میو")
        return

    # ارسال پیام تایید شروع بازی
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ شروع بازی", callback_data=f"pop_start_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ لغو بازی", callback_data=f"pop_cancel_{user_id}")
        ]
    ])

    await message.reply(
        f"🎰 **تایید شروع بازی پوپ**\n\n"
        f"👤 کاربر: {message.from_user.first_name}\n"
        f"💰 مبلغ شرط: `{amount:,.0f} میو`\n\n"
        f"آیا از شروع بازی اطمینان دارید؟",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ۲. دکمه لغو بازی
@router.callback_query(F.data.startswith("pop_cancel_"))
async def cancel_pop_game(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id:
        await callback.answer("❌ این بازی شما نیست!", show_alert=True)
        return
    await callback.message.edit_text("❌ بازی پوپ لغو شد.")
    await callback.answer("بازی لغو شد.")

# ۳. دکمه تایید و شروع واقعی بازی
@router.callback_query(F.data.startswith("pop_start_"))
async def confirm_and_start_pop(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    owner_id = int(data_parts[2])
    amount = float(data_parts[3])

    if callback.from_user.id != owner_id:
        await callback.answer("❌ این دکمه برای شما نیست!", show_alert=True)
        return

    balance = await get_balance(owner_id)
    if balance < amount:
        await callback.message.edit_text("❌ موجودی شما برای شروع بازی کافی نیست!")
        await callback.answer("موجودی کافی نیست!", show_alert=True)
        return

    # کم کردن مبلغ از حساب کاربر
    await update_balance(owner_id, -amount)

    # ساخت مرحله‌ها (۵ ردیف، هر ردیف ۴ خانه که در هر ردیف دقیقاً ۱ پوپ [عدد ۱] و ۳ خانه امن [عدد ۰] وجود دارد)
    stages = []
    for _ in range(5):
        row = [0, 0, 0, 1]
        random.shuffle(row)
        stages.append(row)

    multipliers = [1.2, 1.4, 1.6, 2.0, 2.5]

    active_pop_games[owner_id] = {
        "bet": amount,
        "current_stage": 0,
        "stages": stages,
        "multipliers": multipliers,
        "history": ["⚪", "⚪", "⚪", "⚪", "⚪"]
    }

    await render_pop_board(callback.message, owner_id, is_edit=True)
    await callback.answer("بازی شروع شد! موفق باشی 🍀")

async def render_pop_board(message: Message, user_id: int, is_edit=False):
    game = active_pop_games.get(user_id)
    if not game:
        return

    stage = game["current_stage"]
    bet = game["bet"]
    multipliers = game["multipliers"]
    
    current_mult = multipliers[stage - 1] if stage > 0 else 1.0
    current_prize = bet * multipliers[stage - 1] if stage > 0 else bet
    pipe_str = "".join(game["history"])

    text = (
        f"🐱 **میوبت | MEOWBET** 🎰\n\n"
        f" لوله وضعیت: `{pipe_str}`\n\n"
        f"💩 پوپ — مرحله {stage + 1} از ۵ 🎮\n"
        f"💰 شرط: {bet:,.0f} میو\n"
        f"📈 ضریب این مرحله: {multipliers[stage]}x\n"
        f"🏆 جایزه فعلی: {current_prize:,.0f} میو"
    )

    keyboard = []
    for r in range(5):
        row_buttons = []
        for c in range(4):
            if r == stage:
                # ردیف فعال برای کلیک (پنهان و استاندارد)
                row_buttons.append(InlineKeyboardButton(text="❓", callback_data=f"pop_click_{user_id}_{r}_{c}"))
            elif r < stage:
                row_buttons.append(InlineKeyboardButton(text="✅", callback_data="pop_passed"))
            else:
                row_buttons.append(InlineKeyboardButton(text="🔒", callback_data="pop_locked"))
        keyboard.append(row_buttons)

    if stage > 0:
        keyboard.append([InlineKeyboardButton(text=f"💵 برداشت جایزه ({current_prize:,.0f} میو)", callback_data=f"pop_cashout_{user_id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if is_edit:
        try:
            await message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
        except:
            pass
    else:
        await message.reply(text, reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("pop_click_"))
async def process_pop_click(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    owner_id = int(data_parts[2])
    clicked_stage = int(data_parts[3])
    clicked_col = int(data_parts[4])

    if callback.from_user.id != owner_id:
        await callback.answer("❌ این بازی شما نیست!", show_alert=True)
        return

    game = active_pop_games.get(owner_id)
    if not game or game["current_stage"] != clicked_stage:
        await callback.answer("⚠️ این مرحله نامعتبر است.", show_alert=True)
        return

    stage = game["current_stage"]
    # بررسی اینکه آیا خانه‌ای که کاربر زده پوپ (1) است یا امن (0)
    is_poop = game["stages"][stage][clicked_col] == 1

    if is_poop:
        game["history"][stage] = "💩"
        pipe_str = "".join(game["history"])
        text = (
            f"💥 **باختی داداش!**\n"
            f"لوله: `{pipe_str}`\n"
            f"مرحله {stage + 1} به پوپ خوردی 💩\n"
            f"مبلغ `{game['bet']:,.0f} میو` سوخت شد!"
        )
        await callback.message.edit_text(text, parse_mode="Markdown")
        del active_pop_games[owner_id]
        await callback.answer("💥 باختی!", show_alert=True)
    else:
        game["history"][stage] = "🟢"
        game["current_stage"] += 1

        if game["current_stage"] >= 5:
            final_prize = game["bet"] * game["multipliers"][4]
            await update_balance(owner_id, final_prize)
            pipe_str = "".join(game["history"])
            text = (
                f"🏆 **ترکوندی و برنده شدی!**\n"
                f"لوله: `{pipe_str}`\n"
                f"کل ۵ مرحله با موفقیت رد شد!\n"
                f"💰 جایزه نهایی: **{final_prize:,.0f} میو**"
            )
            await callback.message.edit_text(text, parse_mode="Markdown")
            del active_pop_games[owner_id]
            await callback.answer("🎉 برنده شدی!", show_alert=True)
        else:
            await callback.answer("عالی بود! خانه امن بود 🟢", show_alert=False)
            await render_pop_board(callback.message, owner_id, is_edit=True)

@router.callback_query(F.data.startswith("pop_cashout_"))
async def process_pop_cashout(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id:
        await callback.answer("❌ برای شما نیست!", show_alert=True)
        return
    game = active_pop_games.get(owner_id)
    if not game:
        await callback.answer("⚠️ منقضی شده.", show_alert=True)
        return
    stage = game["current_stage"]
    prize = game["bet"] * game["multipliers"][stage - 1]
    await update_balance(owner_id, prize)
    await callback.message.edit_text(f"💵 **برداشت موفق جایزه!**\nمبلغ **{prize:,.0f} میو** به حسابت واریز شد.", parse_mode="Markdown")
    del active_pop_games[owner_id]
    await callback.answer("💵 پول واریز شد!", show_alert=True)

@router.callback_query(F.data == "pop_locked")
async def cb_pop_locked(callback: CallbackQuery):
    await callback.answer("🔒 این مرحله قفل است!", show_alert=True)

@router.callback_query(F.data == "pop_passed")
async def cb_pop_passed(callback: CallbackQuery):
    await callback.answer("✅ این مرحله با موفقیت رد شده است.", show_alert=True)
