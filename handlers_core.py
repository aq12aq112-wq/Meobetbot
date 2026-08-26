from aiogram.fsm.state import State, StatesGroup

class BroadcastState(StatesGroup):
    waiting_for_message = State()

class AdminSettingsState(StatesGroup):
    waiting_for_pop_multiplier = State()

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
    text = "📢 **ارسال پیام همگانی**\n\nلطفاً پیام خود را (متن، عکس همراه با کپشن) ارسال کنید تا به تمام کاربران (پی‌وی) و گروه‌ها ارسال شود:"
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

    # ارسال به کاربران پی‌وی
    for uid in users:
        try:
            if message.photo:
                await message.bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            else:
                await message.bot.send_message(uid, message.text)
            success_users += 1
            await asyncio.sleep(0.05)
        except:
            pass

    # ارسال به گروه‌ها
    for gid in groups:
        try:
            if message.photo:
                await message.bot.send_photo(gid, message.photo[-1].file_id, caption=message.caption)
            else:
                await message.bot.send_message(gid, message.text)
            success_groups += 1
            await asyncio.sleep(0.05)
        except:
            pass

    await status_msg.edit_text(
        f"✅ **پیام همگانی با موفقیت ارسال شد!**\n\n"
        f"👥 ارسال شده به پی‌وی کاربران: {success_users} نفر\n"
        f"🏛 ارسال شده به گروه‌ها: {success_groups} گروه"
    )
