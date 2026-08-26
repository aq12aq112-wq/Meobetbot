import telebot
from telebot import types
import sqlite3
import random
from config import BOT_TOKEN, ADMIN_ID, CARD_NUMBER, MIN_DEPOSIT

bot = telebot.TeleBot(BOT_TOKEN)

# راه‌اندازی دیتابیس
def init_db():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 10000
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user(user_id, username=""):
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
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
    username = message.from_user.username || message.from_user.first_name || "کاربر"
    balance = get_user(user_id, username)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💰 موجودی من", "💳 شارژ حساب")
    markup.add("📈 ترید", "🦋 برداشت وجه")
    markup.add("📖 راهنمای ربات", "➕ افزودن به گروه")
    if user_id == ADMIN_ID:
        markup.add("⚙️ پنل مدیریت")

    text = (
        f"🐱 **Meowbet | میوبنت** 🎰\n\n"
        f"👤 کاربر: @{username}\n"
        f"💳 موجودی شما: **{balance:,} میو**\n\n"
        f"🎮 **بازی‌های فعال در گروه و پی‌وی:**\n"
        f"• 💎 پوپ: `پوپ [مبلغ]` (مثال: `پوپ 50k`)\n"
        f"• 📦 مین: `مین [مبلغ]`\n"
        f"• 🎲 تاس: `#زوج [مبلغ]` یا `#فرد [مبلغ]`"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text and ("مین" in message.text || "پوپ" in message.text))
def handle_min_poop(message):
    user_id = message.from_user.id
    username = message.from_user.username || message.from_user.first_name
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
    game_text = (
        f"🐱 **Meowbet** | میوبنت 🎰\n"
        f"👤 @{username}\n\n"
        f"🎰 بازی: {game_type}\n"
        f"💲 شرط: **{bet:,} میو**\n\n"
        f"👇 برای شروع یک خانه انتخاب کنید:"
    )
    bot.send_message(message.chat.id, game_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text and (message.text.startswith("#زوج") || message.text.startswith("#فرد")))
