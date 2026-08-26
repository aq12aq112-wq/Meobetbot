import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, update_balance, get_setting, set_setting
from config import ADMIN_IDS

router = Router()

# نگهداری وضعیت بازی‌های فعال پوپ کاربران
# active_games[user_id] = {bet, step, multiplier, grid, user_name, chat_id}
active_games = {}

@router.message(F.text.regexp(r"^(?:#پوپ|پوپ)\s*(.+)"))
async def start_pop_game(message: Message):
    # ذخیره گروه در دیتابیس برای پیام همگانی
    if message.chat.type != "private":
        from database import add_group
        await add_group(message.chat.id)

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("⚠️ لطفاً مبلغ شرط را وارد کنید. مثال: `پوپ 300k` یا `پوپ 10000`", parse_mode="Markdown")
        return

    text = args[1].strip().lower()
    multiplier_val = 1
    if text.endswith('k'): multiplier_val = 1000; text = text[:-1]
    elif text.endswith('m'): multiplier_val = 1000000; text = text[:-1]

    try:
        bet = float(text) * multiplier_val
        if bet <= 0: raise ValueError()
    except ValueError:
        await message.reply("⚠️ مبلغ شرط نامعتبر است.")
        return

    user_id = message.from_user.id
    balance = await get_balance(user_id)
    if balance < bet:
        await message.reply(f"❌ موجودی کافی نیست! موجودی شما: {balance:,.0f} میو")
        return

    # کسر موجودی برای شروع بازی
    await update_balance(user_id, -bet)

    # ساخت شبکه بازی پوپ (5 مرحله، هر مرحله 4 خانه که یکی از آن‌ها بمب/پوپ است)
    grid = []
    for _ in range(5):
        row = [False] * 4
        bomb_idx = random.randint(0, 3)
        row[bomb_idx] = True
        grid.append(row)

    active_games[user_id] = {
        "bet": bet,
        "step": 0, # از مرحله 0 (پایین‌ترین سطح)
        "grid": grid,
        "user_name": message.from_user.first_name,
        "chat_id": message.chat.id
    }

    await send_pop_board(message, user_id, is_new=True)

