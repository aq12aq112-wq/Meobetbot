import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# تنظیمات پایه
BOT_TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"
ADMIN_CARD = "760188800770"
ADMIN_ID = 6937799221

MIN_LIMIT = 50000
MIN_BET = 20000

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
active_charge_states = {}
active_withdraw_states = {}
active_dice_games = {}
active_pop_games = {}

def parse_amount(val_str: str) -> float:
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        return float(val_str.replace("k", "")) * 1000
    return float(val_str)

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 حساب کاربری و موجودی", callback_data="menu_profile")],
        [
            InlineKeyboardButton(text="💳 شارژ حساب", callback_data="menu_charge"),
            InlineKeyboardButton(text="💵 برداشت وجه", callback_data="menu_withdraw")
        ],
        [InlineKeyboardButton(text="📖 راهنمای بازی‌ها", callback_data="menu_help")]
    ])

@router.message(F.text.in_({"/start", "استارت", "منو"}))
async def cmd_start(message: Message):
    await message.reply(
        "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت شرط ببندی!",
        reply_markup=get_main_menu(), parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("menu_"))
async def handle_menu(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    user_id = callback.from_user.id

    if action == "profile":
        bal = await get_balance(user_id)
        text = f"👤 **حساب کاربری:**\n🆔 آیدی: `{user_id}`\n💳 موجودی: `{bal:,.0f} میو`"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_back")]])
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    elif action == "charge":
        active_charge_states[user_id] = "awaiting_amount"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ لغو", callback_data="menu_back")]])
        await callback.message.edit_text(
            f"💰 **شارژ موجودی**\n\nحداقل مبلغ شارژ `{MIN_LIMIT:,.0f} میو` است.\nمبلغ مورد نظر را ارسال کنید:",
            reply_markup=markup, parse_mode="Markdown"
        )

    elif action == "withdraw":
        active_withdraw_states[user_id] = {"step": "awaiting_card"}
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ لغو", callback_data="menu_back")]])
        await callback.message.edit_text(
            "💵 **برداشت وجه**\n\nابتدا **شماره کارت** بانکی خود را ارسال کنید:",
            reply_markup=markup, parse_mode="Markdown"
        )

    elif action == "help":
        text = (
            "📖 **راهنمای بازی‌ها:**\n\n"
            "• تاس: `#زوج [مبلغ]` یا `#فرد [مبلغ]` (حداقل مبلغ 20,000)\n"
            "• پوپ: `#پوپ [مبلغ]` (حداقل مبلغ 20,000)\n"
            "• حداقل شارژ و برداشت: ۵۰,۰۰۰ میو"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu_back")]])
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    elif action == "back":
        await callback.message.edit_text(
            "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت شرط ببندی!",
            reply_markup=get_main_menu(), parse_mode="Markdown"
        )
    await callback.answer()

@router.message(F.text & ~F.text.startswith("#"))
async def handle_text_inputs(message: Message):
    user_id = message.from_user.id
    
    if user_id in active_charge_states:
        state = active_charge_states[user_id]
        if state == "awaiting_amount":
            try:
                amount = parse_amount(message.text)
            except ValueError:
                return await message.reply("⚠️ مبلغ نامعتبر است.")
            
            if amount < MIN_LIMIT:
                return await message.reply(f"❌ حداقل مبلغ شارژ {MIN_LIMIT:,.0f} میو است.")
            
            active_charge_states[user_id] = {"step": "awaiting_receipt", "amount": amount}
            await message.reply(
                f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
                f"💳 **به کارت زیر واریز کنید:**\n`{ADMIN_CARD}`\n\n"
                f"💰 مبلغ: `{amount:,.0f} میو`\n\n"
                f"📸 بعد از واریز، رسید رو همینجا بفرست.",
                parse_mode="Markdown"
            )
            return

    if user_id in active_withdraw_states:
        data = active_withdraw_states[user_id]
        if data["step"] == "awaiting_card":
            card_num = message.text.strip()
            active_withdraw_states[user_id] = {"step": "awaiting_amount", "card": card_num}
            await message.reply("💵 مبلغ مورد نظر برای برداشت را وارد کنید (حداقل ۵۰,۰۰۰ میو):", parse_mode="Markdown")
            return
        elif data["step"] == "awaiting_amount":
            try:
                amount = parse_amount(message.text)
            except ValueError:
                return await message.reply("⚠️ مبلغ نامعتبر است.")
            
            if amount < MIN_LIMIT:
                return await message.reply(f"❌ حداقل مبلغ برداشت {MIN_LIMIT:,.0f} میو است.")
            
            bal = await get_balance(user_id)
            if bal < amount:
                return await message.reply(f"❌ موجودی شما کافی نیست! موجودی: {bal:,.0f} میو")
            
            card = data["card"]
            del active_withdraw_states[user_id]
            
            admin_markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ تأیید برداشت", callback_data=f"adm_w_acc_{user_id}_{int(amount)}"),
                    InlineKeyboardButton(text="❌ رد برداشت", callback_data=f"adm_w_rej_{user_id}")
                ]
            ])
            await message.reply("⏳ درخواست برداشت شما ثبت شد و در صف بررسی مدیر قرار گرفت.", parse_mode="Markdown")
            try:
                await message.bot.send_message(
                    ADMIN_ID,
                    f"📤 **درخواست برداشت جدید:**\n👤 کاربر: `{user_id}`\n💳 کارت: `{card}`\n💰 مبلغ: `{amount:,.0f} میو`",
                    reply_markup=admin_markup, parse_mode="Markdown"
                )
            except Exception:
                pass
            return

