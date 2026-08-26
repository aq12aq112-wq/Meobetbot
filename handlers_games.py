import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_balance, update_balance

router = Router()

# کمکی برای تبدیل مبلغ ورودی مثل 50k
def parse_amount(text: str) -> float:
    text = text.strip().lower()
    multiplier = 1
    if text.endswith('k'):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith('m'):
        multiplier = 1000000
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return 0.0

# ---------------- بازی پوپ (Poop) ----------------
# ذخیره موقت بازی‌های فعال پوپ
active_poop_games = {}

@router.message(F.text.regexp(r"^پوپ\s+(.+)"))
async def start_poop_game(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ لطفاً مبلغ بازی را وارد کنید. مثال: `پوپ 50k`", parse_mode="Markdown")
        return
        
    amount = parse_amount(args[1])
    if amount <= 0:
        await message.answer("⚠️ مبلغ نامعتبر است.")
        return
        
    user_balance = await get_balance(message.from_user.id)
    if user_balance < amount:
        await message.answer(f"❌ موجودی شما کافی نیست!\nموجودی فعلی: {user_balance:,.0f} تومان", parse_mode="Markdown")
        return
        
    # کسر مبلغ از کاربر به عنوان شروع بازی
    await update_balance(message.from_user.id, -amount)
    
    # ساخت مراحل بازی پوپ (۵ مرحله، هر مرحله ۳ خانه که یکی پوچ/💩 است)
    game_id = f"{message.from_user.id}_{message.date.timestamp()}"
    active_poop_games[game_id] = {
        "user_id": message.from_user.id,
        "amount": amount,
        "step": 0,
        "multiplier": 1.2
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 خانه ۱", callback_data=f"poop_{game_id}_0"),
            InlineKeyboardButton(text="💎 خانه ۲", callback_data=f"poop_{game_id}_1"),
            InlineKeyboardButton(text="💎 خانه ۳", callback_data=f"poop_{game_id}_2"),
        ],
        [InlineKeyboardButton(text="💰 برداشت جایزه و اتمام", callback_data=f"poop_cash_{game_id}")]
    ])
    
    await message.answer(
        f"💩 **بازی پوپ (Poop)**\n\n"
        f"مبلغ ورود: **{amount:,.0f} تومان**\n"
        f"مرحله: **۱ از ۵** | ضریب فعلی: **1.2x**\n\n"
        "یک خانه را انتخاب کنید تا الماس بگیرید و از پوپ دوری کنید!",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("poop_") & ~F.data.startswith("poop_cash_"))
