# -*- coding: utf-8 -*-
import sqlite3

# توکن ربات شما
TOKEN = "8807018385:AAH0BJOhINR_TqpU0i_3b29QGWOlL5QUL2M"

MIN_BET = 1000
MAX_BET = 10000000

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

def add_user_if_not_exists(user_id, username):
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, 10000)", (user_id, username))
        conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def parse_amount(text):
    text = text.lower().strip()
    if text.endswith('k'):
        return int(float(text[:-1]) * 1000)
    elif text.endswith('m'):
        return int(float(text[:-1]) * 1000000)
    return int(text)

def get_poop_multipliers():
    return [1.2, 1.3, 1.5, 2.0, 2.5]