async def send_pop_board(message_or_callback, user_id: int, is_new=False):
    game = active_games.get(user_id)
    if not game:
        return

    bet = game["bet"]
    step = game["step"]
    
    # ضریب پوپ خوانده شده از دیتابیس (تنظیم‌شده توسط ادمین)
    try:
        custom_mult = float(await get_setting("pop_multiplier"))
    except:
        custom_mult = 1.5

    current_prize = bet * (custom_mult ** step) if step > 0 else bet

    text = (
        f"Meowie bet🐱\n"
        f"🐾 {game['user_name']} \n"
        f"📌 `#پوپ {int(bet)}کی`\n"
        f"🎰 میوبت 2\n\n"
        f"🐾 پوپ — 💩\n"
        f"🎮 مرحله {step + 1} از ۵\n"
        f"💰 شرط: {int(bet):,} میو\n"
        f"📈 جایزه فعلی: {int(current_prize):,} میو"
    )

    # ساخت کیبورد شیشه‌ای پوپ دقیقاً مشابه عکس
    keyboard_rows = []
    
    # ردیف‌های بازی (5 ردیف)
    for r in range(5):
        row_buttons = []
        for c in range(4):
            if r > step:
                # مراحل آینده (قفل)
                row_buttons.append(InlineKeyboardButton(text="🔒", callback_data="pop_noop"))
            elif r < step:
                # مراحل رد شده قبلی
                row_buttons.append(InlineKeyboardButton(text="🟢", callback_data="pop_noop"))
            else:
                # مرحله فعلی (قابل انتخاب 4 ستون)
                row_buttons.append(InlineKeyboardButton(text="⚪", callback_data=f"pop_choose_{r}_{c}"))
        keyboard_rows.append(row_buttons)

    # دکمه برداشت در صورت عبور از حداقل یک مرحله
    if step > 0:
        keyboard_rows.append([InlineKeyboardButton(text=f"💰 برداشت ({int(current_prize):,} میو)", callback_data="pop_cashout")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    if is_new:
        if isinstance(message_or_callback, Message):
            sent = await message_or_callback.reply(text, reply_markup=keyboard)
            game["msg_id"] = sent.message_id
    else:
        if isinstance(message_or_callback, CallbackQuery):
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except Exception:
                pass

@router.callback_query(F.data.startswith("pop_choose_"))
async def cb_pop_choose(callback: CallbackQuery):
    user_id = callback.from_user.id
    game = active_games.get(user_id)
    if not game:
        await callback.answer("بازی فعالی ندارید یا منقضی شده است.", show_alert=True)
        return

    _, _, r_str, c_str = callback.data.split("_")
    chosen_row, chosen_col = int(r_str), int(c_str)

    if chosen_row != game["step"]:
        await callback.answer("این مرحله معتبر نیست!", show_alert=True)
        return

    grid = game["grid"]
    is_bomb = grid[chosen_row][chosen_col]

    if is_bomb:
        # باخت در بازی پوپ
        bet = game["bet"]
        del active_games[user_id]
        
        try:
            await callback.message.edit_text(
                f"Meowie bet🐱\n"
                f"🐾 {game['user_name']} \n"
                f"❌ **پوپ منفجر شد! باختی.**\n"
                f"💸 مبلغ از دست رفته: {int(bet):,} میو",
                parse_mode="Markdown"
            )
        except:
            pass
        await callback.answer("پوپ ترکید! باختی 💥", show_alert=True)
    else:
        # موفقیت در این مرحله و رفتن به مرحله بعد
        game["step"] += 1
        if game["step"] >= 5:
            # برنده شدن کامل در تمام 5 مرحله
            try:
                custom_mult = float(await get_setting("pop_multiplier"))
            except:
                custom_mult = 1.5
            final_prize = game["bet"] * (custom_mult ** 5)
            await update_balance(user_id, final_prize)
            prize_val = final_prize
            user_name = game["user_name"]
            del active_games[user_id]

            await callback.message.edit_text(
                f"Meowie bet🐱\n"
                f"🐾 {user_name} \n"
                f"🎉 **تبریک! تمام مراحل را برنده شدید!**\n"
                f"💰 جایزه دریافتی: {int(prize_val):,} میو",
                parse_mode="Markdown"
            )
            await callback.answer("برنده شدی! تبریک 🎉", show_alert=True)
        else:
            await send_pop_board(callback, user_id, is_new=False)
            await callback.answer("عالی بود! برو مرحله بعد 👍")

@router.callback_query(F.data == "pop_cashout")
async def cb_pop_cashout(callback: CallbackQuery):
    user_id = callback.from_user.id
    game = active_games.get(user_id)
    if not game:
        await callback.answer("بازی فعالی ندارید.", show_alert=True)
        return

    step = game["step"]
    bet = game["bet"]
    try:
        custom_mult = float(await get_setting("pop_multiplier"))
    except:
        custom_mult = 1.5

    prize = bet * (custom_mult ** step)
    await update_balance(user_id, prize)
    user_name = game["user_name"]
    del active_games[user_id]

    try:
        await callback.message.edit_text(
            f"Meowie bet🐱\n"
            f"🐾 {user_name} \n"
            f"💰 **برداشت موفق!**\n"
            f"مبلغ سود به حسابتان واریز شد: {int(prize):,} میو",
            parse_mode="Markdown"
        )
    except:
        pass
    await callback.answer(f"مبلغ {int(prize):,} میو برداشت شد!")

@router.callback_query(F.data == "pop_noop")
async def cb_pop_noop(callback: CallbackQuery):
    await callback.answer("این خانه قابل انتخاب نیست.", show_alert=True)
