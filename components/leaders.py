from aiogram import types, Bot
import sqlite3

async def show_leaderboard(callback: types.CallbackQuery, bot: Bot):
    """Показ таблицы лидеров"""
    conn = sqlite3.connect('film_bot.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10')
    leaders = cur.fetchall()
    conn.close()
    
    leaderboard = "🏆 Таблица лидеров FKB за всё время:\n\n"
    for i, (leader_id, points) in enumerate(leaders, 1):
        try:
            user_info = await bot.get_chat(leader_id)
            username = user_info.username or user_info.first_name
            leaderboard += f"{i}. {username}: {points} очков\n"
        except:
            continue
    
    await callback.message.answer(leaderboard) 