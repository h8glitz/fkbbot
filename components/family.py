from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from database import Database

db = Database('film_bot.db')

async def show_family_info(callback: types.CallbackQuery):
    """Показ информации о семье пользователя"""
    user = db.get_user(callback.from_user.id)
    
    if user and user[4]:  # Если у пользователя есть семья
        conn = sqlite3.connect('film_bot.db')
        cur = conn.cursor()
        cur.execute('SELECT * FROM family WHERE leader_id = ?', (user[4],))
        family = cur.fetchone()
        conn.close()
        
        if family:
            house_text = (
                f"🏠 Ваш дом\n\n"
                f"👥 Члены семьи: {family[1]}\n"
                f"💎 Очки семьи: {family[2]}\n"
            )
            await callback.message.answer(house_text)
        else:
            await callback.message.answer("У вас пока нет дома")
    else:
        await callback.message.answer("Сначала вступите в семью")

def get_family_keyboard():
    """Создание клавиатуры для меню семьи"""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Члены семьи", callback_data="family_members"),
            InlineKeyboardButton(text="💎 Очки семьи", callback_data="family_points")
        ],
        [
            InlineKeyboardButton(text="➕ Пригласить", callback_data="family_invite"),
            InlineKeyboardButton(text="❌ Покинуть", callback_data="family_leave")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 