def handle_dice(message):
    user_id = message.from_user.id
    username = message.from_user.username || message.from_user.first_name
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
    user_won = (choice == "زوج" and is_even) || (choice == "فرد" and not is_even)

    if user_won:
        win_amount = bet * 2
        update_balance(user_id, win_amount)
        result_text = f"🎉 تاس آمد: {dice_result} ({'زوج' if is_even else 'فرد'})\n✨ برنده شدید! جایزه: {win_amount:,} میو"
    else:
        result_text = f"😢 تاس آمد: {dice_result} ({'زوج' if is_even else 'فرد'})\n💥 باختید!"

    bot.reply_to(message, f"🎲 **نتیجه تاس زوج/فرد**\n\nانتخاب شما: {choice} | مبلغ: {bet:,}\n\n{result_text}", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    user_id = message.from_user.id
    username = message.from_user.username || message.from_user.first_name
    balance = get_user(user_id, username)

    if text == "💰 موجودی من":
        bot.reply_to(message, f"💳 موجودی فعلی حساب شما: **{balance:,} میو**", parse_mode="Markdown")
    
    elif text == "📖 راهنمای ربات":
        guide_text = (
            "📖 **راهنمای جامع ربات میوبنت (Meowie Bet)**\n\n"
            "💎 **بازی پوپ:** دستور `پوپ [مبلغ]` (مثال: `پوپ 50k`)\n"
            "📦 **بازی مین:** دستور `مین [مبلغ]`\n"
            "🎲 **تاس زوج/فرد:** دستور `#زوج [مبلغ]` یا `#فرد [مبلغ]`\n"
            "📈 **بخش ترید:** پیش‌بینی صعودی و نزولی سریع.\n"
            "💳 **شارژ حساب:** حداقل مبلغ ۵۰ هزار تومان از طریق کارت به کارت."
        )
        bot.reply_to(message, guide_text, parse_mode="Markdown")
    
    elif text == "📈 ترید":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📈 صعودی (Green)", callback_data="trade_up"),
            types.InlineKeyboardButton("📉 نزولی (Red)", callback_data="trade_down")
        )
        bot.reply_to(message, "📈 **بخش ترید سریع**\n\nجهت بازار را پیش‌بینی کنید:", reply_markup=markup, parse_mode="Markdown")
    
    elif text == "💳 شارژ حساب":
        user_states[user_id] = "waiting_deposit_amount"
        bot.reply_to(message, f"💳 **شارژ حساب کاربری**\n\nحداقل مبلغ شارژ **50k** (۵۰,۰۰۰ میو) است.\nلطفاً مبلغ مورد نظر خود را ارسال کنید:", parse_mode="Markdown")
    
    elif text == "🦋 برداشت وجه":
        user_states[user_id] = "waiting_withdraw_amount"
        bot.reply_to(message, f"🦋 **برداشت از حساب**\n\nموجودی شما: {balance:,} میو\nمبلغ درخواستی برای برداشت را بفرستید:", parse_mode="Markdown")
    
    elif text == "⚙️ پنل مدیریت" and user_id == ADMIN_ID:
        bot.reply_to(message, "🛠 **خوش آمدید به پنل مدیریت پیشرفته ربات**\nدرخواست‌های شارژ و برداشت کاربران اینجا مدیریت می‌شوند.", parse_mode="Markdown")
    
    elif text == "➕ افزودن به گروه":
        bot.reply_to(message, f"برای افزودن ربات به گروه روی لینک زیر کلیک کنید:\nhttps://t.me/{bot.get_me().username}?startgroup=true")
    
    elif user_id in user_states:
        state = user_states[user_id]
        if state == "waiting_deposit_amount":
            user_states[user_id] = f"waiting_receipt_{text}"
            bot.reply_to(message, 
                f"✅ مبلغ **{text}** ثبت شد.\n\n"
                f"لطفاً مبلغ را به کارت زیر واریز کنید و **عکس رسید** را بفرستید:\n\n"
                f"💳 `{CARD_NUMBER}`", parse_mode="Markdown"
            )
        elif state == "waiting_withdraw_amount":
            user_states.pop(user_id, None)
            bot.reply_to(message, "✅ درخواست برداشت شما ثبت شد و برای ادمین ارسال گردید.")
            
            admin_msg = f"🔔 **درخواست برداشت جدید!**\n\n👤 کاربر: @{username} (`{user_id}`)\n💰 مبلغ: **{text}**"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ تأیید", callback_data=f"adm_w_yes_{user_id}_{text}"),
                types.InlineKeyboardButton("❌ رد", callback_data=f"adm_w_no_{user_id}")
            )
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    username = message.from_user.username || message.from_user.first_name
    
    if user_id in user_states and user_states[user_id].startswith("waiting_receipt_"):
        amount_str = user_states[user_id].split("_")[2]
        user_states.pop(user_id, None)
        
        file_id = message.photo[-1].file_id
        bot.reply_to(message, "⏳ رسید دریافت شد و برای ادمین ارسال گردید.")
        
        admin_text = f"🔔 **رسید شارژ جدید!**\n\n👤 کاربر: @{username} (`{user_id}`)\n💵 مبلغ: **{amount_str}**"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تأیید و شارژ", callback_data=f"adm_d_yes_{user_id}_{amount_str}"),
            types.InlineKeyboardButton("❌ رد رسید", callback_data=f"adm_d_no_{user_id}")
        )
        bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    user_id = call.from_user.id
    
    if data.startswith("game_"):
        parts = data.split("_")
        target_user = int(parts[1])
        bet_val = int(parts[2])
        if user_id != target_user:
            bot.answer_callback_query(call.id, "❌ این بازی متعلق به شما نیست!", show_alert=True)
            return
        
        if "💎" in call.message.text || random.random() > 0.5:
            win_val = int(bet_val * 1.5)
            update_balance(user_id, win_val)
            bot.answer_callback_query(call.id, f"💎 الماس پیدا کردید! +{win_val:,} میو")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"🎉 تبریک! شما برنده شدید و {win_val:,} میو گرفتید.")
        else:
            bot.answer_callback_query(call.id, "💥 بمب منفجر شد! باختید.", show_alert=True)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="💥 بمب منفجر شد! باختید.")

    elif data.startswith("trade_"):
        bot.answer_callback_query(call.id, "نتیجه ترید ثبت شد!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📈 نتیجه ترید: بازار به نفع شما حرکت کرد و سود کردید! 🟢")

    elif data.startswith("adm_d_yes_"):
        parts = data.split("_")
        target_user = int(parts[3])
        amount_str = parts[4]
        num_amount = parse_amount(amount_str)
                
        update_balance(target_user, num_amount)
        bot.answer_callback_query(call.id, "تأیید شد!")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **وضعیت: تأیید و واریز شد**", parse_mode="Markdown")
        bot.send_message(target_user, f"🎉 حساب شما به مبلغ **{num_amount:,} میو** شارژ شد!", parse_mode="Markdown")
        
    elif data.startswith("adm_d_no_"):
        target_user = int(data.split("_")[3])
        bot.answer_callback_query(call.id, "رد شد!")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **وضعیت: رد شد**", parse_mode="Markdown")
        bot.send_message(target_user, "❌ رسید شارژ شما توسط ادمین رد شد.")

    elif data.startswith("adm_w_yes_"):
        target_user = int(data.split("_")[3])
        bot.answer_callback_query(call.id, "برداشت تأیید شد!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n✅ **وضعیت: برداشت واریز شد**", parse_mode="Markdown")
        bot.send_message(target_user, "✅ درخواست برداشت وجه شما تأیید و واریز گردید.")

    elif data.startswith("adm_w_no_"):
        target_user = int(data.split("_")[3])
        bot.answer_callback_query(call.id, "برداشت رد شد!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text + "\n\n❌ **وضعیت: برداشت رد شد**", parse_mode="Markdown")
        bot.send_message(target_user, "❌ درخواست برداشت شما توسط ادمین رد شد.")

if __name__ == "__main__":
    print("Bot is running perfectly...")
    bot.infinity_polling()
