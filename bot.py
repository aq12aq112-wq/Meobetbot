import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

BOT_TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"
ADMIN_ID = 6937799221
ADMIN_CARD = "760188800770"
MIN_LIMIT = 50000
MIN_BET = 20000

bot = telebot.TeleBot(BOT_TOKEN)

# دیتابیس ساده در حافظه (برای پایداری تست روی ترموکس)
users_db = {}
active_dice_games = {}
active_pop_games = {}
charge_states = {}
withdraw_states = {}

def get_user_balance(user_id):
    if user_id not in users_db:
        users_db[user_id] = 100000.0  # موجودی اولیه برای تست
    return users_db[user_id]

def update_user_balance(user_id, amount):
    current = get_user_balance(user_id)
    users_db[user_id] = current + amount

def parse_amount(val_str):
    val_str = val_str.lower().replace("کی", "k").replace("میو", "").replace(",", "").strip()
    if "k" in val_str:
        return float(val_str.replace("k", "")) * 1000
    return float(val_str)

def get_main_menu(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👤 حساب کاربری و موجودی", callback_data="menu_profile"),
    )
    markup.row(
        InlineKeyboardButton("💳 شارژ حساب", callback_data="menu_charge"),
        InlineKeyboardButton("💵 برداشت وجه", callback_data="menu_withdraw")
    )
    markup.row(
        InlineKeyboardButton("📖 راهنمای بازی‌ها", callback_data="menu_help")
    )
    if user_id == ADMIN_ID:
        markup.row(InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel"))
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.reply_to(
        message,
        "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت شرط ببندی!",
        reply_markup=get_main_menu(user_id)
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "menu_profile":
        bal = get_user_balance(user_id)
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_home"))
        bot.edit_message_text(
            f"👤 **حساب کاربری شما:**\n\n🆔 آیدی: `{user_id}`\n💳 موجودی: `{bal:,.0f} میو`",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    elif call.data == "menu_charge":
        charge_states[user_id] = "awaiting_amount"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ لغو", callback_data="back_home"))
        bot.edit_message_text(
            f"💰 **شارژ موجودی**\n\nحداقل مبلغ شارژ `{MIN_LIMIT:,.0f} میو` است.\nمبلغ مورد نظر را ارسال کنید:",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    elif call.data == "menu_withdraw":
        withdraw_states[user_id] = {"step": "awaiting_card"}
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ لغو", callback_data="back_home"))
        bot.edit_message_text(
            "💵 **برداشت وجه**\n\nابتدا شماره کارت بانکی خود را ارسال کنید:",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    elif call.data == "menu_help":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_home"))
        bot.edit_message_text(
            "📖 **راهنمای بازی‌ها:**\n\n• تاس: `#زوج [مبلغ]` یا `#فرد [مبلغ]`\n• پوپ: `#پوپ [مبلغ]`",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_home"))
        bot.edit_message_text(
            "👑 **پنل مدیریت کل:**\n\nمدیریت تراکنش‌ها و حساب‌ها فعال است.",
            call.message.chat.id, call.message.message_id,
            reply_markup=markup, parse_mode="Markdown"
        )
    elif call.data == "back_home":
        bot.edit_message_text(
            "Meowie bet🐱\n\nاز کازینو با ربات میویی خسته شدی؟ میتونی با میوبت شرط ببندی!",
            call.message.chat.id, call.message.message_id,
            reply_markup=get_main_menu(user_id)
        )
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text and not message.text.startswith("#"))
def handle_text_inputs(message):
    user_id = message.from_user.id
    
    # شارژ
    if user_id in charge_states and charge_states[user_id] == "awaiting_amount":
        try:
            amount = parse_amount(message.text)
        except ValueError:
            return bot.reply_to(message, "⚠️ مبلغ نامعتبر است.")
        
        if amount < MIN_LIMIT:
            return bot.reply_to(message, f"❌ حداقل مبلغ شارژ {MIN_LIMIT:,.0f} میو است.")
        
        charge_states[user_id] = {"step": "awaiting_receipt", "amount": amount}
        bot.reply_to(
            message,
            f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n💳 **به کارت زیر واریز کنید:**\n`{ADMIN_CARD}`\n\n💰 مبلغ: `{amount:,.0f} میو`\n\n📸 بعد از واریز، رسید رو همینجا بفرست.",
            parse_mode="Markdown"
        )
        return

    # برداشت
    if user_id in withdraw_states:
        data = withdraw_states[user_id]
        if data["step"] == "awaiting_card":
            card = message.text.strip()
            withdraw_states[user_id] = {"step": "awaiting_amount", "card": card}
            bot.reply_to(message, "💵 مبلغ مورد نظر برای برداشت را وارد کنید (حداقل ۵۰,۰۰۰ میو):")
            return
        elif data["step"] == "awaiting_amount":
            try:
                amount = parse_amount(message.text)
            except ValueError:
                return bot.reply_to(message, "⚠️ مبلغ نامعتبر است.")
            
            if amount < MIN_LIMIT:
                return bot.reply_to(message, f"❌ حداقل مبلغ برداشت {MIN_LIMIT:,.0f} میو است.")
            
            bal = get_user_balance(user_id)
            if bal < amount:
                return bot.reply_to(message, f"❌ موجودی کافی نیست! موجودی: {bal:,.0f} میو")
            
            del withdraw_states[user_id]
            bot.reply_to(message, "⏳ درخواست برداشت شما ثبت شد و در صف بررسی قرار گرفت.")
            
            # ارسال به ادمین
            admin_markup = InlineKeyboardMarkup()
            admin_markup.row(
                InlineKeyboardButton("✅ تأیید", callback_data=f"adm_w_acc_{user_id}_{int(amount)}"),
                InlineKeyboardButton("❌ رد", callback_data=f"adm_w_rej_{user_id}")
            )
            bot.send_message(ADMIN_ID, f"📤 **درخواست برداشت جدید:**\n👤 کاربر: `{user_id}`\n💰 مبلغ: `{amount:,.0f} میو`", reply_markup=admin_markup, parse_mode="Markdown")
            return

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    if user_id in charge_states and isinstance(charge_states[user_id], dict):
        amount = charge_states[user_id]["amount"]
        del charge_states[user_id]
        
        admin_markup = InlineKeyboardMarkup()
        admin_markup.row(
            InlineKeyboardButton("✅ تأیید شارژ", callback_data=f"adm_c_acc_{user_id}_{int(amount)}"),
            InlineKeyboardButton("❌ رد رسید", callback_data=f"adm_c_rej_{user_id}")
        )
        bot.reply_to(message, "⏳ رسید شما برای مدیر ارسال شد.")
        bot.send_photo(
            ADMIN_ID, message.photo[-1].file_id,
            caption=f"📥 **رسید شارژ جدید:**\n👤 کاربر: `{user_id}`\n💰 مبلغ: `{amount:,.0f} میو`",
            reply_markup=admin_markup, parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_decision(call):
    if call.from_user.id != ADMIN_ID:
        return bot.answer_callback_query(call.id, "❌ دسترسی ندارید!", show_alert=True)
    
    parts = call.data.split("_")
    action_type, status, target_id = parts[1], parts[2], int(parts[3])
    
    if action_type == "c":
        if status == "acc":
            amount = float(parts[4])
            update_user_balance(target_id, amount)
            bot.edit_message_caption(f"✅ شارژ تأیید شد.\n💰 `{amount:,.0f} میو` واریز شد.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.send_message(target_id, f"✅ پرداخت شما تأیید شد و مبلغ `{amount:,.0f} میو` به موجودی اضافه شد.", parse_mode="Markdown")
        else:
            bot.edit_message_caption("❌ رسید شارژ رد شد.", call.message.chat.id, call.message.message_id)
            bot.send_message(target_id, "❌ رسید واریز شما توسط مدیر رد شد.")
    elif action_type == "w":
        if status == "acc":
            amount = float(parts[4])
            update_user_balance(target_id, -amount)
            bot.edit_message_text("✅ برداشت تأیید شد.", call.message.chat.id, call.message.message_id)
            bot.send_message(target_id, f"✅ درخواست برداشت شما به مبلغ `{amount:,.0f} میو` تأیید شد.", parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ درخواست برداشت رد شد.", call.message.chat.id, call.message.message_id)
            bot.send_message(target_id, "❌ درخواست برداشت شما توسط مدیر رد شد.")
    bot.answer_callback_query(call.id)

# بازی تاس
@bot.message_handler(regexp=r"^#(زوج|فرد)\s+(.+)$")
def start_dice_game(message):
    if message.chat.type == "private":
        return bot.reply_to(message, "❌ این بازی فقط در گروه‌ها قابل اجراست!")
    
    parts = message.text.replace("#", "").split()
    choice = parts[0]
    try:
        amount = parse_amount(parts[1])
    except ValueError:
        return bot.reply_to(message, "⚠️ مبلغ نامعتبر است.")

    if amount < MIN_BET:
        return bot.reply_to(message, f"❌ حداقل مبلغ شرط‌بندی {MIN_BET:,.0f} میو است.")

    user_id = message.from_user.id
    bal = get_user_balance(user_id)
    if bal < amount:
        return bot.reply_to(message, f"❌ موجودی کافی نیست! موجودی: {bal:,.0f} میو")

    update_user_balance(user_id, -amount)
    active_dice_games[user_id] = {"choice": choice, "amount": amount, "rolls": []}

    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ لغو شرط", callback_data=f"dice_cancel_{user_id}"))
    text = (
        f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
        f"🎰 شرط ثبت شد\n\n👤 @{message.from_user.username or message.from_user.first_name}\n\n"
        f"🎯 شرط: «{choice}»\n💰 مبلغ: `{amount:,.0f} میو`\n\n🎲 لطفاً ۳ تاس بیندازید..."
    )
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("dice_cancel_"))
def cancel_dice(call):
    user_id = call.from_user.id
    target_id = int(call.data.split("_")[2])
    if user_id != target_id:
        return bot.answer_callback_query(call.id, "❌ این دکمه برای شما نیست!", show_alert=True)
    
    if user_id in active_dice_games:
        game = active_dice_games.pop(user_id)
        update_user_balance(user_id, game["amount"])
        bot.edit_message_text("❌ شرط شما لغو شد و مبلغ به حسابتان برگشت.", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['dice'])
def handle_dice(message):
    user_id = message.from_user.id
    if user_id not in active_dice_games:
        return
    
    game = active_dice_games[user_id]
    game["rolls"].append(message.dice.value)

    if len(game["rolls"]) < 3:
        bot.reply_to(message, f"🎲 تاس {len(game['rolls'])} ثبت شد. {3 - len(game['rolls'])} تاس دیگر بفرستید.")
    else:
        total = sum(game["rolls"])
        is_even = total % 2 == 0
        won = (game["choice"] == "زوج" and is_even) or (game["choice"] == "فرد" and not is_even)
        rolls = game["rolls"]

        if won:
            prize = game["amount"] * 1.5
            update_user_balance(user_id, prize)
            new_bal = get_user_balance(user_id)
            res = (
                f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
                f"🎲 تاس‌ها: `{rolls}`\n🎉 مجموع: `{total} ({game['choice']})`\n"
                f"🎉 احسنت! برنده شدی.\n💰 جایزه: `{prize:,.0f} میو`\n🆕 موجودی جدید: `{new_bal:,.0f} میو`"
            )
        else:
            new_bal = get_user_balance(user_id)
            res = (
                f"Meowie bet🐱\n┗‌روبوت ۲ 🎰 میوبت 🏛\n\n"
                f"🎲 تاس‌ها: `{rolls}`\n😔 مجموع: `{total} ('زوج' if is_even else 'فرد')`\n"
                f"💥 باختی! خداحافظ.\n🆕 موجودی جدید: `{new_bal:,.0f} میو`"
            )
        bot.reply_to(message, res, parse_mode="Markdown")
        del active_dice_games[user_id]

print("🚀 MeowBet Bot is running perfectly...")
bot.infinity_polling()

نحوه اجرا توی ترموکس با دستور EOF
کافیه این دستور رو یکجا توی ترموکس بزنی تا فایل ساخته بشه و مستقیم اجراش کنی:
cat << 'EOF' > bot.py
# (کد بالا رو اینجا کپی کن)
EOF
python bot.py

