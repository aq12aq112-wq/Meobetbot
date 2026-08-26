import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import add_user, get_balance, get_referrals_count, get_setting, set_setting, get_all_users, get_all_groups
from config import ADMIN_IDS

router = Router()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

class AdminSettingsState(StatesGroup):
    waiting_for_pop_multiplier = State()

def get_main_menu(user_id: int):
    keyboard = [
        [
            InlineKeyboardButton(text="موجودی من 💰", callback_data="my_balance"),
            InlineKeyboardButton(text="شارژ حساب 💳", callback_data="charge_account")
        ],
        [
            InlineKeyboardButton(text="برداشت وجه 💸", callback_data="withdraw_menu"),
            InlineKeyboardButton(text="ترید 📈", callback_data="trade_menu")
        ],
        [
            InlineKeyboardButton(text="زیرمجموعه‌گیری 👥", callback_data="referral_menu"),
            InlineKeyboardButton(text="راهنمای ربات 📖", callback_data="help_menu")
        ]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(text="⚙️ پنل مدیریت", callback_data="admin_panel")])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type != "private":
        return

    args = message.text.split()
    ref_by = 0
    if len(args) > 1 and args[1].isdigit():
        potential_ref = int(args[1])
        if potential_ref != message.from_user.id:
            ref_by = potential_ref

    await add_user(message.from_user.id, message.from_user.username or "NoUsername", ref_by)
    
    welcome_text = (
        f"💎 به کازینو و پلتفرم معاملاتی **میوبت (MEOWBET)** خوش آمدید، {message.from_user.first_name}!\n\n"
        "پیشرفته‌ترین ربات سرگرمی، ترید و بازی‌های آنلاین با واحد پول **میو (MEOW)**.\n"
        "از منوی زیر برای شروع استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(message.from_user.id), parse_mode="Markdown")

@router.message(F.text.in_({"راهنما", "/help", "راهنمای ربات"}))
async def text_help(message: Message):
    text = (
        "📖 **راهنمای جامع ربات میوبت (MEOWBET)**\n\n"
        "🎮 بازی‌ها و امکانات در ربات قابل دسترسی هستند.\n"
        "• برای چک کردن موجودی بنویسید: `موجودی`\n"
        "• برای دیدن راهنما بنویسید: `راهنما`\n\n"
        "💳 واحد پول تمام بازی‌ها و تراکنش‌ها **میو (MEOW)** است."
    )
    await message.reply(text, parse_mode="Markdown")

@router.message(F.text.in_({"موجودی", "موجودی من", "balance"}))
async def text_balance(message: Message):
    balance = await get_balance(message.from_user.id)
    text = (
        f"💼 **حساب کاربری شما**\n\n"
        f"🆔 آیدی تلگرام: `{message.from_user.id}`\n"
        f"💰 موجودی فعلی: **{balance:,.0f} میو**"
    )
    await message.reply(text, parse_mode="Markdown")

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    if callback.message.chat.type != "private":
        await callback.answer("این دکمه‌ها فقط در چت خصوصی ربات کار می‌کنند!", show_alert=True)
        return
    await callback.message.edit_text(
        "منوی اصلی ربات میوبت 🐾\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_main_menu(callback.from_user.id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "my_balance")
async def cb_my_balance(callback: CallbackQuery):
    balance = await get_balance(callback.from_user.id)
    text = (
        f"💼 **حساب کاربری شما**\n\n"
        f"🆔 آیدی تلگرام: `{callback.from_user.id}`\n"
        f"💰 موجودی فعلی: **{balance:,.0f} میو**"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "referral_menu")
async def cb_referral(callback: CallbackQuery):
    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"
    refs_count = await get_referrals_count(callback.from_user.id)
    
    text = (
        f"👥 **سیستم زیرمجموعه‌گیری میوبت**\n\n"
        f"با دعوت دوستان خود به ربات، ۵۰k میو هدیه بگیرید!\n\n"
        f"🔗 لینک اختصاصی شما:\n`{ref_link}`\n\n"
        f"📊 تعداد زیرمجموعه‌های شما: **{refs_count} نفر**"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "help_menu")
async def cb_help(callback: CallbackQuery):
    text = (
        "📖 **راهنمای جامع ربات میوبت (MEOWBET)**\n\n"
        "🎮 **بازی‌ها با واحد میو:**\n"
        "• بازی پوپ: `پوپ [مبلغ]` یا `#پوپ [مبلغ]`\n\n"
        "💳 واحد پول تمام بازی‌ها و تراکنش‌ها **میو (MEOW)** است."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "trade_menu")
async def cb_trade(callback: CallbackQuery):
    text = "📈 **بخش ترید و پیش‌بینی بازار**\n\nبه زودی فعال خواهد شد!"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ دسترسی ندارید!", show_alert=True)
        return
        
    text = "⚙️ **پنل مدیریت پیشرفته میوبت**\n\nگزینه مورد نظر را انتخاب کنید:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کلی ربات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ تنظیم ضریب پوپ", callback_data="admin_set_pop")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("دسترسی ندارید!", show_alert=True)
        return
        
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT SUM(balance) FROM users") as cursor:
            total_balance = (await cursor.fetchone())[0] or 0.0
            
    text = (
        f"📊 **آمار سیستم میوبت**\n\n"
        f"👥 کل کاربران: **{users_count} نفر**\n"
        f"💰 مجموع موجودی میو کاربران: **{total_balance:,.0f} میو**"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_set_pop")
async def cb_admin_set_pop(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    current = await get_setting("pop_multiplier")
    text = f"⚙️ ضریب فعلی بازی پوپ: `{current}`\n\nلطفاً ضریب جدید را وارد کنید (مثلاً `1.5` یا `2`):"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")]]))
    await state.set_state(AdminSettingsState.waiting_for_pop_multiplier)
    await callback.answer()

@router.message(AdminSettingsState.waiting_for_pop_multiplier)
async def process_new_pop_mult(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        val = float(message.text.strip())
        if val <= 0: raise ValueError()
    except ValueError:
        await message.answer("⚠️ مقدار نامعتبر است. لطفاً عدد اعشاری معتبر وارد کنید:")
        return

    await set_setting("pop_multiplier", str(val))
    await state.clear()
    await message.answer(f"✅ ضریب بازی پوپ با موفقیت به `{val}` تغییر یافت.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ پنل مدیریت", callback_data="admin_panel")]]))

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    text = "📢 **ارسال پیام همگانی**\n\nلطفاً پیام خود را (متن یا عکس همراه با کپشن) ارسال کنید تا به تمام کاربران (پی‌وی) و گروه‌ها ارسال شود:"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")]]))
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await state.clear()
    status_msg = await message.answer("⏳ در حال ارسال پیام همگانی به کاربران و گروه‌ها...")

    users = await get_all_users()
    groups = await get_all_groups()

    success_users = 0
    success_groups = 0

    for uid in users:
        try:
            if message.photo:
                await message.bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            else:
                await message.bot.send_message(uid, message.text)
            success_users += 1
            await asyncio.sleep(0.04)
        except:
            pass

    for gid in groups:
        try:
            if message.photo:
                await message.bot.send_photo(gid, message.photo[-1].file_id, caption=message.caption)
            else:
                await message.bot.send_message(gid, message.text)
            success_groups += 1
            await asyncio.sleep(0.04)
        except:
            pass

    await status_msg.edit_text(
        f"✅ **پیام همگانی با موفقیت ارسال شد!**\n\n"
        f"👥 ارسال شده به پی‌وی کاربران: {success_users} نفر\n"
        f"🏛 ارسال شده به گروه‌ها: {success_groups} گروه"
    )
