import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_balance, update_balance

router = Router()

active_pop_games = {}
active_dice_games = {}
active_mine_games = {}

def parse_amount(val_str: str) -> float:
    """تبدیل مقادیری مثل 20کی یا 50k به عدد واقعی"""
    val_str = val_str.lower().replace("کی", "k").replace(",", "").strip()
    if "k" in val_str:
        num = float(val_str.replace("k", ""))
        return num * 1000
    return float(val_str)

# ==================== 🎮 بازی پوپ (Pop) ====================
@router.message(F.text.regexp(r"^(?:#)?پوپ\s+(.+)$"))
async def start_pop_game(message: Message, state: FSMContext):
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

    await update_balance(user_id, -amount)

    multipliers = [1.2, 1.4, 1.6, 2.0, 2.5]
    stages = []
    for _ in range(5):
        row = [0, 0, 0, 1]
        random.shuffle(row)
        stages.append(row)

    active_pop_games[user_id] = {
        "bet": amount,
        "current_stage": 0,
        "stages": stages,
        "multipliers": multipliers,
        "history": ["⚪", "⚪", "⚪", "⚪", "⚪"]
    }

    await send_pop_board(message, user_id, is_new=True)

async def send_pop_board(event, user_id: int, is_new=False):
    game = active_pop_games.get(user_id)
    if not game:
        return

    stage = game["current_stage"]
    bet = game["bet"]
    multipliers = game["multipliers"]
    
    current_mult = multipliers[stage - 1] if stage > 0 else 1.0
    current_prize = bet * (multipliers[stage - 1]) if stage > 0 else bet
    pipe_str = "".join(game["history"])
    user_name = event.from_user.first_name if hasattr(event, "from_user") else "کاربر"

    text = (
        f"🐱 **میوبت | MEOWBET** 🎰\n\n"
        f"⚡️ کاربر: `{user_name}`\n"
        f" لوله وضعیت: `{pipe_str}`\n\n"
        f"💩 پوپ — مرحله {stage + 1} از ۵ 🎮\n"
        f"💰 شرط: {bet:,.0f} میو\n"
        f"📈 ضریب این مرحله: {current_mult}x\n"
        f"🏆 جایزه فعلی: {current_prize:,.0f} میو"
    )

    keyboard = []
    for r in range(5):
        row_buttons = []
        for c in range(4):
            if r == stage:
                row_buttons.append(InlineKeyboardButton(text="🟢", callback_data=f"pop_click_{user_id}_{r}_{c}"))
            elif r < stage:
                row_buttons.append(InlineKeyboardButton(text="✅", callback_data="pop_passed"))
            else:
                row_buttons.append(InlineKeyboardButton(text="🔒", callback_data="pop_locked"))
        keyboard.append(row_buttons)

    if stage > 0:
        keyboard.append([InlineKeyboardButton(text=f"💵 برداشت جایزه ({current_prize:,.0f} میو)", callback_data=f"pop_cashout_{user_id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if is_new:
        if isinstance(event, Message):
            await event.reply(text, reply_markup=markup, parse_mode="Markdown")
    else:
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            except:
                pass

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
    is_poop = game["stages"][stage][clicked_col] == 1

    if is_poop:
        game["history"][stage] = "💩"
        pipe_str = "".join(game["history"])
        text = f"💥 **باختی داداش!**\nمرحله {stage + 1} به پوپ خوردی 💩\nمبلغ {game['bet']:,.0f} میو سوخت شد!"
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
            text = f"🏆 **ترکوندی!**\nکل ۵ مرحله رد شد!\n💰 جایزه: **{final_prize:,.0f} میو**"
            await callback.message.edit_text(text, parse_mode="Markdown")
            del active_pop_games[owner_id]
            await callback.answer("🎉 برنده شدی!", show_alert=True)
        else:
            await callback.answer("عالی بود!", show_alert=False)
            await send_pop_board(callback, owner_id)

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
    await callback.message.edit_text(f"💵 **برداشت موفق!**\nمبلغ **{prize:,.0f} میو** واریز شد.", parse_mode="Markdown")
    del active_pop_games[owner_id]
    await callback.answer("💵 واریز شد!", show_alert=True)

@router.callback_query(F.data == "pop_locked")
async def cb_pop_locked(callback: CallbackQuery):
    await callback.answer("🔒 قفل است!", show_alert=True)

@router.callback_query(F.data == "pop_passed")
async def cb_pop_passed(callback: CallbackQuery):
    await callback.answer("✅ رد شده!", show_alert=True)


# ==================== 🎲 بازی تاس (Dice) ====================
@router.message(F.text.regexp(r"^(زوج|فرد)\s+(.+)$"))
async def start_dice_game(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ بازی تاس فقط داخل گروه‌ها قابل اجراست!")
        return

    text_parts = message.text.split()
    choice_fa = text_parts[0]
    try:
        amount = parse_amount(text_parts[1])
    except ValueError:
        await message.reply("⚠️ مبلغ وارد شده معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)

    if balance < amount:
        await message.reply(f"❌ موجودی شما کافی نیست!\nموجودی فعلی: {balance:,.0f} میو")
        return

    await update_balance(user_id, -amount)
    choice = "even" if choice_fa == "زوج" else "odd"

    active_dice_games[user_id] = {
        "bet": amount,
        "choice": choice,
        "rolls": []
    }

    mention = f"<a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>"
    text = (
        f"🎲 **بازی تاس میوبت**\n\n"
        f"کاربر {mention} روی **{choice_fa}** مبلغ `{amount:,.0f} میو` شرط بست.\n\n"
        f"👇 لطفاً پشت سر هم **۳ عدد تاس** 🎲 داخل گروه بفرستید!"
    )
    await message.reply(text, parse_mode="HTML")

@router.message(F.dice)
async def handle_dice_throw(message: Message):
    if message.chat.type == "private":
        return

    user_id = message.from_user.id
    game = active_dice_games.get(user_id)
    if not game or message.dice.emoji != "🎲":
        return

    dice_value = message.dice.value
    game["rolls"].append(dice_value)
    rolls_count = len(game["rolls"])
    mention = f"<a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>"

    if rolls_count < 3:
        await message.reply(f"🎲 تاس {rolls_count} ثبت شد ({3 - rolls_count} تاس دیگر مانده) {mention}!", parse_mode="HTML")
    else:
        total_sum = sum(game["rolls"])
        is_even = total_sum % 2 == 0
        user_choice = game["choice"]
        won = (user_choice == "even" and is_even) or (user_choice == "odd" and not is_even)
        
        rolls_str = " + ".join(map(str, game["rolls"]))
        sum_type = "زوج 🟢" if is_even else "فرد 🔴"

        if won:
            prize = game["bet"] * 1.5
            await update_balance(user_id, prize)
            result_text = f"🎉 **برنده شدی!**\nتاس‌ها: `({rolls_str}) = {total_sum}` ({sum_type})\n🎁 جایزه: **{prize:,.0f} میو**"
        else:
            result_text = f"💥 **باختی!**\nتاس‌ها: `({rolls_str}) = {total_sum}` ({sum_type})\nمبلغ `{game['bet']:,.0f} میو` سوخت شد."

        del active_dice_games[user_id]
        await message.reply(result_text, parse_mode="HTML")


# ==================== 💣 بازی مین (Mine) ====================
@router.message(F.text.regexp(r"^(?:#)?مین\s+(.+)$"))
async def start_mine_game(message: Message):
    if message.chat.type == "private":
        await message.reply("❌ بازی مین فقط داخل گروه‌ها قابل اجراست!")
        return

    args = message.text.replace("#", "").split()
    try:
        amount = parse_amount(args[1])
    except ValueError:
        await message.reply("⚠️ مبلغ معتبر نیست.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < amount:
        await message.reply(f"❌ موجودی کافی نیست! موجودی: {balance:,.0f} میو")
        return

    await update_balance(user_id, -amount)
    mine_pos = random.randint(0, 8)
    board = [0] * 9
    board[mine_pos] = 1

    active_mine_games[user_id] = {
        "bet": amount,
        "board": board,
        "revealed": [False] * 9,
        "score": 0
    }
    await send_mine_board(message, user_id, is_new=True)

async def send_mine_board(event, user_id: int, is_new=False):
    game = active_mine_games.get(user_id)
    if not game:
        return
    bet = game["bet"]
    revealed = game["revealed"]
    user_name = event.from_user.first_name if hasattr(event, "from_user") else "کاربر"

    text = f"💣 **بازی مین**\n👤 کاربر: `{user_name}`\n💰 شرط: `{bet:,.0f} میو`\n\nیک خانه انتخاب کنید:"
    keyboard = []
    for r in range(3):
        row_btns = []
        for c in range(3):
            idx = r * 3 + c
            if revealed[idx]:
                row_btns.append(InlineKeyboardButton(text="💎", callback_data="mine_noop"))
            else:
                row_btns.append(InlineKeyboardButton(text="🟩", callback_data=f"mine_click_{user_id}_{idx}"))
        keyboard.append(row_btns)

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if is_new and isinstance(event, Message):
        await event.reply(text, reply_markup=markup, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
        except:
            pass

@router.callback_query(F.data.startswith("mine_click_"))
async def process_mine_click(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id = int(parts[2])
    idx = int(parts[3])

    if callback.from_user.id != owner_id:
        await callback.answer("❌ برای شما نیست!", show_alert=True)
        return

    game = active_mine_games.get(owner_id)
    if not game or game["revealed"][idx]:
        await callback.answer("⚠️ نامعتبر.", show_alert=True)
        return

    if game["board"][idx] == 1:
        await callback.message.edit_text(f"💥 **بمب منفجر شد!**\nمبلغ `{game['bet']:,.0f} میو` سوخت شد.", parse_mode="Markdown")
        del active_mine_games[owner_id]
        await callback.answer("💥 باختی!", show_alert=True)
    else:
        game["revealed"][idx] = True
        game["score"] += 1
        if game["score"] >= 3:
            prize = game["bet"] * 1.8
            await update_balance(owner_id, prize)
            await callback.message.edit_text(f"🎉 **برنده شدی!**\nمبلغ **{prize:,.0f} میو** واریز شد.", parse_mode="Markdown")
            del active_mine_games[owner_id]
            await callback.answer("🎉 برنده!", show_alert=True)
        else:
            await callback.answer("💎 امن بود!", show_alert=False)
            await send_mine_board(callback, owner_id)

@router.callback_query(F.data == "mine_noop")
async def cb_mine_noop(callback: CallbackQuery):
    await callback.answer("⚠️ قبلاً باز شده!", show_alert=True)
