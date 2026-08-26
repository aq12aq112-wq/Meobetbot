from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text.in_({"راهنما", "/help", "❓ راهنما"}))
async def show_help_menu(message: Message):
    help_text = (
        "「 🐱 **میوبت | MEOWBET** 🎰 」\n\n"
        
        "🎲 **بازی تاس (۳ تایی):**\n"
        "• دستورات: `زوج [مبلغ]` یا `فرد [مبلغ]` (مثلاً: `زوج 50کی`)\n"
        "• بعد از ثبت شرط، ۳ تاس پشت سر هم داخل گروه بفرستید (ضریب: `1.5x`).\n\n"
        
        "💩 **بازی پوپ:**\n"
        "• دستور: `#پوپ [مبلغ]` (مثلاً: `#پوپ 100کی`)\n"
        "• ضرایب ۵ مرحله‌ای: `1.2x` ← `1.4x` ← `1.6x` ← `2.0x` ← `2.5x`\n\n"
        
        "💣 **بازی مین:**\n"
        "• دستور: `مین [مبلغ]` (پیدا کردن خانه‌های امن در جدول ۳ در ۳)\n\n"
        "🎯 **راهنمای عمومی:**\n"
        "• 💰 **موجودی** / 💳 **شارژ** / 💸 **برداشت**"
    )
    await message.reply(help_text, parse_mode="Markdown")
