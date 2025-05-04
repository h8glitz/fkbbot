from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
import random
from database import Database
from components.states import RandomCardStates

db = Database('film_bot.db')

async def start_random_card(callback: types.CallbackQuery, state: FSMContext):
    """Начало получения случайной карты"""
    await state.set_state(RandomCardStates.waiting_for_roll)
    
    # Создаем клавиатуру для броска
    keyboard = [[InlineKeyboardButton(text="🎲 Бросить кости", callback_data="roll_random_card")]]
    
    await callback.message.answer(
        "🎲 Бросьте кости и получите случайную карту!\n"
        "Чем больше выпавшее число, тем выше шанс получить редкую карту!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def handle_random_card_roll(callback: types.CallbackQuery, state: FSMContext):
    """Обработка броска костей для получения случайной карты"""
    dice_msg = await callback.message.answer_dice(emoji="🎲")
    roll_value = dice_msg.dice.value
    
    # Определяем редкость карты на основе выпавшего числа
    rarity = "Обычная"
    if roll_value >= 5:
        rarity = "Редкая"
    elif roll_value >= 3:
        rarity = "Необычная"
    
    # Получаем случайную карту выбранной редкости
    card = db.get_random_card_by_rarity(rarity)
    
    if not card:
        await callback.message.answer("К сожалению, карта выбранной редкости не найдена")
        await state.clear()
        return
    
    # Добавляем карту пользователю
    try:
        db.add_card_to_user(callback.from_user.id, card[0])
        
        # Формируем сообщение о полученной карте
        card_info = (
            f"🎉 Поздравляем! Вы получили карту:\n\n"
            f"Название: {card[1]}\n"
            f"Редкость: {card[4]}\n"
            f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}"
        )
        
        # Отправляем фото карты
        await callback.message.answer_photo(
            photo=card[2],
            caption=card_info
        )
        
    except Exception as e:
        logging.error(f"Error during random card roll: {e}")
        await callback.message.answer("Произошла ошибка при получении карты")
    
    await state.clear() 