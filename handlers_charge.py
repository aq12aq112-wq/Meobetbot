from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import add_transaction, get_transaction, update_transaction_status, update_balance
from config import CARD_NUMBER, CARD_HOLDER, ADMIN_IDS

router = Router()

class ChargeState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()

@router.callback_query(F.data == "charge_account")
async def cb_charge_start(callback: CallbackQuery, state: FSMContext):
    text = (
        "💳 **شارژ حساب کاربری**\n\n"
        "لطفاً مبلغ مورد نظر خود برای شارژ را به **تومان** وارد کنید (مثلاً: `50000` یا `100k`):"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ لغو", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(ChargeState.waiting_for_amount)
    await callback.answer()

@router.message(ChargeState.waiting_for_amount)
async def process_charge_amount(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    multiplier = 1
    if text.endswith('k'):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith('m'):
        multiplier = 1000000
        text = text[:-1]
        
    try:
        amount = float(text) * multiplier
        if amount < 1000:
            await message.answer("⚠️ حداقل مبلغ شارژ ۱,۰۰۰ تومان است. لطفاً مبلغ بیشتری وارد کنید:")
            return
    except ValueError:
        await message.answer("⚠️ مبلغ نامعتبر است. لطفاً فقط عدد وارد کنید (مثلاً 50000):")
        return

    await state.update_data(amount=amount)
    
    instruction = (
        f"💳 **کارت به کارت برای شارژ حساب**\n\n"
        f"مبلغ: **{amount:,.0f} تومان**\n\n"
        f"لطفاً مبلغ فوق را به شماره کارت زیر واریز نمایید:\n"
        f"`{CARD_NUMBER}`\n"
        f"به نام: {CARD_HOLDER}\n\n"
        "پس از واریز، **عکس رسید** یا **کد پیگیری تراکنش** را برای ما ارسال کنید:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="main_menu")]
    ])
    await message.answer(instruction, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(ChargeState.waiting_for_receipt)

@router.message(ChargeState.waiting_for_receipt, F.text | F.photo)
async def process_charge_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")
    
    receipt_info = ""
    if message.photo:
        receipt_info = f"photo:{message.photo[-1].file_id}"
    else:
        receipt_info = f"text:{message.text}"
        
    tx_id = await add_transaction(message.from_user.id, amount, receipt_info)
    await state.clear()
    
    await message.answer("✅ رسید شما با موفقیت ثبت شد و برای بررسی به مدیریت ارسال گردید. به زودی حساب شما شارژ می‌شود.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]]))
    
    # ارسال به ادمین‌ها
    admin_text = (
        f"🔔 **درخواست شارژ جدید**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (`{message.from_user.id}`)\n"
        f"💰 مبلغ: **{amount:,.0f} تومان**\n"
        f"🆔 شناسه تراکنش: `{tx_id}`"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأیید و شارژ", callback_data=f"adm_approve_{tx_id}"),
            InlineKeyboardButton(text="❌ رد درخواست", callback_data=f"adm_reject_{tx_id}")
        ]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await message.bot.send_photo(admin_id, message.photo[-1].file_id, caption=admin_text, reply_markup=admin_kb, parse_mode="Markdown")
            else:
                await message.bot.send_message(admin_id, admin_text + f"\n\nمتن رسید: {message.text}", reply_markup=admin_kb, parse_mode="Markdown")
        except Exception:
            pass

@router.callback_query(F.data.startswith("adm_approve_"))
async def admin_approve_tx(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("شما دسترسی ادمین ندارید!", show_alert=True)
        return
        
    tx_id = int(callback.data.split("_")[2])
    tx = await get_transaction(tx_id)
    
    if not tx or tx["status"] != "pending":
        await callback.answer("این تراکنش قبلاً پردازش شده یا وجود ندارد.", show_alert=True)
        return
        
    await update_transaction_status(tx_id, "approved")
    await update_balance(tx["user_id"], tx["amount"])
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **وضعیت: تأیید و واریز شد**", parse_mode="Markdown")
    await callback.answer("تراکنش با موفقیت تأیید و موجودی کاربر شارژ شد.")
    
    try:
        await callback.bot.send_message(tx["user_id"], f"🎉 حساب شما به مبلغ **{tx['amount']:,.0f} تومان** با موفقیت شارژ شد!", parse_mode="Markdown")
    except Exception:
        pass

@router.callback_query(F.data.startswith("adm_reject_"))
async def admin_reject_tx(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("شما دسترسی ادمین ندارید!", show_alert=True)
        return
        
    tx_id = int(callback.data.split("_")[2])
    tx = await get_transaction(tx_id)
    
    if not tx or tx["status"] != "pending":
        await callback.answer("این تراکنش قبلاً پردازش شده یا وجود ندارد.", show_alert=True)
        return
        
    await update_transaction_status(tx_id, "rejected")
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **وضعیت: رد شد**", parse_mode="Markdown")
    await callback.answer("تراکنش رد شد.")
    
    try:
        await callback.bot.send_message(tx["user_id"], "⚠️ درخواست شارژ حساب شما توسط مدیریت رد شد. در صورت وجود مشکل با پشتیبانی تماس بگیرید.")
    except Exception:
        pass
