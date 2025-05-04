from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
from database import Database
from components.states import CollectionStates

db = Database('film_bot.db')

async def show_collection_card(message: types.Message, state: FSMContext):
    """Показ карты из коллекции"""
    data = await state.get_data()
    cards = data['cards']
    current_index = data['current_index']
    current_rarity = data.get('current_rarity')
    
    if not cards:
        await message.answer("Ваша коллекция пуста")
        await state.clear()
        return

    card = cards[current_index]
    
    # Формируем информацию о карточке
    card_info = (
        f"Название: {card[1]}\n"
        f"Редкость: {card[4]}\n"
        f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}\n\n"
        f"{current_index + 1}/{len(cards)}"
    )
    
    # Создаем клавиатуру с навигацией
    keyboard = get_collection_keyboard(current_index, len(cards), current_rarity)

    try:
        await message.edit_media(
            types.InputMediaPhoto(
                media=card[2],
                caption=card_info
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        try:
            await message.answer_photo(
                photo=card[2],
                caption=card_info,
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Error showing collection card: {e}")

def get_collection_keyboard(current_index: int, total_cards: int, current_rarity: str = None):
    """Создание клавиатуры для просмотра коллекции"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️", callback_data="prev_card"),
            InlineKeyboardButton(text=f"{current_index + 1}/{total_cards}", callback_data="page_info"),
            InlineKeyboardButton(text="➡️", callback_data="next_card")
        ],
        [
            InlineKeyboardButton(text="🔄 Сортировка", callback_data="sort_cards")
        ]
    ]
    
    if current_rarity:
        keyboard.append([
            InlineKeyboardButton(text=f"📊 {current_rarity}", callback_data=f"rarity_{current_rarity}")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_rarity_keyboard():
    """Создание клавиатуры для сортировки по редкости"""
    keyboard = [
        [
            InlineKeyboardButton(text="Base", callback_data="rarity_Base"),
            InlineKeyboardButton(text="Medium", callback_data="rarity_Medium")
        ],
        [
            InlineKeyboardButton(text="Episode", callback_data="rarity_Episode"),
            InlineKeyboardButton(text="Muth", callback_data="rarity_Muth")
        ],
        [
            InlineKeyboardButton(text="Legendary", callback_data="rarity_Legendary"),
            InlineKeyboardButton(text="Limited", callback_data="rarity_Limited")
        ],
        [
            InlineKeyboardButton(text="Все карты", callback_data="rarity_all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_collection_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка навигации по коллекции"""
    try:
        current_state = await state.get_state()
        if current_state != CollectionStates.viewing:
            await callback.answer("Ошибка: неверное состояние")
            return

        data = await state.get_data()
        cards = data['cards']
        current_index = data['current_index']
        
        if callback.data == "prev_card":
            current_index = len(cards) - 1 if current_index == 0 else current_index - 1
        elif callback.data == "next_card":
            current_index = 0 if current_index == len(cards) - 1 else current_index + 1
        elif callback.data == "sort_cards":
            await callback.message.answer(
                "Выберите редкость для сортировки:",
                reply_markup=get_rarity_keyboard()
            )
            await callback.answer()
            return
        elif callback.data == "page_info":
            await callback.answer()
            return
        
        await state.update_data(current_index=current_index)
        await show_collection_card(callback.message, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in collection navigation: {e}")
        await callback.answer("Произошла ошибка при навигации") 