import telebot
from telebot import types
import sqlite3
import random

TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"
ADMIN_ID = 6937799221
CARD_NUMBER = "760188800770"

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 10000,
            invited_by INTEGER DEFAULT 0,
            refs_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user(user_id, username=""):
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, invited_by, refs_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, username, 10000))
        conn.commit()
        balance = 10000
    else:
        balance = row[0]
    conn.close()
    return balance

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

user_states = {}

def parse_amount(text):
    text = text.lower().strip()
    if 'k' in text:
        try:
            return int(text.replace('k', '')) * 1000
        except:
            return 10000
    try:
        return int(text)
    except:
        return 10000

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "کاربر"
    
    # بررسی سیستم دعوت (ریفال)
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            conn = sqlite3.connect("bot_database.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, username, balance, invited_by) VALUES (?, ?, ?, ?)", (user_id, username, 10000, ref_id))
                cursor.execute("UPDATE users SET refs_count = refs_count + 1, balance = balance + 5000 WHERE user_id = ?", (ref_id,))
                conn.commit()
                try:
                    bot.send_message(ref_id, "🎉 یک زیرمجموعه جدید اضافه شد و 5,000 میو پاداش گرفتید!")
                except:
                    pass
            conn.close()

    balance = get_user(user_id, username)
    
    # ۷ بخش اصلی ربات (کیبورد کامل)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💰 موجودی من", "💳 شارژ حساب")
    markup.add("📈 ترید", "🦋 برداشت وجه")
    markup.add("👥 زیرمجموعه‌گیری", "📖 راهنمای ربات")
    markup.add("➕ افزودن به گروه")
    if user_id == ADMIN_ID:
        markup.add("⚙️ پنل مدیریت")

    text = (
        f"🐱 **Meowbet | میوبنت** 🎰\n\n"
        f"👤 کاربر: @{username}\n"
        f"💳 موجودی شما: **{balance:,} میو**\n\n"
        f"🎮 **بازی‌ها و بخش‌ها:**\n"
        f"• 💎 پوپ: `پوپ [مبلغ]`\n"
        f"• 📦 مین: `مین [مبلغ]`\n"
        f"• 🎲 تاس: `#زوج [مبلغ]` یا `#فرد [مبلغ]`"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text and ("مین" in message.text or "پوپ" in message.text))