@router.message(F.photo)
async def handle_receipt_photo(message: Message):
    user_id = message.from_user.id
    if user_id in active_charge_states and isinstance(active_charge_states[user_id], dict):
        data = active_charge_states[user_id]
        amount = data["amount"]
        del active_charge_states[user_id]

        admin_markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأیید شارژ", callback_data=f"adm_c_acc_{user_id}_{int(amount)}"),
                InlineKeyboardButton(text="❌ رد رسید", callback_data=f"adm_c_rej_{user_id}")
            ]
        ])
        await message.reply("⏳ درخواست شارژ شما ثبت شد و در صف بررسی قرار گرفت.", parse_mode="Markdown")
        try:
            await message.bot.send_photo(
                ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=f"📥 **رسید شارژ جدید:**\n👤 کاربر: `{user_id}`\n💰 مبلغ: `{amount:,.0f} میو`",
                reply_markup=admin_markup, parse_mode="Markdown"
            )
        except Exception:
            pass

@router.callback_query(F.data.startswith("adm_"))
async def admin_decision(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ دسترسی ندارید!", show_alert=True)
    
    parts = callback.data.split("_")
    action_type = parts[1]
    status = parts[2]
    target_user_id = int(parts[3])

    if action_type == "c":
        if status == "acc":
            amount = float(parts[4])
            await update_balance(target_user_id, amount)
            await callback.message.edit_caption(caption=f"✅ شارژ تأیید شد.\n💰 `{amount:,.0f} میو` واریز شد.")
            try:
                await callback.bot.send_message(target_user_id, f"✅ پرداخت شما تأیید شد.\n💰 مبلغ `{amount:,.0f} میو` به موجودی اضافه شد.", parse_mode="Markdown")
            except Exception:
                pass
        else:
            await callback.message.edit_caption(caption="❌ رسید شارژ رد شد.")
            try:
                await callback.bot.send_message(target_user_id, "❌ رسید واریز شما توسط مدیر رد شد.", parse_mode="Markdown")
            except Exception:
                pass
    elif action_type == "w":
        if status == "acc":
            amount = float(parts[4])
            bal = await get_balance(target_user_id)
            if bal >= amount:
                await update_balance(target_user_id, -amount)
                await callback.message.edit_text(text="✅ برداشت تأیید و از حساب کاربر کسر شد.")
                try:
                    await callback.bot.send_message(target_user_id, f"✅ درخواست برداشت شما به مبلغ `{amount:,.0f} میو` تأیید شد.", parse_mode="Markdown")
                except Exception:
                    pass
            else:
                await callback.message.edit_text(text="⚠️ موجودی کاربر کافی نبود!")
        else:
            await callback.message.edit_text(text="❌ درخواست برداشت رد شد.")
            try:
                await callback.bot.send_message(target_user_id, "❌ درخواست برداشت شما توسط مدیر رد شد.", parse_mode="Markdown")
            except Exception:
                pass
    await callback.answer()

@router.message(F.text.regexp(r"^#(زوج|فرد)\s+(.+)$"))
async def start_dice_game(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ بازی تاس فقط در گروه‌ها قابل اجراست!")
    
    parts = message.text.replace("#", "").split()
    choice = parts[0]
    try:
        amount = parse_amount(parts[1])
    except ValueError:
        return await message.reply("⚠️ مبلغ نامعتبر است.")

    if amount < MIN_BET:
        return await message.reply(f"❌ حداقل مبلغ شرط‌بندی {MIN_BET:,.0f} میو است.")

    user_id = message.from_user.id
    bal = await get_balance(user_id)
    if bal < amount:
        return await message.reply(f"❌ موجودی کافی نیست! موجودی: {bal:,.0f} میو")

    await update_balance(user_id, -amount)
    active_dice_games[user_id] = {"choice": choice, "amount": amount, "rolls": []}

    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ لغو شرط", callback_data=f"dice_cancel_{user_id}")]
    ])

    text = (
        f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
        f"🎰 شرط ثبت شد\n\n"
        f"👤 {message.from_user.mention_html()}\n\n"
        f"🎯 شرط: «{choice}»\n"
        f"💰 مبلغ: `{amount:,.0f} میو`\n\n"
        f"🎲 لطفاً ۳ تاس بیندازید...\n"
        f"⏳ فقط ۶۰ ثانیه وقت داری، وگرنه ۵۰% مبلغ به عنوان جریمه کسر میشه."
    )
    await message.reply(text, reply_markup=cancel_markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("dice_cancel_"))
