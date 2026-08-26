from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_setting, set_setting

router = Router()

# لیست کانال‌ها/گروه‌های اجباری در دیتابیس ذخیره میشه
# برای مدیریت توسط ادمین:
@router.message(F.text == "/admin_channels")
async def admin_channels_panel(message: Message):
    # اینجا می‌تونی چک کنی ادمین هست یا نه
    channels_str = await get_setting("forced_channels") or ""
    channels = channels_str.split(",") if channels_str else []
    
    text = "📢 **مدیریت جوین اجباری کانال/گروه**\n\nکانال‌های فعلی:\n"
    for ch in channels:
        if ch:
            text += f"• `{ch}`\n"
            
    text += "\nبرای افزودن بفرست: `/add_channel @username`\nبرای حذف بفرست: `/del_channel @username`"
    await message.reply(text, parse_mode="Markdown")

@router.message(F.text.startswith("/add_channel "))
async def add_forced_channel(message: Message):
    ch_username = message.text.replace("/add_channel", "").strip()
    channels_str = await get_setting("forced_channels") or ""
    channels = channels_str.split(",") if channels_str else []
    
    if ch_username not in channels:
        channels.append(ch_username)
        await set_setting("forced_channels", ",".join(channels))
        await message.reply(f"✅ کانال {ch_username} به لیست جوین اجباری اضافه شد.")
    else:
        await message.reply("⚠️ این کانال از قبل در لیست وجود دارد.")

@router.message(F.text.startswith("/del_channel "))
async def del_forced_channel(message: Message):
    ch_username = message.text.replace("/del_channel", "").strip()
    channels_str = await get_setting("forced_channels") or ""
    channels = channels_str.split(",") if channels_str else []
    
    if ch_username in channels:
        channels.remove(ch_username)
        await set_setting("forced_channels", ",".join(channels))
        await message.reply(f"🗑 کانال {ch_username} از لیست جوین اجباری حذف شد.")
    else:
        await message.reply("⚠️ این کانال در لیست یافت نشد.")