def handle_min_poop(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "کاربر"
    balance = get_user(user_id, username)
    
    parts = message.text.split()
    bet = parse_amount(parts[1]) if len(parts) > 1 else 10000

    if balance < bet:
        bot.reply_to(message, "❌ موجودی کافی نیست!")
        return

    update_balance(user_id, -bet)
    
    markup = types.InlineKeyboardMarkup(row_width=4)
    buttons = [types.InlineKeyboardButton("💎" if random.random() > 0.3 else "💣", callback_data=f"game_{user_id}_{bet}_{i}") for i in range(16)]
    markup.add(*buttons)
    
    game_type = "پوپ 💩" if "پوپ" in message.text else "مین و الماس 📦"
    game_text = f"🎰 بازی: {game_type}\n💲 شرط: **{bet:,} میو**\n\n👇 یک خانه انتخاب کنید:"
    bot.send_message(message.chat.id, game_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text and (message.text.startswith("#زوج") or message.text.startswith("#فرد")))
def handle_dice(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "کاربر"
    balance = get_user(user_id, username)
    
    parts = message.text.split()
    choice = "زوج" if "زوج" in parts[0] else "فرد"
    bet = parse_amount(parts[1]) if len(parts) > 1 else 10000

    if balance < bet:
        bot.reply_to(message, "❌ موجودی کافی نیست!")
        return

    update_balance(user_id, -bet)
    dice_result = random.randint(1, 6)
    is_even = (dice_result % 2 == 0)
    user_won = (choice == "زوج" and is_even) or (choice == "فرد" and not is_even)

    if user_won:
        win_amount = bet * 2
        update_balance(user_id, win_amount)
        result_text = f"🎉 تاس: {dice_result}\n✨ برنده شدید! جایزه: {win_amount:,} میو"
    else:
        result_text = f"😢 تاس: {dice_result}\n💥 باختید!"

    bot.reply_to(message, result_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "کاربر"
    balance = get_user(user_id, username)

    if text == "💰 موجودی من":
        bot.reply_to(message, f"💳 موجودی فعلی: **{balance:,} میو**", parse_mode="Markdown")
    elif text == "📖 راهنمای ربات":
        bot.reply_to(message, "📖 دستورات بازی:\nپوپ [مبلغ]\nمین [مبلغ]\n#زوج [مبلغ]\n#فرد [مبلغ]")
    elif text == "📈 ترید":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📈 صعودی", callback_data="trade_up"), types.InlineKeyboardButton("📉 نزولی", callback_data="trade_down"))
        bot.reply_to(message, "📈 جهت بازار را انتخاب کنید:", reply_markup=markup)
    elif text == "👥 زیرمجموعه‌گیری":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        conn = sqlite3.connect("bot_database.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT refs_count FROM users WHERE user_id = ?", (user_id,))
        r_row = cursor.fetchone()
        refs = r_row[0] if r_row else 0
        conn.close()
        bot.reply_to(message, f"👥 **سیستم زیرمجموعه‌گیری**\n\n🔗 لینک دعوت شما:\n`{ref_link}`\n\n👤 تعداد زیرمجموعه‌ها: {refs} نفر\n🎁 پاداش هر دعوت: 5,000 میو", parse_mode="Markdown")
    elif text == "💳 شارژ حساب":
        user_states[user_id] = "waiting_deposit_amount"
        bot.reply_to(message, "💳 لطفاً مبلغ شارژ را وارد کنید (مثلا 50k):")
    elif text == "🦋 برداشت وجه":
        user_states[user_id] = "waiting_withdraw_amount"
        bot.reply_to(message, f"🦋 موجودی شما: {balance:,}\nمبلغ برداشت را وارد کنید:")
    elif text == "⚙️ پنل مدیریت" and user_id == ADMIN_ID:
        bot.reply_to(message, "🛠 پنل مدیریت فعال است.")
    elif text == "➕ افزودن به گروه":
        bot.reply_to(message, f"https://t.me/{bot.get_me().username}?startgroup=true")
    elif user_id in user_states:
        state = user_states[user_id]
        if state == "waiting_deposit_amount":
            user_states[user_id] = f"waiting_receipt_{text}"
            bot.reply_to(message, f"✅ مبلغ {text} ثبت شد.\nبه کارت زیر واریز کنید و عکس رسید بفرستید:\n`{CARD_NUMBER}`", parse_mode="Markdown")
        elif state == "waiting_withdraw_amount":
            user_states.pop(user_id, None)
            bot.reply_to(message, "✅ درخواست برداشت ثبت شد.")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ تأیید", callback_data=f"adm_w_yes_{user_id}_{text}"), types.InlineKeyboardButton("❌ رد", callback_data=f"adm_w_no_{user_id}"))
            bot.send_message(ADMIN_ID, f"🔔 برداشت جدید از @{username}\nمبلغ: {text}", reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].startswith("waiting_receipt_"):
        amount_str = user_states[user_id].split("_")[2]
        user_states.pop(user_id, None)
        file_id = message.photo[-1].file_id
        bot.reply_to(message, "⏳ رسید ارسال شد.")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تأیید", callback_data=f"adm_d_yes_{user_id}_{amount_str}"), types.InlineKeyboardButton("❌ رد", callback_data=f"adm_d_no_{user_id}"))
        bot.send_photo(ADMIN_ID, file_id, caption=f"🔔 رسید شارژ از کاربر `{user_id}`\nمبلغ: {amount_str}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    user_id = call.from_user.id
    if data.startswith("game_"):
        parts = data.split("_")
        if user_id != int(parts[1]):
            bot.answer_callback_query(call.id, "❌ مال شما نیست!", show_alert=True)
            return
        bet_val = int(parts[2])
        if random.random() > 0.5:
            win_val = int(bet_val * 1.5)
            update_balance(user_id, win_val)
            bot.answer_callback_query(call.id, f"برنده شدید! +{win_val:,}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"🎉 برنده شدید و {win_val:,} میو گرفتید.")
        else:
            bot.answer_callback_query(call.id, "باختید!", show_alert=True)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="💥 بمب منفجر شد و باختید.")
    elif data.startswith("adm_d_yes_"):
        parts = data.split("_")
        target = int(parts[3])
        amt = parse_amount(parts[4])
        update_balance(target, amt)
        bot.answer_callback_query(call.id, "تأیید شد")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ تأیید و واریز شد")
        bot.send_message(target, f"🎉 حساب شما به مبلغ {amt:,} میو شارژ شد.")
    elif data.startswith("adm_d_no_"):
        target = int(data.split("_")[3])
        bot.answer_callback_query(call.id, "رد شد")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ رد شد")
        bot.send_message(target, "❌ رسید شارژ شما رد شد.")
    elif data.startswith("adm_w_yes_"):
        target = int(data.split("_")[3])
        bot.answer_callback_query(call.id, "تأیید شد")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n✅ برداشت واریز شد")
        bot.send_message(target, "✅ درخواست برداشت شما واریز شد.")
    elif data.startswith("adm_w_no_"):
        target = int(data.split("_")[3])
        bot.answer_callback_query(call.id, "رد شد")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n❌ برداشت رد شد")
        bot.send_message(target, "❌ درخواست برداشت شما رد شد.")

if __name__ == "__main__":
    bot.infinity_polling()
