import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"
ADMIN_ID = 6937799221
ADMIN_CARD = "760188800770"
MIN_LIMIT = 50000
MIN_BET = 20000

# دیتابیس در حافظه برای پایداری ۱۰۰٪ بدون خطای فایل
users_db = {}
active_dice_games = {}
charge_states = {}
withdraw_states = {}

def get_balance(user_id):
    if user_id not in users_db:
        users_db[user_id] = 100000.0
    return users_db[user_id]

def update_balance(user_id, amount):
    users_db[user_id] = get_balance(user_id) + amount

def parse_amount(val_str):
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        return float(val_str.replace("k", "")) * 1000
    return float(val_str)

router = Router()

def get_main_menu(user_id):
    buttons = [
        [InlineKeyboardButton(text="👤 حساب کاربری و موجودی", callback_data="menu_profile")],
        [InlineKeyboardButton(text="💳 شارژ حساب", callback_data="menu_charge"),
         InlineKeyboardButton(text="💵 برداشت وجه", callback_data="menu_withdraw")],
        [InlineKeyboardButton(text="📖 راهنمای بازی‌ها", callback_data="menu_help")]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="👑 پنل مدیریت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text.in_({"/start", "استارت", "منو"}))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await message.reply(
        "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت شرط ببندی!",
        reply_markup=get_main_menu(user_id), parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    user_id = callback.from_user.id

    if action == "profile":
        bal = get_balance(user_id)
        text = f"👤 **حساب کاربری:**\n🆔 آیدی: `{user_id}`\n💳 موجودی: `{bal:,.0f} میو`"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]])
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    elif action == "charge":
        charge_states[user_id] = "awaiting_amount"
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ لغو", callback_data="back_home")]])
        await callback.message.edit_text(f"💰 **شارژ موجودی**\n\nحداقل مبلغ شارژ `{MIN_LIMIT:,.0f} میو` است. مبلغ را بفرستید:", reply_markup=markup, parse_mode="Markdown")
    elif action == "withdraw":
        withdraw_states[user_id] = {"step": "awaiting_card"}
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ لغو", callback_data="back_home")]])
        await callback.message.edit_text("💵 **برداشت وجه**\n\nابتدا شماره کارت خود را بفرستید:", reply_markup=markup, parse_mode="Markdown")
    elif action == "help":
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]])
        await callback.message.edit_text("📖 **راهنما:**\n• تاس: `#زوج [مبلغ]`\n• پوپ: `#پوپ [مبلغ]`", reply_markup=markup, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ دسترسی ندارید!", show_alert=True)
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]])
    await callback.message.edit_text("👑 **پنل مدیریت فعال است.**", reply_markup=markup, parse_mode="Markdown")

@router.callback_query(F.data == "back_home")
async def back_home(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت شرط ببندی!",
        reply_markup=get_main_menu(user_id), parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.text & ~F.text.startswith("#"))
async def text_handler(message: Message):
    user_id = message.from_user.id
    if user_id in charge_states and charge_states[user_id] == "awaiting_amount":
        try:
            amount = parse_amount(message.text)
        except ValueError:
            return await message.reply("⚠️ مبلغ نامعتبر است.")
        if amount < MIN_LIMIT:
            return await message.reply(f"❌ حداقل مبلغ شارژ {MIN_LIMIT:,.0f} میو است.")
        
        charge_states[user_id] = {"amount": amount}
        await message.reply(
            f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n💳 **به کارت زیر واریز کنید:**\n`{ADMIN_CARD}`\n\n💰 مبلغ: `{amount:,.0f} میو`\n\n📸 رسید رو بفرست.",
            parse_mode="Markdown"
        )
        return

@router.message(F.photo)
async def photo_handler(message: Message):
    user_id = message.from_user.id
    if user_id in charge_states:
        amount = charge_states[user_id]["amount"]
        del charge_states[user_id]
        
        admin_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأیید", callback_data=f"adm_c_acc_{user_id}_{int(amount)}"),
             InlineKeyboardButton(text="❌ رد", callback_data=f"adm_c_rej_{user_id}")]
        ])
        await message.reply("⏳ رسید ارسال شد.")
        await message.bot.send_photo(
            ADMIN_ID, photo=message.photo[-1].file_id,
            caption=f"📥 **رسید شارژ جدید:**\n👤 کاربر: `{user_id}`\n💰 مبلغ: `{amount:,.0f} میو`",
            reply_markup=admin_markup, parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("adm_"))
async def admin_action(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌", show_alert=True)
    parts = callback.data.split("_")
    action_type, status, target_id = parts[1], parts[2], int(parts[3])
    
    if action_type == "c" and status == "acc":
        amount = float(parts[4])
        update_balance(target_id, amount)
        await callback.message.edit_caption(caption=f"✅ تأیید شد. {amount:,.0f} واریز شد.")
        await callback.bot.send_message(target_id, f"✅ شارژ شما به مبلغ {amount:,.0f} میو تأیید شد.")
    await callback.answer()

async def main():
    await bot_polling_loop()

async def bot_polling_loop():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 MeowBet Cloud Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

