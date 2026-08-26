# -*- coding: utf-8 -*-
import telebot
from config import TOKEN, get_user_balance
from poop_game import register_poop_handler

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ثبت هندلر بازی پوپ
register_poop_handler(bot)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    bal = get_user_balance(user_id)
    bot.reply_to(message, f"سلام! خوش آمدید به ربات میوبی 🐱\nموجودی شما: {bal:,} میو\nبرای بازی پوپ بنویسید: پوپ 10k")

print("Bot is running...")
bot.infinity_polling(skip_pending=True)