async def process_poop_step(callback: CallbackQuery):
    parts = callback.data.split("_")
    game_id = f"{parts[1]}_{parts[2]}"
    choice = int(parts[3])
    
    game = active_poop_games.get(game_id)
    if not game or game["user_id"] != callback.from_user.id:
        await callback.answer("این بازی منقضی شده یا متعلق به شما نیست.", show_alert=True)
        return
        
    # تعیین تصادفی جایگاه پوپ (0 تا 2)
    poop_index = random.randint(0, 2)
    
    if choice == poop_index:
        # باخت
        del active_poop_games[game_id]
        await callback.message.edit_text(
            f"💩 **باختید!**\nبه پوپ خوردید!\nمبلغ {game['amount']:,.0f} تومان از دست رفت.",
            parse_mode="Markdown"
        )
        await callback.answer("متأسفانه باختید!", show_alert=True)
    else:
        # برد در این مرحله و رفتن به مرحله بعد
        game["step"] += 1
        game["multiplier"] = round(game["multiplier"] * 1.5, 2)
        
        if game["step"] >= 5:
            # برد نهایی
            win_amount = game["amount"] * game["multiplier"]
            await update_balance(callback.from_user.id, win_amount)
            del active_poop_games[game_id]
            await callback.message.edit_text(
                f"🎉 تبریک! شما تمام ۵ مرحله را با موفقیت رد کردید!\n"
                f"💎 جایزه شما: **{win_amount:,.0f} تومان** به حساب اضافه شد.",
                parse_mode="Markdown"
            )
            await callback.answer("تبریک! برنده شدید!")
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💎 خانه ۱", callback_data=f"poop_{game_id}_0"),
                    InlineKeyboardButton(text="💎 خانه ۲", callback_data=f"poop_{game_id}_1"),
                    InlineKeyboardButton(text="💎 خانه ۳", callback_data=f"poop_{game_id}_2"),
                ],
                [InlineKeyboardButton(text=f"💰 برداشت ({game['amount'] * game['multiplier']:,.0f} ت)", callback_data=f"poop_cash_{game_id}")]
            ])
            await callback.message.edit_text(
                f"💩 **بازی پوپ (Poop)** - مرحله {game['step'] + 1}\n\n"
                f"ضریب فعلی: **{game['multiplier']}x**\n"
                "انتخاب بعدی خود را انجام دهید:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer("آفرین! الماس نصیبت شد.")

@router.callback_query(F.data.startswith("poop_cash_"))
async def process_poop_cashout(callback: CallbackQuery):
    game_id = callback.data.replace("poop_cash_", "")
    game = active_poop_games.get(game_id)
    if not game or game["user_id"] != callback.from_user.id:
        await callback.answer("بازی یافت نشد.", show_alert=True)
        return
        
    win_amount = game["amount"] * game["multiplier"]
    await update_balance(callback.from_user.id, win_amount)
    del active_poop_games[game_id]
    
    await callback.message.edit_text(
        f"💰 **برداشت موفق!**\n\n"
        f"مبلغ **{win_amount:,.0f} تومان** به موجودی شما اضافه شد.",
        parse_mode="Markdown"
    )
    await callback.answer("برداشت با موفقیت انجام شد.")

# ---------------- بازی تاس (Dice) ----------------
@router.message(F.text.regexp(r"^تاس\s+(.+)"))
async def play_dice(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ لطفاً مبلغ را وارد کنید. مثال: `تاس 20k`", parse_mode="Markdown")
        return
        
    amount = parse_amount(args[1])
    if amount <= 0:
        await message.answer("⚠️ مبلغ نامعتبر است.")
        return
        
    user_balance = await get_balance(message.from_user.id)
    if user_balance < amount:
        await message.answer(f"❌ موجودی کافی نیست!\nموجودی فعلی: {user_balance:,.0f} تومان", parse_mode="Markdown")
        return
        
    await update_balance(message.from_user.id, -amount)
    
    # ارسال تاس تلگرام
    dice_msg = await message.answer_dice(emoji="🎲")
    # صبر کوتاه برای نشستن تاس
    import asyncio
    await asyncio.sleep(4)
    
    dice_value = dice_msg.dice.value
    if dice_value >= 4:
        win_amount = amount * 2
        await update_balance(message.from_user.id, win_amount)
        await message.answer(f"🎲 عدد تاس: {dice_value}\n🎉 **برنده شدید!** مبلغ {win_amount:,.0f} تومان به شما تعلق گرفت.", parse_mode="Markdown")
    else:
        await message.answer(f"🎲 عدد تاس: {dice_value}\n😢 **باختید!** مبلغ {amount:,.0f} تومان کسر شد.", parse_mode="Markdown")

# ---------------- بازی مین و الماس (Mines) ----------------
@router.message(F.text.regexp(r"^مین\s+(.+)"))
async def play_mines(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ مثال استفاده: `مین 50k`", parse_mode="Markdown")
        return
        
    amount = parse_amount(args[1])
    if amount <= 0:
        await message.answer("⚠️ مبلغ نامعتبر.")
        return
        
    user_balance = await get_balance(message.from_user.id)
    if user_balance < amount:
        await message.answer("❌ موجودی کافی نیست!")
        return
        
    await update_balance(message.from_user.id, -amount)
    
    # شبیه‌سازی ساده برد/باخت مینی گیم مین
    is_win = random.choice([True, False])
    if is_win:
        win_amount = amount * 2.2
        await update_balance(message.from_user.id, win_amount)
        await message.answer(f"💎 **موفقیت!** خانه امن را انتخاب کردید.\nپاداش: **{win_amount:,.0f} تومان**", parse_mode="Markdown")
    else:
        await message.answer(f"💣 **بوم!** روی مین رفتید و مبلغ {amount:,.0f} تومان را از دست دادید.", parse_mode="Markdown")