async def cancel_dice_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_user_id = int(callback.data.split("_")[2])
    
    if user_id != target_user_id:
        return await callback.answer("❌ این دکمه برای شما نیست!", show_alert=True)
    
    if user_id in active_dice_games:
        game = active_dice_games.pop(user_id)
        await update_balance(user_id, game["amount"])
        await callback.message.edit_text("❌ شرط شما لغو شد و مبلغ به حسابتان برگشت.")
    else:
        await callback.answer("⚠️ این شرط قبلاً انجام شده یا منقضی شده است.", show_alert=True)

@router.message(F.dice)
async def handle_dice_roll(message: Message):
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
        rolls_list = game["rolls"]

        new_bal = await get_balance(user_id)
        if won:
            prize = game["amount"] * 1.5
            await update_balance(user_id, prize)
            new_bal = await get_balance(user_id)
            result_text = (
                f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
                f"👤 {message.from_user.mention_html()}\n"
                f"🎲 تاس‌ها: `{rolls_list}`\n"
                f"🎉 مجموع: `{total} ({game['choice']})`\n"
                f"🎉 احسنت! برنده شدی.\n"
                f"💰 جایزه: `{prize:,.0f} میو`\n"
                f"🆕 موجودی جدید: `{new_bal:,.0f} میو`"
            )
        else:
            result_text = (
                f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
                f"👤 {message.from_user.mention_html()}\n"
                f"🎲 تاس‌ها: `{rolls_list}`\n"
                f"😔 مجموع: `{total} ({'زوج' if is_even else 'فرد'})`\n"
                f"💥 باختی! خداحافظ.\n"
                f"🆕 موجودی جدید: `{new_bal:,.0f} میو`"
            )
        await message.reply(result_text, parse_mode="HTML")
        del active_dice_games[user_id]

@router.message(F.text.regexp(r"^(?:#)?پوپ\s+(.+)$"))
async def start_pop_game(message: Message):
    if message.chat.type == "private":
        return await message.reply("❌ بازی پوپ فقط در گروه قابل اجراست!")
    try:
        amount = parse_amount(message.text.replace("#", "").split()[1])
    except ValueError:
        return await message.reply("⚠️ مبلغ نامعتبر.")

    if amount < MIN_BET:
        return await message.reply(f"❌ حداقل مبلغ شرط‌بندی {MIN_BET:,.0f} میو است.")

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
        f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
        f"💩 **بازی پوپ**\n👤 بازیکن: {message.from_user.mention_html()}\n\n"
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
async def pop_begin(callback: CallbackQuery):
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
        f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
        f"💩 پوپ — 👤 بازیکن\n"
        f"🎮 مرحله {stage+1} از ۵\n"
        f"💰 شرط: `{bet:,.0f} میو`\n"
        f"📈 جایزه فعلی: `{curr_prize:,.0f} میو`"
    )

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
async def pop_click(callback: CallbackQuery):
    parts = callback.data.split("_")
    owner_id, stg, col = int(parts[2]), int(parts[3]), int(parts[4])
    if callback.from_user.id != owner_id: return await callback.answer("❌ خطا", show_alert=True)

    game = active_pop_games.get(owner_id)
    if not game or game["current_stage"] != stg: return

    row_data = game["stages"][stg]
    game["revealed_rows"][stg] = row_data
    if row_data[col] == 1:
        for r in range(5): game["revealed_rows"][r] = game["stages"][r]
        await render_pop(callback.message, owner_id, is_edit=True)
        await callback.message.answer("💥 به پوپ خوردی! باختی.")
        del active_pop_games[owner_id]
    else:
        game["current_stage"] += 1
        if game["current_stage"] >= 5:
            prize = game["bet"] * 4.0
            await update_balance(owner_id, prize)
            for r in range(5): game["revealed_rows"][r] = game["stages"][r]
            await render_pop(callback.message, owner_id, is_edit=True)
            await callback.message.answer(f"🏆 برنده نهایی شدی!\n💰 جایزه: `{prize:,.0f} میو`", parse_mode="Markdown")
            del active_pop_games[owner_id]
        else:
            await render_pop(callback.message, owner_id, is_edit=True)

@router.callback_query(F.data.startswith("pop_cash_"))
async def pop_cash(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id: return
    game