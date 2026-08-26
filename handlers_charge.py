from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_balance, add_transaction, get_transaction, update_transaction_status, update_balance
from config import CARD_NUMBER, CARD_HOLDER, ADMIN_IDS

router = Router()

class ChargeState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()

@router.callback_query(F.data == "charge_account")
async def cb_charge_start(callback: CallbackQuery, state: FSMContext):
    text = (
        "💳 **شارژ حساب کاربری (میو)**\n\n"
        "لطفاً تعداد میو مورد نظر برای شارژ را وارد کنید (مثلاً: `50000` یا `50k`):"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ لغو", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
    await state.set_state(ChargeState.waiting_for_amount)

@router.message(ChargeState.waiting_for_amount)
async def process_charge_amount(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    multiplier = 1
    if text.endswith('k'): multiplier = 1000; text = text[:-1]
    elif text.endswith('m'): multiplier = 1000000; text = text[:-1]
        
    try:
        amount = float(text) * multiplier
        if amount <= 0: raise ValueError()
    except ValueError:
        await message.answer("⚠️ مقدار نامعتبر است. لطفاً فقط عدد وارد کنید (مثلاً 50k):")
        return

    await state.update_data(amount=amount)
    
    instruction = (
        f"💳 **افزایش موجودی میو**\n\n"
        f"مبلغ: **{amount:,.0f} میو**\n\n"
        f"لطفاً معادل ریالی را به کارت زیر واریز کرده و رسید بفرستید:\n"
        f"`{CARD_NUMBER}`\n"
        f"به نام: {CARD_HOLDER}"
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
    
    receipt_info = f"photo:{message.photo[-1].file_id}" if message.photo else f"text:{message.text}"
    tx_id = await add_transaction(message.from_user.id, amount, receipt_info)
    await state.clear()
    
    await message.answer("✅ رسید شما ثبت شد و برای ادمین ارسال گردید.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]]))
    
    admin_text = (
        f"🔔 **درخواست شارژ جدید (میو)**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (`{message.from_user.id}`)\n"
        f"💰 مقدار: **{amount:,.0f} میو**\n"
        f"🆔 شناسه: `{tx_id}`\n"
        f"متن رسید: {message.text if message.text else 'عکس رسید'}"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأیید", callback_data=f"adm_approve_{tx_id}"),
            InlineKeyboardButton(text="❌ رد", callback_data=f"adm_reject_{tx_id}")
        ]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await message.bot.send_photo(admin_id, message.photo[-1].file_id, caption=admin_text, reply_markup=admin_kb, parse_mode="Markdown")
            else:
                await message.bot.send_message(admin_id, admin_text, reply_markup=admin_kb, parse_mode="Markdown")
        except Exception:
            pass

@router.callback_query(F.data.startswith("adm_approve_"))
async def admin_approve_tx(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("دسترسی ندارید!", show_alert=True)
        return
    tx_id = int(callback.data.split("_")[2])
    tx = await get_transaction(tx_id)
    if not tx or tx["status"] != "pending":
        await callback.answer("تراکنش نامعتبر یا قبلاً پردازش شده.", show_alert=True)
        return
    
    await update_transaction_status(tx_id, "approved")
    await update_balance(tx["user_id"], tx["amount"])
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n✅ **تأیید و واریز شد**", parse_mode="Markdown", reply_markup=None)
        else:
            await callback.message.edit_text(text=(callback.message.text or "") + "\n\n✅ **تأیید و واریز شد**", parse_mode="Markdown", reply_markup=None)
    except Exception:
        pass
        
    try:
        await callback.bot.send_message(tx["user_id"], f"🎉 حساب شما به مبلغ **{tx['amount']:,.0f} میو** شارژ شد!", parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer("تراکنش با موفقیت تأیید شد.")

@router.callback_query(F.data.startswith("adm_reject_"))
async def admin_reject_tx(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("دسترسی ندارید!", show_alert=True)
        return
    tx_id = int(callback.data.split("_")[2])
    tx = await get_transaction(tx_id)
    if not tx or tx["status"] != "pending":
        await callback.answer("تراکنش نامعتبر.", show_alert=True)
        return
        
    await update_transaction_status(tx_id, "rejected")
    
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n❌ **رد شد**", parse_mode="Markdown", reply_markup=None)
        else:
            await callback.message.edit_text(text=(callback.message.text or "") + "\n\n❌ **رد شد**", parse_mode="Markdown", reply_markup=None)
    except Exception:
        pass
        
    try:
        await callback.bot.send_message(tx["user_id"], "⚠️ درخواست شارژ شما رد شد.")
    except Exception:
        pass
    await callback.answer("تراکنش رد شد.")


# ---------- بخش برداشت وجه ----------
class WithdrawState(StatesGroup):
    waiting_for_card = State()
    waiting_for_amount = State()

@router.callback_query(F.data == "withdraw_menu")
async def cb_withdraw_start(callback: CallbackQuery, state: FSMContext):
    balance = await get_balance(callback.from_user.id)
    text = (
        f"💸 **بخش برداشت میو**\n\n"
        f"💰 موجودی شما: **{balance:,.0f} میو**\n\n"
        "لطفاً شماره کارت میویی خود را وارد کنید:\n"
        "*(مسئولیت درست یا غلط وارد کردن کارت با خود کاربر است)*"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
    await state.set_state(WithdrawState.waiting_for_card)

@router.message(WithdrawState.waiting_for_card)
async def process_withdraw_card(message: Message, state: FSMContext):
    card_info = message.text.strip()
    await state.update_data(card_info=card_info)
    await message.answer("💳 اطلاعات کارت ثبت شد.\n\nحالا **مقدار میو** مورد نظر برای برداشت را وارد کنید (مثلاً `10000` یا `10k`):")
    await state.set_state(WithdrawState.waiting_for_amount)

@router.message(WithdrawState.waiting_for_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    card_info = data.get("card_info")
    
    text = message.text.strip().lower()
    multiplier = 1
    if text.endswith('k'): multiplier = 1000; text = text[:-1]
    elif text.endswith('m'): multiplier = 1000000; text = text[:-1]
    
    try:
        amount = float(text) * multiplier
        if amount <= 0: raise ValueError()
    except ValueError:
        await message.answer("⚠️ مقدار نامعتبر است. لطفاً فقط عدد وارد کنید:")
        return

    balance = await get_balance(message.from_user.id)
    if balance < amount:
        await message.answer(f"❌ موجودی کافی نیست! موجودی شما: {balance:,.0f} میو")
        return

    tx_id = await add_transaction(message.from_user.id, amount, f"withdraw:{card_info}")
    await update_balance(message.from_user.id, -amount)
    await state.clear()

    await message.answer("✅ درخواست برداشت شما با موفقیت ثبت شد و به ادمین ارسال گردید.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]]))

    admin_text = (
        f"🚨 **درخواست برداشت جدید (میو)**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (`{message.from_user.id}`)\n"
        f"💰 مقدار: **{amount:,.0f} میو**\n"
        f"🆔 شناسه: `{tx_id}`\n"
        f"💳 اطلاعات کارت مقصد:\n`{card_info}`"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأیید و واریز", callback_data=f"adm_w_approve_{tx_id}"),
            InlineKeyboardButton(text="❌ رد", callback_data=f"adm_w_reject_{tx_id}")
        ]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text, reply_markup=admin_kb, parse_mode="Markdown")
        except Exception:
            pass

# اصلاح دقیق کال‌بک‌های تأیید و رد برداشت
@router.callback_query(F.data.startswith("adm_w_approve_"))
async def admin_approve_withdraw(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("دسترسی ندارید!", show_alert=True)
        return
    tx_id = int(callback.data.split("_")[3])
    tx = await get_transaction(tx_id)
    if not tx or tx["status"] != "pending":
        await callback.answer("تراکنش نامعتبر یا قبلاً پردازش شده.", show_alert=True)
        return
    
    await update_transaction_status(tx_id, "approved")
    try:
        await callback.message.edit_text(text=(callback.message.text or "") + "\n\n✅ **تأیید واریز انجام شد**", parse_mode="Markdown", reply_markup=None)
    except Exception:
        pass
    try:
        await callback.bot.send_message(tx["user_id"], f"🎉 مبلغ **{tx['amount']:,.0f} میو** از درخواست برداشت شما واریز شد!", parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer("برداشت تأیید شد.")

@router.callback_query(F.data.startswith("adm_w_reject_"))
async def admin_reject_withdraw(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("دسترسی ندارید!", show_alert=True)
        return
    tx_id = int(callback.data.split("_")[3])
    tx = await get_transaction(tx_id)
    if not tx or tx["status"] != "pending":
        await callback.answer("تراکنش نامعتبر.", show_alert=True)
        return
        
    await update_transaction_status(tx_id, "rejected")
    await update_balance(tx["user_id"], tx["amount"]) # برگشت موجودی
    
    try:
        await callback.message.edit_text(text=(callback.message.text or "") + "\n\n❌ **برداشت رد شد و مبلغ به حساب کاربر برگشت**", parse_mode="Markdown", reply_markup=None)
    except Exception:
        pass
    try:
        await callback.bot.send_message(tx["user_id"], f"⚠️ درخواست برداشت شما رد شد و مبلغ {tx['amount']:,.0f} میو به حسابتان برگشت داده شد.")
    except Exception:
        pass
    await callback.answer("برداشت رد شد.")
