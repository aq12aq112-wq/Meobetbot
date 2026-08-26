from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from database import add_user, get_user, get_balance, get_referrals_count
from config import CARD_NUMBER, CARD_HOLDER

router = Router()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="موجودی من 💰", callback_data="my_balance"),
            InlineKeyboardButton(text="شارژ حساب 💳", callback_data="charge_account")
        ],
        [
            InlineKeyboardButton(text="ترید 📈", callback_data="trade_menu"),
            InlineKeyboardButton(text="زیرمجموعه‌گیری 👥", callback_data="referral_menu")
        ],
        [
            InlineKeyboardButton(text="راهنمای ربات 📖", callback_data="help_menu")
        ]
    ])

@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    ref_by = 0
    if len(args) > 1 and args[1].isdigit():
        potential_ref = int(args[1])
        if potential_ref != message.from_user.id:
            ref_by = potential_ref

    await add_user(message.from_user.id, message.from_user.username or "NoUsername", ref_by)
    
    welcome_text = (
        f"💎 به کازینو و پلتفرم معاملاتی **میوبت (MEOWBET)** خوش آمدید، {message.from_user.first_name}!\n\n"
        "پیشرفته‌ترین ربات سرگرمی، ترید و بازی‌های آنلاین با ضرایب واقعی.\n"
        "از منوی زیر برای شروع استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "منوی اصلی ربات میوبت 🐾\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "my_balance")
async def cb_my_balance(callback: CallbackQuery):
    balance = await get_balance(callback.from_user.id)
    text = (
        f"💼 **حساب کاربری شما**\n\n"
        f"🆔 آیدی تلگرام: `{callback.from_user.id}`\n"
        f"💰 موجودی فعلی: **{balance:,.0f} تومان**\n\n"
        "برای افزایش موجودی از بخش شارژ حساب اقدام کنید."
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
        f"با دعوت دوستان خود به ربات، به ازای فعالیت آن‌ها پاداش بگیرید!\n\n"
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
        "🎮 **دستورات بازی‌ها:**\n"
        "• بازی پوپ: `پوپ [مبلغ]` (مثلاً `پوپ 50000`)\n"
        "• بازی مین و الماس: `مین [مبلغ]` (مثلاً `مین 100000`)\n"
        "• بازی تاس: `تاس [مبلغ]` (مثلاً `تاس 20000`)\n\n"
        "💳 **نحوه شارژ حساب:**\n"
        "از طریق بخش شارژ حساب، مبلغ را وارد کرده و پس از وخاری به کارت اعلامی، رسید آن را ارسال کنید تا ادمین تأیید کند.\n\n"
        f"📌 **شماره کارت پیشفرض:**\n`{CARD_NUMBER}`\nبه نام: {CARD_HOLDER}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "trade_menu")
async def cb_trade(callback: CallbackQuery):
    text = (
        "📈 **بخش ترید و پیش‌بینی بازار**\n\n"
        "این بخش به زودی با نمودارهای لحظه‌ای ارزهای دیجیتال و طلا فعال خواهد شد. فعلاً از بازی‌های هیجان‌انگیز میوبت لذت ببرید!"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
