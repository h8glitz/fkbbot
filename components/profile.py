from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
from datetime import datetime
import logging

db = Database('film_bot.db')

async def show_profile(callback: types.CallbackQuery):
    """Показ профиля пользователя"""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    if user:
        # Форматируем дату окончания пасса
        pass_expiry_str = user[7]
        pass_expiry_dt = None
        if pass_expiry_str:
            try:
                pass_expiry_dt = datetime.strptime(pass_expiry_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logging.error(f"Invalid pass date format for user {user_id}: {pass_expiry_str}")
        pass_date = pass_expiry_dt.strftime('%d.%m.%Y') if pass_expiry_dt else 'Нет'
        
        # Получаем статистику Dice
        dice_stats = db.get_dice_stats(user_id)
        if dice_stats:
            count_games, win, loss = dice_stats
        else:
            count_games, win, loss = 0, 0, 0
            
        # Рассчитываем процент побед
        if count_games > 0:
            win_rate = round((win / count_games) * 100)
        else:
            win_rate = 0
        win_rate_str = f"{win_rate}%"
        
        profile_text = (
            f"👤 {callback.from_user.username or 'Без имени'}\n\n"
            f"💎 Очки в этом сезоне: {user[9]}\n"
            f"💫 Всего очков: {user[3]}\n"
            f"🎫 Pass до: {pass_date}\n"
            f"⏰ Попытки: {user[8] if user[8] != -1 else '🚫 Забанен'}\n"
            f"💰 Донат: {user[6]}\n" # Индекс 12 для donate_balance
        )
        
        dice_stats_text = (
            f"\n🎲 Dice\n"
            f"• Побед: {win}\n"
            f"• Поражений: {loss}\n"
            f"• Процент побед: {win_rate_str}"
        )
        
        profile_text += dice_stats_text
        
        await callback.message.answer(profile_text) 