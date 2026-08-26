# -*- coding: utf-8 -*-
from telebot import types
import random
from config import add_user_if_not_exists, get_user_balance, update_balance, parse_amount, MIN_BET, MAX_BET, get_poop_multipliers

active_tower_games = {}
POOP_COUNTS = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3}
MULTIPLIERS = [1.2, 1.3, 1.5, 2.0, 2.5]

def register_poop_handler(bot):
    @bot.message_handler(func=lambda msg: msg.text and (msg.text.lower().startswith("پوپ") or msg.text.startswith("/poop")))
    def start_tower(message):
        global active_tower_games
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        add_user_if_not_exists(user_id, username)

        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ مثال: <code>پوپ 50k</code>")
            return
        amount = parse_amount(parts[1])
        current_bal = get_user_balance(user_id)

        if amount < MIN_BET or amount > MAX_BET or current_bal < amount:
            bot.reply_to(message, f"❌ موجودی کافی نیست!\nموجودی: {current_bal:,} میو")
            return

        update_balance(user_id, -amount)

        poops = []
        for r in range(5):
            p_count = POOP_COUNTS[r]
            row_p = [1]*p_count + [0]*(5 - p_count)
            random.shuffle(row_p)
            poops.append(row_p)

        mults = get_poop_multipliers()
        active_tower_games[user_id] = {
            'user_id': user_id,
            'username': username,
            'amount': amount,
            'poops': poops,
            'revealed': [[False]*5 for _ in range(5)],
            'current_row': 0,
            'lost': False,
            'won': False
        }

        kb = build_tower_board(active_tower_games[user_id])
        text = (
            f"Meowie bet🐱\n"
            f"👤 {username} 🐾\n\n"
            f"💩 پوپ 🎰\n"
            f"🎮 مرحله: 1 از 5 (ضریب: {mults[0]}x)\n"
            f"💲 شرط: {amount:,} میو\n"
            f"📈 جایزه فعلی: {amount:,} میو"
        )
        bot.reply_to(message, text, reply_markup=kb)

def build_tower_board(game, show_all=False):
    mults = get_poop_multipliers()
    kb = types.InlineKeyboardMarkup(row_width=5)
    for r in range(4, -1, -1):
        row_btns = []
        for c in range(5):
            if show_all or game['lost'] or game['won']:
                sym = "💩" if game['poops'][r][c] == 1 else "🟢"
                row_btns.append(types.InlineKeyboardButton(sym, callback_data="none"))
            elif game['revealed'][r][c]:
                row_btns.append(types.InlineKeyboardButton("🟢", callback_data="none"))
            elif r == game['current_row']:
                row_btns.append(types.InlineKeyboardButton("⚪", callback_data=f"tower_sel_{game['user_id']}_{r}_{c}"))
            else:
                row_btns.append(types.InlineKeyboardButton("🔒", callback_data="none"))
        kb.row(*row_btns)

    if not show_all and not game['lost'] and not game['won'] and game['current_row'] > 0:
        prev_mult = mults[game['current_row'] - 1]
        prize = int(game['amount'] * prev_mult)
        kb.row(types.InlineKeyboardButton(f"💵 برداشت ({prize:,} میو)", callback_data=f"tower_cash_{game['user_id']}"))
    return kb
