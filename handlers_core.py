import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from database import add_user, get_balance, get_referrals_count
from config import ADMIN_IDS

router = Router()

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
    # اگر در گروه بود، دکمه منوی اصلی یا استارت کار نکند یا پیام عمومی ندهد
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


# ---------- پاسخ به دستورات متنی در گروه و پی‌وی (راهنما و موجودی) ----------
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


# ---------- دکمه‌های شیشه‌ای (فقط در پی‌وی کار کنند) ----------
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
    await callback.message.edit_text(text, reply_markup=keyboard, parse_Mode="Markdown")
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
        "• بازی پوپ: `پوپ [مبلغ]`\n"
        "• بازی مین: `مین [مبلغ]`\n"
        "• بازی تاس: `تاس [مبلغ]`\n\n"
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
