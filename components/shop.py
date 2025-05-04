from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database

db = Database('film_bot.db')

# Словарь с очками за карты разных редкостей
CARD_POINTS = {
    'Base': 250,
    'Medium': 350,
    'Episode': 500,
    'Muth': 1500,
    'Legendary': 3000,
    'Limited': 10000
}

async def show_shop(callback: types.CallbackQuery):
    """Показ магазина фильмов"""
    shop_text = (
        "🎬 Магазин фильмов\n\n"
        "Здесь вы можете обменять свои очки на карты\n"
        "Выберите категорию:"
    )
    await callback.message.answer(shop_text, reply_markup=get_shop_keyboard())

def get_shop_keyboard():
    """Создание клавиатуры для магазина"""
    keyboard = [
        [
            InlineKeyboardButton(text="Base (250)", callback_data="shop_base"),
            InlineKeyboardButton(text="Medium (350)", callback_data="shop_medium")
        ],
        [
            InlineKeyboardButton(text="Episode (500)", callback_data="shop_episode"),
            InlineKeyboardButton(text="Muth (1500)", callback_data="shop_muth")
        ],
        [
            InlineKeyboardButton(text="Legendary (3000)", callback_data="shop_legendary")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_shop_purchase(callback: types.CallbackQuery):
    """Обработка покупки в магазине"""
    rarity = callback.data.replace("shop_", "").capitalize()
    user = db.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        return
        
    cost = CARD_POINTS.get(rarity)
    if not cost:
        await callback.answer("Ошибка: неверная категория")
        return
        
    if user[3] < cost:  # shop_points
        await callback.answer(f"Недостаточно очков. Нужно: {cost}")
        return
        
    # Здесь логика покупки карты
    # TODO: Реализовать покупку карты
    await callback.answer("Функция в разработке") 