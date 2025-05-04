from aiogram import types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import asyncio
import logging
from config import TOKEN
from database import Database
from components.states import AddCard, AdminStates, CollectionStates, TradeStates, DiceStates, FamilyStates
from components.admin import *
from components.collection import show_collection_card, handle_collection_navigation
from components.cards import get_card, start_notification_checker
from components.trade import *
from components.dice import *
from components.shop import *
from components.profile import show_profile
import datetime
import random
import sqlite3
from dispatcher import dp, bot  # Импортируем из нового файла

# Импорт компонентов
from components.family import show_family_info
from components.leaders import show_leaderboard
from components.random_card import start_random_card, handle_random_card_roll
from components.dice import (
    handle_dice_navigation, handle_dice_card_selection,
    handle_dice_username_input, handle_dice_response,
    handle_dice_response_card_selection, handle_first_roll,
    handle_second_roll, cancel_dice
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
db = Database('film_bot.db')

# Создание основной клавиатуры
def get_keyboard():
    keyboard = [
        [
            KeyboardButton(text="📸 Получить карту"),
            KeyboardButton(text="🎬 Мой фильмстрип")
        ],
        [KeyboardButton(text="☰ Меню")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="☰ Выберите действие"
    )

# Создание inline-меню
def get_inline_menu():
    keyboard = [
        [
            InlineKeyboardButton(text="👑 Leaders", callback_data="leaders"),
            InlineKeyboardButton(text="🪪 Profile", callback_data="profile")
        ],
        [
            InlineKeyboardButton(text="🎞️ House", callback_data="house"),
            InlineKeyboardButton(text="🎬 Movie Shop", callback_data="movie_shop")
        ],
        [
            InlineKeyboardButton(text="🎭 Trade", callback_data="trade"),
            InlineKeyboardButton(text="🎫 Film Pass", callback_data="film_pass")
        ],
        [
            InlineKeyboardButton(text="🎲 Dice", callback_data="dice"),
            InlineKeyboardButton(text="🎰 Casino 🎰", callback_data="casino")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    # Добавляем пользователя в базу данных
    db.add_user(message.from_user.id)
    # Обновляем username
    if message.from_user.username:
        db.update_username(message.from_user.id, message.from_user.username)
    
    await message.answer(
        "Добро пожаловать! Выберите действие:",
        reply_markup=get_keyboard()
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Обработчик команды /admin"""
    if db.is_admin(message.from_user.id):
        await message.answer(
            "Панель администратора:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("У вас нет доступа к панели администратора.")

@dp.message(Command("recreate_db"))
async def cmd_recreate_db(message: types.Message):
    """Обработчик команды /recreate_db"""
    if db.is_admin(message.from_user.id):
        await message.answer("Начинаю пересоздание базы данных...")
        db.recreate_database()
        await message.answer("База данных успешно пересоздана!")
    else:
        await message.answer("У вас нет доступа к этой команде.")

@dp.message()
async def handle_message(message: types.Message, state: FSMContext):
    """Обработчик текстовых сообщений"""
    current_state = await state.get_state()
    logging.info(f"Received message: {message.text}, current state: {current_state}")
    
    if current_state == TradeStates.waiting_for_username:
        await handle_username_input(message, state)
        return
    elif current_state == DiceStates.waiting_for_username:
        await handle_dice_username_input(message, state)
        return
    elif current_state == AdminStates.waiting_for_pass_user_id:
        await process_pass_user_id(message, state)
        return
    elif current_state == AdminStates.waiting_for_pass_months:
        await process_pass_months(message, state)
        return
    elif current_state == AdminStates.waiting_for_donate_user_id:
        await process_donate_user_id(message, state)
        return
    elif current_state == AdminStates.waiting_for_donate_amount:
        await process_donate_amount(message, state)
        return
    elif current_state == FamilyStates.waiting_for_name:
        await process_family_name(message, state)
        return
    elif current_state == FamilyStates.waiting_for_avatar:
        await process_family_avatar(message, state)
        return
    elif current_state == FamilyStates.waiting_for_description:
        await process_family_description(message, state)
        return
    elif current_state == FamilyStates.waiting_for_invite_username:
        await process_invite_username(message, state)
        return
    elif current_state == AddCard.waiting_for_name:
        await process_name(message, state)
        return
    elif current_state == AddCard.waiting_for_photo:
        await process_photo(message, state)
        return
    elif current_state == AddCard.waiting_for_limited:
        await process_limited(message, state)
        return
    elif current_state == AddCard.waiting_for_rare:
        await process_rare(message, state)
        return
    elif current_state == AddCard.waiting_for_points:
        await process_points(message, state)
        return
    elif current_state == AddCard.waiting_for_price:
        await process_price(message, state)
        return
    elif current_state == AddCard.waiting_for_counts:
        await process_counts(message, state)
        return
    elif current_state == AdminStates.waiting_for_user_id:
        await process_user_id_for_attempts(message, state)
        return
    elif current_state == AdminStates.waiting_for_attempts:
        await process_attempts_count(message, state)
        return
    elif current_state == AdminStates.waiting_for_ban_user_id:
        await process_ban_user_id(message, state)
        return
    elif current_state == AdminStates.waiting_for_unban_user_id:
        await process_unban_user_id(message, state)
        return
    
    if message.text == "📸 Получить карту":
        await get_card(message)
    elif message.text == "🎬 Мой фильмстрип":
        user = db.get_user(message.from_user.id)
        if not user:
            await message.answer("Ошибка: пользователь не найден")
            return
        
        cards = db.get_user_cards(message.from_user.id)
        if not cards:
            await message.answer("Ваша коллекция пуста")
            return

        await state.set_state(CollectionStates.viewing)
        await state.update_data(
            cards=cards,
            current_index=0,
            current_rarity=None
        )

        await show_collection_card(message, state)
    elif message.text == "☰ Меню":
        await message.answer(
            "Выберите действие в меню:",
            reply_markup=get_inline_menu()
        )
    elif message.text.isdigit() and db.is_admin(message.from_user.id):
        # Поиск карты по ID
        card = db.get_card(int(message.text))
        if card:
            card_info = (
                f"ID: {card[0]}\n"
                f"Название: {card[1]}\n"
                f"Редкость: {card[4]}\n"
                f"Очки: {card[5]}\n"
                f"Цена: {card[6]}\n"
                f"Counts: {card[7]}\n"
                f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}"
            )
            await message.answer_photo(
                photo=card[2],
                caption=card_info
            )
        else:
            await message.answer("Карта не найдена")

# Регистрация обработчиков админ-функций
@dp.callback_query(lambda c: c.data == "add_card")
async def add_card_callback(callback: types.CallbackQuery, state: FSMContext):
    await process_add_card(callback, state)

@dp.callback_query(lambda c: c.data == "list_cards")
async def list_cards_callback(callback: types.CallbackQuery):
    await process_list_cards(callback)

@dp.callback_query(lambda c: c.data == "find_card")
async def find_card_callback(callback: types.CallbackQuery):
    await process_find_card(callback)

@dp.callback_query(lambda c: c.data == "add_attempts")
async def add_attempts_callback(callback: types.CallbackQuery, state: FSMContext):
    await process_add_attempts(callback, state)

@dp.callback_query(lambda c: c.data == "ban_user")
async def ban_user_callback(callback: types.CallbackQuery, state: FSMContext):
    await process_ban_user(callback, state)

@dp.callback_query(lambda c: c.data == "unban_user")
async def unban_user_callback(callback: types.CallbackQuery, state: FSMContext):
    await process_unban_user(callback, state)


@dp.callback_query(lambda c: c.data.startswith('confirm_trade_'))
async def confirm_trade_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_trade_confirmation(callback, state)


# Регистрация обработчиков навигации по коллекции
@dp.callback_query(lambda c: c.data in ["prev_card", "next_card", "sort_cards", "page_info"])
async def collection_navigation(callback: types.CallbackQuery, state: FSMContext):
    await handle_collection_navigation(callback, state)

# Регистрация обработчиков других функций
@dp.callback_query(lambda c: c.data.startswith("shop_"))
async def shop_purchase_callback(callback: types.CallbackQuery):
    await handle_shop_purchase(callback)

@dp.callback_query(lambda c: c.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    await show_profile(callback)

@dp.callback_query(lambda c: c.data == "leaders")
async def leaders_callback(callback: types.CallbackQuery):
    await show_leaderboard(callback, bot)

@dp.callback_query(lambda c: c.data == "trade")
async def trade_callback(callback: types.CallbackQuery, state: FSMContext):
    await start_trade(callback, state)

@dp.callback_query(lambda c: c.data.startswith("trade_select_"))
async def trade_select_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_card_selection(callback, state)

@dp.callback_query(lambda c: c.data in ["trade_prev", "trade_next", "trade_info"])
async def trade_navigation_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_trade_navigation(callback, state)

@dp.callback_query(lambda c: c.data.startswith(("accept_trade_", "reject_trade_")))
async def trade_response_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_trade_response(callback, state)

@dp.callback_query(lambda c: c.data.startswith("respond_select_"))
async def respond_select_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_response_card_selection(callback, state)

@dp.callback_query(lambda c: c.data == "cancel_trade")
async def cancel_trade_callback(callback: types.CallbackQuery, state: FSMContext):
    await cancel_trade(callback, state)

@dp.callback_query(lambda c: c.data.startswith(("confirm_trade_", "reject_trade_")))
async def trade_confirmation_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_trade_confirmation(callback, state)

@dp.callback_query(lambda c: c.data == "film_pass")
async def film_pass_callback(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    if db.has_active_pass(callback.from_user.id):
        # Если у пользователя есть активный пасс
        keyboard = [
            [InlineKeyboardButton(text="🎲 Бросить кубик", callback_data="roll_dice")],
            [InlineKeyboardButton(text="🎰 Получить легендарную карту", callback_data="get_legendary_card")]
        ]
        await callback.message.answer(
            "🎫 У вас активный Film Pass!\n\n"
            "Ваши привилегии:\n"
            "• Уведомление о следующей попытке\n"
            "• 2 часа ожидания следующей карты\n"
            "• 🎲 Кубик можно кидать 2 раза в месяц\n"
            "• 🎰 Раз в неделю получаете легендарную карту\n"
            "• Возможность создать свою 🎞️Гильдию\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        # Если у пользователя нет пасса
        keyboard = [
            [InlineKeyboardButton(text="Купить Pass", callback_data="buy_pass")]
        ]
        await callback.message.answer(
            "📹💭 Режиссер, давай расскажу тебе о 🎫 Film Pass. Film Pass - это уникальный пропуск для развития в игре, вот его плюсы:\n\n"
            "• Уведомление о следующей попытке\n"
            "• 2 часа ожидания следующей карты\n"
            "• 🎲 Кубик можно кидать 2 раза в месяц\n"
            "• 🎰 Раз в неделю получаете легендарную карту\n"
            "• Возможность создать свою 🎞️Гильдию\n\n"
            "Приобретите Film Pass, чтобы получить все преимущества!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@dp.callback_query(lambda c: c.data == "buy_pass")
async def buy_pass_callback(callback: types.CallbackQuery):
    """Обработчик кнопки 'Купить Pass'"""
    target_username = "SkyBro2"
    message_text = (
        f"Для приобретения 🎫 Film Pass, пожалуйста, свяжитесь с администратором: "
        f"[@{target_username}](https://t.me/{target_username})"
    )
    try:
        # Отправляем новое сообщение с ссылкой
        await callback.message.answer(
            message_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        # Подтверждаем нажатие кнопки (без текста уведомления)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in buy_pass_callback: {e}")
        await callback.answer("Произошла ошибка при обработке запроса.")

@dp.callback_query(lambda c: c.data == "get_legendary_card")
async def get_legendary_card_callback(callback: types.CallbackQuery):
    """Обработчик получения легендарной карты"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    if not db.has_active_pass(callback.from_user.id):
        await callback.message.answer("У вас нет активного Film Pass")
        return

    # Получаем текущую дату
    current_date = datetime.datetime.now()
    
    # Проверяем, является ли сегодня 15-м числом
    if current_date.day != 15:
        await callback.message.answer(
            "Легендарную карту можно получить только 15-го числа каждого месяца.\n"
            f"Следующая возможность будет {current_date.replace(day=15).strftime('%d.%m.%Y')}"
        )
        return

    # Получаем случайную легендарную карту
    card = db.get_random_card_by_rarity("Legendary")
    if not card:
        await callback.message.answer("К сожалению, сейчас нет доступных легендарных карт")
        return

    # Добавляем карту пользователю
    if db.add_card_to_user(callback.from_user.id, card[0]):
        await callback.message.answer_photo(
            photo=card[2],
            caption=f"🎉 Поздравляем! Вы получили легендарную карту:\n\n"
                   f"Название: {card[1]}\n"
                   f"Редкость: {card[4]}\n"
                   f"Очки: {card[5]}"
        )
    else:
        await callback.message.answer("Произошла ошибка при получении карты")

@dp.callback_query(lambda c: c.data == "dice")
async def dice_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки игры в кости"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    # Получаем карты пользователя
    cards = db.get_user_cards(callback.from_user.id)
    if not cards:
        await callback.message.answer("У вас нет карт для игры")
        return

    # Сохраняем состояние и показываем первую карту
    await state.set_state(DiceStates.selecting_card)
    await state.update_data(current_index=0)
    await show_card_for_dice(callback.message, callback.from_user.id, 0)

@dp.callback_query(lambda c: c.data == "roll_dice")
async def roll_dice_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик броска кубика для получения попыток"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    if not db.has_active_pass(callback.from_user.id):
        await callback.message.answer("Для броска кубика требуется Film Pass")
        return

    # Проверяем количество бросков за месяц
    rolls_count = db.get_dice_rolls_count(callback.from_user.id)
    logging.info(f"Current dice rolls count for user {callback.from_user.id}: {rolls_count}")
    
    if rolls_count >= 2:
        await callback.message.answer(
            "Вы уже использовали все 2 броска кубика за этот месяц.\n"
            "Следующая возможность будет доступна в следующем месяце."
        )
        return

    # Генерируем случайное число от 1 до 6
    dice_result = random.randint(1, 6)
    logging.info(f"Dice result for user {callback.from_user.id}: {dice_result}")
    
    # Отправляем анимацию броска кубика
    await callback.message.answer_dice(emoji="🎲")
    
    # Ждем 2 секунды для эффекта
    await asyncio.sleep(2)
    
    # Добавляем попытки в любом случае
    attempts_to_add = dice_result
    db.add_attempts(callback.from_user.id, attempts_to_add)
    logging.info(f"Added {attempts_to_add} attempts to user {callback.from_user.id}")
    
    # Увеличиваем счетчик бросков
    if not db.increment_dice_rolls(callback.from_user.id):
        logging.error(f"Failed to increment dice rolls for user {callback.from_user.id}")
        await callback.message.answer("Произошла ошибка при обновлении счетчика бросков")
        return
    
    # Отправляем результат
    remaining_rolls = 2 - (rolls_count + 1)
    await callback.message.answer(
        f"🎲 Выпало число: {dice_result}\n"
        f"🎉 Вам добавлено {attempts_to_add} попыток!\n\n"
        f"Осталось бросков в этом месяце: {remaining_rolls}"
    )

@dp.callback_query(lambda c: c.data == "casino")
async def casino_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки казино"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    # Проверяем баланс доната
    donate_balance = db.get_user_donate(callback.from_user.id)
    
    keyboard = [
        [
            InlineKeyboardButton(text="🏀 Баскетбол", callback_data="casino_basketball"),
            InlineKeyboardButton(text="⚽ Футбол", callback_data="casino_football")
        ],
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data="casino_slots")
        ]
    ]
    
    await callback.message.answer(
        f"🎰 Добро пожаловать в казино!\n\n"
        f"💰 Ваш баланс доната: {donate_balance}\n\n"
        "Выберите игру:\n"
        "• 🏀 Баскетбол - 25 донат\n"
        "• ⚽ Футбол - 25 донат\n"
        "• 🎰 Слоты - 25 донат\n\n"
        "Приз за победу: 10 попыток!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data == "casino_basketball")
async def casino_basketball_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик игры в баскетбол"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    # Проверяем баланс доната
    donate_balance = db.get_user_donate(callback.from_user.id)
    if donate_balance < 25:
        await callback.message.answer(
            "❌ Недостаточно доната!\n"
            f"Ваш баланс: {donate_balance}\n"
            "Требуется: 25"
        )
        return

    # Списываем донат
    if not db.remove_donate(callback.from_user.id, 25):
        await callback.message.answer("Произошла ошибка при списании доната")
        return

    # Отправляем анимацию баскетбола
    dice_msg = await callback.message.answer_dice(emoji="🏀")
    
    # Ждем завершения анимации
    await asyncio.sleep(4)
    
    # Проверяем результат
    result = dice_msg.dice.value
    if result in [4, 5]:
        db.add_attempts(callback.from_user.id, 10)
        await callback.message.answer(
            f"🎉 Поздравляем! Вы попали в корзину!\n"
            f"Вам начислено 10 попыток!"
        )
    else:
        await callback.message.answer(
            f"😔 К сожалению, вы не попали в корзину.\n"
            f"Попробуйте еще раз!"
        )

@dp.callback_query(lambda c: c.data == "casino_football")
async def casino_football_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик игры в футбол"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    # Проверяем баланс доната
    donate_balance = db.get_user_donate(callback.from_user.id)
    if donate_balance < 25:
        await callback.message.answer(
            "❌ Недостаточно доната!\n"
            f"Ваш баланс: {donate_balance}\n"
            "Требуется: 25"
        )
        return

    # Списываем донат
    if not db.remove_donate(callback.from_user.id, 25):
        await callback.message.answer("Произошла ошибка при списании доната")
        return

    # Отправляем анимацию футбола
    dice_msg = await callback.message.answer_dice(emoji="⚽")
    
    # Ждем завершения анимации
    await asyncio.sleep(4)
    
    # Проверяем результат
    result = dice_msg.dice.value
    if result in [4, 5]:
        db.add_attempts(callback.from_user.id, 10)
        await callback.message.answer(
            f"🎉 Поздравляем! Вы забили гол!\n"
            f"Вам начислено 10 попыток!"
        )
    else:
        await callback.message.answer(
            f"😔 К сожалению, вы не забили гол.\n"
            f"Попробуйте еще раз!"
        )

@dp.callback_query(lambda c: c.data == "casino_slots")
async def casino_slots_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик игры в слоты"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    # Проверяем баланс доната
    donate_balance = db.get_user_donate(callback.from_user.id)
    if donate_balance < 25:
        await callback.message.answer(
            "❌ Недостаточно доната!\n"
            f"Ваш баланс: {donate_balance}\n"
            "Требуется: 25"
        )
        return

    # Списываем донат
    if not db.remove_donate(callback.from_user.id, 25):
        await callback.message.answer("Произошла ошибка при списании доната")
        return

    # Отправляем анимацию слотов
    dice_msg = await callback.message.answer_dice(emoji="🎰")
    
    # Ждем завершения анимации
    await asyncio.sleep(4)
    
    # Проверяем результат
    result = dice_msg.dice.value
    if result == 64:
        db.add_attempts(callback.from_user.id, 10)
        await callback.message.answer(
            f"🎉 Поздравляем! Джекпот!\n"
            f"Вам начислено 10 попыток!"
        )
    else:
        await callback.message.answer(
            f"😔 К сожалению, не повезло.\n"
            f"Попробуйте еще раз!"
        )
@dp.message(lambda m: m.dice is not None)
async def handle_dice_result(message: types.Message, state: FSMContext):
    result = message.dice.value
    emoji = message.dice.emoji

    logging.info(f"Получен результат игры: эмодзи={emoji}, значение={result}")

    # Для баскетбола (🏀) - победа при 4 или 5
    if emoji == "🏀":
        if result in [4, 5]:
            db.add_attempts(message.from_user.id, 10)
            await message.answer(
                f"🎉 Поздравляем! Вы попали в корзину!\n"
                f"Вам начислено 10 попыток!"
            )
        else:
            await message.answer(
                f"😔 К сожалению, вы не попали в корзину.\n"
                f"Попробуйте еще раз!"
            )

    # Для футбола (⚽) - победа при 4 или 5
    elif emoji == "⚽":
        if result in [4, 5]:
            db.add_attempts(message.from_user.id, 10)
            await message.answer(
                f"🎉 Поздравляем! Вы забили гол!\n"
                f"Вам начислено 10 попыток!"
            )
        else:
            await message.answer(
                f"😔 К сожалению, вы не забили гол.\n"
                f"Попробуйте еще раз!"
            )

    # Для слотов (🎰) - победа при 64
    elif emoji == "🎰":
        if result == 64:
            db.add_attempts(message.from_user.id, 10)
            await message.answer(
                f"🎉 Поздравляем! Джекпот!\n"
                f"Вам начислено 10 попыток!"
            )
        else:
            await message.answer(
                f"😔 К сожалению, не повезло.\n"
                f"Попробуйте еще раз!"
            )

@dp.callback_query(lambda c: c.data == "roll_random_card")
async def roll_random_card_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик броска костей для получения случайной карты"""
    await handle_random_card_roll(callback, state)

@dp.callback_query(lambda c: c.data in ["dice_prev", "dice_next", "dice_info"])
async def dice_navigation_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_dice_navigation(callback, state)

@dp.callback_query(lambda c: c.data.startswith("dice_select_"))
async def dice_select_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_dice_card_selection(callback, state)

@dp.callback_query(lambda c: c.data.startswith(("accept_dice_", "reject_dice_")))
async def dice_response_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_dice_response(callback, state)

@dp.callback_query(lambda c: c.data.startswith("respond_dice_"))
async def respond_dice_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_dice_response_card_selection(callback, state)

@dp.callback_query(lambda c: c.data.startswith("roll_dice_first_"))
async def roll_dice_first_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_first_roll(callback, state)

@dp.callback_query(lambda c: c.data.startswith("roll_dice_second_"))
async def roll_dice_second_callback(callback: types.CallbackQuery, state: FSMContext):
    await handle_second_roll(callback, state)

@dp.callback_query(lambda c: c.data == "cancel_dice")
async def cancel_dice_callback(callback: types.CallbackQuery, state: FSMContext):
    await cancel_dice(callback, state)

@dp.callback_query(lambda c: c.data == "house")
async def house_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки House"""
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return

    # Проверяем, есть ли у пользователя уже семья
    if user[5] and user[5].strip():  # Проверяем, что поле family не пустое
        family = db.get_family(user[5])
        if family:
            # Проверяем, действительно ли пользователь является членом семьи
            members = db.get_family_members(family[1])
            is_member = any(member[0] == callback.from_user.id for member in members)
            
            if is_member:
                # Формируем список участников с их сезонными очками
                members_text = []
                for member in members:
                    if member[1]:  # если есть username
                        season_points = db.get_user_season_points(member[0])
                        members_text.append(f"@{member[1]} 🏆 {season_points}")
                
                members_text = "\n".join(members_text)
                
                # Создаем клавиатуру только для главы семьи
                keyboard = []
                if family[0] == callback.from_user.id:  # Если пользователь - глава семьи
                    keyboard = [
                        [InlineKeyboardButton(text="👥 Пригласить", callback_data="invite_member")],
                        [InlineKeyboardButton(text="❌ Исключить пользователя", callback_data="kick_member")],
                        [InlineKeyboardButton(text="⚠️ Расформировать семью", callback_data="disband_family")]
                    ]
                
                await callback.message.answer_photo(
                    photo=family[2],  # family[2] - это avatar_url
                    caption=f"🏠 Семья: {family[1]}\n"
                           f"👑 Глава: @{db.get_user(family[0])[1]}\n\n"
                           f"👥 Участники:\n{members_text}\n\n"
                           f"📝 Описание:\n{family[3]}",  # family[3] - это description
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
                return
            else:
                # Если пользователь не является членом семьи, очищаем поле family
                db.update_user_field(callback.from_user.id, 'family', '')
                logging.info(f"Cleared family field for user {callback.from_user.id} as they are not a member")

    # Если у пользователя нет семьи, проверяем Film Pass
    if not db.has_active_pass(callback.from_user.id):
        await callback.message.answer(
            "Для создания семьи требуется Film Pass.\n"
            "Приобретите его в магазине, чтобы создать свою семью!"
        )
        return

    # Если у пользователя нет семьи, но есть активный Film Pass, предлагаем создать
    keyboard = [
        [InlineKeyboardButton(text="🏠 Создать семью", callback_data="create_family")]
    ]
    await callback.message.answer(
        "У вас еще нет семьи. Хотите создать свою?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data == "create_family")
async def create_family_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик создания семьи"""
    await state.set_state(FamilyStates.waiting_for_name)
    await callback.message.answer("Введите название вашей семьи:")

@dp.message(FamilyStates.waiting_for_name)
async def process_family_name(message: types.Message, state: FSMContext):
    """Обработка названия семьи"""
    logging.info("=== Processing family name ===")
    logging.info(f"Message text: {message.text}")
    logging.info(f"Current state: {await state.get_state()}")
    
    try:
        # Сохраняем название семьи
        await state.update_data(family_name=message.text)
        logging.info("Family name saved to state")
        
        # Переходим к следующему состоянию
        await state.set_state(FamilyStates.waiting_for_avatar)
        logging.info("State changed to waiting_for_avatar")
        
        await message.answer("Отправьте аватарку для вашей семьи (фото):")
        logging.info("Sent request for family avatar")
    except Exception as e:
        logging.error(f"Error in process_family_name: {e}")
        await message.answer("Произошла ошибка. Попробуйте еще раз.")
        await state.clear()

@dp.message(FamilyStates.waiting_for_avatar)
async def process_family_avatar(message: types.Message, state: FSMContext):
    """Обработка аватарки семьи"""
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото для аватарки семьи")
        return
        
    photo = message.photo[-1]  # Берем самое большое фото
    await state.update_data(family_avatar=photo.file_id)
    await state.set_state(FamilyStates.waiting_for_description)
    await message.answer("Введите описание вашей семьи:")

@dp.message(FamilyStates.waiting_for_description)
async def process_family_description(message: types.Message, state: FSMContext):
    """Обработка описания семьи"""
    data = await state.get_data()
    
    # Создаем семью
    if db.create_family(
        message.from_user.id,
        data['family_name'],
        data['family_avatar'],
        message.text
    ):
        await message.answer(
            f"🎉 Поздравляем! Вы создали семью '{data['family_name']}'!\n"
            "Теперь вы можете приглашать других участников."
        )
    else:
        await message.answer("Произошла ошибка при создании семьи. Попробуйте позже.")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "invite_member")
async def invite_member_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик приглашения участника"""
    user = db.get_user(callback.from_user.id)
    if not user or not user[5]:  # Проверяем наличие семьи
        await callback.message.answer("У вас нет семьи")
        return
    
    family = db.get_family(user[5])
    if not family or family[0] != callback.from_user.id:  # Проверяем, является ли пользователь лидером
        await callback.message.answer("Только лидер семьи может приглашать участников")
        return
    
    await state.set_state(FamilyStates.waiting_for_invite_username)
    await callback.message.answer("Введите username пользователя, которого хотите пригласить (без @):")

@dp.message(FamilyStates.waiting_for_invite_username)
async def process_invite_username(message: types.Message, state: FSMContext):
    """Обработка username приглашаемого пользователя"""
    logging.info(f"Processing invite username: {message.text}")
    
    # Убираем @ если он есть в начале username
    username = message.text.lstrip('@')
    logging.info(f"Cleaned username: {username}")
    
    user = db.get_user_by_username(username)
    if not user:
        logging.info(f"User not found: {username}")
        await message.answer("Пользователь не найден")
        await state.clear()
        return
    
    logging.info(f"Found user: {user}")
    
    if user[5]:  # Проверяем, не состоит ли пользователь уже в семье
        logging.info(f"User already in family: {user[5]}")
        await message.answer("Этот пользователь уже состоит в семье")
        await state.clear()
        return
    
    # Получаем информацию о текущей семье
    current_user = db.get_user(message.from_user.id)
    family_name = current_user[5]
    family = db.get_family(family_name)
    logging.info(f"Current user family: {family_name}")
    
    # Создаем клавиатуру для приглашения
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_invite_{family_name}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_invite_{family_name}")
        ]
    ]
    
    # Отправляем уведомление пользователю
    try:
        await bot.send_photo(
            chat_id=user[0],
            photo=family[2],  # avatar_url
            caption=f"🎉 Вас пригласили в семью '{family_name}'\n\n"
                   f"👑 Глава: @{db.get_user(family[0])[1]}\n"
                   f"📝 Описание:\n{family[3]}\n\n"
                   f"Хотите присоединиться?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await message.answer(f"Приглашение отправлено пользователю @{username}")
    except Exception as e:
        logging.error(f"Error sending invite: {e}")
        await message.answer("Не удалось отправить приглашение пользователю")
    
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith(("accept_invite_", "reject_invite_")))
async def handle_invite_response(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на приглашение в семью"""
    logging.info(f"Processing invite response: {callback.data}")
    
    # Разбираем callback_data
    parts = callback.data.split("_")
    action = parts[0]  # accept или reject
    family_name = "_".join(parts[2:])  # Объединяем оставшиеся части для имени семьи
    
    logging.info(f"Action: {action}, Family name: {family_name}")
    
    if action == "accept":
        # Добавляем пользователя в семью
        if db.add_family_member(family_name, callback.from_user.id):
            family = db.get_family(family_name)
            await callback.message.edit_caption(
                caption=f"✅ Вы присоединились к семье '{family_name}'!"
            )
            # Уведомляем главу семьи
            try:
                await bot.send_message(
                    chat_id=family[0],
                    text=f"Пользователь @{callback.from_user.username} принял приглашение в семью!"
                )
            except Exception as e:
                logging.error(f"Error notifying family leader: {e}")
        else:
            await callback.message.edit_caption(
                caption="❌ Произошла ошибка при присоединении к семье"
            )
    else:  # reject
        await callback.message.edit_caption(
            caption="❌ Вы отклонили приглашение в семью"
        )

@dp.callback_query(lambda c: c.data == "add_pass")
async def add_pass_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки добавления Film Pass"""
    logging.info("Add pass button clicked")
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return
    await callback.answer()
    await process_add_pass(callback, state)

@dp.callback_query(lambda c: c.data == "kick_member")
async def kick_member_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик исключения участника"""
    user = db.get_user(callback.from_user.id)
    if not user or not user[5]:  # Проверяем наличие семьи
        await callback.message.answer("У вас нет семьи")
        return
    
    family = db.get_family(user[5])
    if not family or family[0] != callback.from_user.id:  # Проверяем, является ли пользователь лидером
        await callback.message.answer("Только лидер семьи может исключать участников")
        return
    
    # Получаем список участников
    members = db.get_family_members(family[1])
    if not members:
        await callback.message.answer("В семье нет участников для исключения")
        return
    
    # Создаем клавиатуру с участниками
    keyboard = []
    for member in members:
        if member[0] != callback.from_user.id:  # Не показываем лидера в списке
            keyboard.append([InlineKeyboardButton(
                text=f"@{member[1]}",
                callback_data=f"kick_{member[0]}"
            )])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_kick")])
    
    await callback.message.answer(
        "Выберите участника для исключения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("kick_"))
async def process_kick_member(callback: types.CallbackQuery, state: FSMContext):
    """Обработка исключения выбранного участника"""
    user_id = int(callback.data.split("_")[1])
    user = db.get_user(callback.from_user.id)
    family = db.get_family(user[5])
    
    # Удаляем пользователя из семьи
    if db.remove_family_member(family[1], user_id):
        await callback.message.answer(f"Пользователь успешно исключен из семьи")
    else:
        await callback.message.answer("Произошла ошибка при исключении пользователя")
    
    # Обновляем информацию о семье
    await house_callback(callback, state)

@dp.callback_query(lambda c: c.data == "disband_family")
async def disband_family_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик расформирования семьи"""
    user = db.get_user(callback.from_user.id)
    if not user or not user[5]:  # Проверяем наличие семьи
        await callback.message.answer("У вас нет семьи")
        return
    
    family = db.get_family(user[5])
    if not family or family[0] != callback.from_user.id:  # Проверяем, является ли пользователь лидером
        await callback.message.answer("Только лидер семьи может расформировать семью")
        return
    
    # Создаем клавиатуру подтверждения
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm_disband"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_disband")
        ]
    ]
    
    await callback.message.answer(
        "⚠️ Вы уверены, что хотите расформировать семью? Это действие нельзя отменить!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data == "confirm_disband")
async def confirm_disband_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение расформирования семьи"""
    user = db.get_user(callback.from_user.id)
    family = db.get_family(user[5])
    
    if db.disband_family(family[1]):
        await callback.message.answer("Семья успешно расформирована")
    else:
        await callback.message.answer("Произошла ошибка при расформировании семьи")

@dp.callback_query(lambda c: c.data in ["cancel_kick", "cancel_disband"])
async def cancel_action_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена действия (исключение, расформирование и т.п.)"""
    logging.info(f"Action cancelled by user {callback.from_user.id}. Callback data: {callback.data}")
    await state.clear()
    try:
        await callback.message.delete()
        logging.info(f"Deleted action message {callback.message.message_id}")
    except Exception as e:
        logging.warning(f"Could not delete action message {callback.message.message_id}: {e}")
        try:
            # Если удаление не удалось, хотя бы убираем кнопки
            await callback.message.edit_text("Действие отменено.", reply_markup=None)
        except Exception as edit_e:
            logging.warning(f"Could not edit action message {callback.message.message_id}: {edit_e}")
    await callback.answer("Действие отменено")

    # Можно добавить возврат в предыдущее меню, если это необходимо
    # Например, обратно в меню дома:
    # from components.house import house_callback # Убедитесь, что импорт есть
    # await house_callback(callback) # Передаем только callback, так как state очищен

@dp.callback_query(lambda c: c.data == "add_donate")
async def add_donate_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки выдачи доната"""
    await process_add_donate(callback, state)

@dp.callback_query(lambda c: c.data.startswith("rarity_"))
async def handle_rarity_sort(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик сортировки карт по редкости"""
    rarity = callback.data.replace("rarity_", "")
    user_id = callback.from_user.id
    
    if rarity == "all":
        # Получаем все карты пользователя
        cards = db.get_user_cards(user_id)
    else:
        # Получаем карты определенной редкости
        cards = db.get_user_cards_by_rarity(user_id, rarity)
    
    if not cards:
        await callback.answer(f"У вас нет карт{'.' if rarity == 'all' else f' редкости {rarity}.'}", show_alert=True)
        return
    
    # Сохраняем карты и начальный индекс в состоянии
    await state.update_data(cards=cards, current_index=0, current_rarity=rarity)
    await state.set_state(CollectionStates.viewing)
    
    # Показываем первую карту
    await show_collection_card(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("confirm_dice_start_"))
async def handle_dice_game_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения начала игры первым игроком"""
    try:
        logging.info("=== DICE GAME CONFIRMATION HANDLER ===")
        data = await state.get_data()
        logging.info(f"Current state data: {data}")
        
        # Проверяем наличие необходимых данных
        required_fields = ['offered_card_id', 'response_card_id', 'target_user_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logging.error(f"Missing required fields: {missing_fields}")
            logging.error(f"Available data: {data}")
            
            # Извлекаем ID карты из callback данных
            response_card_id = int(callback.data.split('_')[3])
            logging.info(f"Extracting response card ID from callback: {response_card_id}")
            
            # Пытаемся восстановить отсутствующие данные
            if 'response_card_id' in missing_fields:
                logging.info(f"Restoring missing response_card_id from callback: {response_card_id}")
                await state.update_data(response_card_id=response_card_id)
                data['response_card_id'] = response_card_id
                missing_fields.remove('response_card_id')
            
            # Если все еще есть отсутствующие поля, выходим с ошибкой
            if missing_fields:
                await callback.message.answer(
                    f"Ошибка: не удалось получить необходимые данные ({', '.join(missing_fields)})"
                )
                await state.clear()
                return

        response_card_id = int(callback.data.split('_')[3])
        logging.info(f"Response card ID from callback: {response_card_id}")
        logging.info(f"Response card ID from state: {data['response_card_id']}")
        
        # Если ID карты в состоянии нет или не совпадает, обновляем его
        if data['response_card_id'] != response_card_id:
            logging.warning(f"Response card ID mismatch: {response_card_id} != {data['response_card_id']}")
            logging.info("Updating response_card_id in state data")
            data['response_card_id'] = response_card_id
            await state.update_data(response_card_id=response_card_id)
        
        # Получаем информацию о картах
        response_card = db.get_card(data['response_card_id'])
        offered_card = db.get_card(data['offered_card_id'])

        if not response_card or not offered_card:
            logging.error("Failed to get card info")
            logging.error(f"Response card ID: {data['response_card_id']}")
            logging.error(f"Offered card ID: {data['offered_card_id']}")
            await callback.message.answer("Ошибка: не удалось получить информацию о картах")
            await state.clear()
            return

        # Создаем сообщение о начале игры
        game_message = (
            "🎲 Игра начинается!\n\n"
            f"Карты в игре:\n"
            f"1. {offered_card[1]} ({offered_card[4]})\n"
            f"2. {response_card[1]} ({response_card[4]})\n\n"
            "Сейчас мы подбросим монетку, чтобы определить, кто будет бросать кости первым!"
        )

        # Отправляем сообщение обоим игрокам
        await callback.message.answer(game_message)
        await callback.bot.send_message(
            chat_id=data['target_user_id'],
            text=game_message
        )

        # Подбрасываем монетку (анимация)
        coin_msg = await callback.message.answer_dice(emoji="🎯")
        coin_value = coin_msg.dice.value

        # Ждем окончания анимации
        await asyncio.sleep(4)

        # Определяем первого игрока (нечетное - первый игрок, четное - второй)
        first_player = callback.from_user.id if coin_value % 2 == 1 else data['target_user_id']
        second_player = data['target_user_id'] if first_player == callback.from_user.id else callback.from_user.id

        # Сохраняем порядок игроков и все остальные данные
        await state.update_data(
            first_player_id=first_player,
            second_player_id=second_player,
            response_card_id=data['response_card_id'],
            offered_card_id=data['offered_card_id']
        )
        await state.set_state(DiceStates.waiting_for_first_roll)

        # Создаем клавиатуру для броска
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🎲 Бросить кости",
                    callback_data=f"roll_dice_first_{first_player}"
                )
            ]
        ]

        # Определяем имена игроков
        first_player_name = (await callback.bot.get_chat(first_player)).username or str(first_player)
        second_player_name = (await callback.bot.get_chat(second_player)).username or str(second_player)

        # Отправляем сообщение о результате жеребьевки
        result_message = (
            f"🎯 Жребий брошен!\n\n"
            f"Первым бросает: @{first_player_name}\n"
            f"Вторым бросает: @{second_player_name}"
        )

        # Отправляем сообщения игрокам
        await callback.message.answer(result_message)
        await callback.bot.send_message(
            chat_id=data['target_user_id'],
            text=result_message
        )

        # Отправляем кнопку броска первому игроку
        await callback.bot.send_message(
            chat_id=first_player,
            text="Ваш ход! Бросайте кости!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

        # Отправляем сообщение второму игроку
        await callback.bot.send_message(
            chat_id=second_player,
            text="Ожидайте своего хода!"
        )

    except Exception as e:
        logging.error(f"Error in handle_dice_game_confirmation: {e}")
        logging.error("Full error details:", exc_info=True)
        await callback.message.answer("Произошла ошибка при начале игры")
        await state.clear()
        
@dp.callback_query(lambda c: c.data == "cancel_admin_state")
async def cancel_admin_state_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена текущего админского действия (очистка состояния)"""
    current_state = await state.get_state()
    logging.info(f"Admin action cancelled by user {callback.from_user.id}. State: {current_state}")
    await state.clear()
    try:
        await callback.message.delete()
        logging.info(f"Deleted admin action message {callback.message.message_id}")
    except Exception as e:
        logging.warning(f"Could not delete admin action message {callback.message.message_id}: {e}")
        try:
            # Если удаление не удалось, редактируем текст
            await callback.message.edit_text("Действие отменено.", reply_markup=None)
        except Exception as edit_e:
            logging.warning(f"Could not edit admin action message {callback.message.message_id}: {edit_e}")
    await callback.answer("Действие отменено")

async def process_unban_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для разбана"""
    # ... (код)
    await state.clear()

@dp.callback_query(lambda c: c.data == "delete_card")
async def delete_card_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки удаления карты"""
    await process_delete_card(callback, state)

@dp.message(AdminStates.waiting_for_delete_card_id)
async def handle_delete_card_id(message: types.Message, state: FSMContext):
    """Обработчик ввода ID карты для удаления"""
    await process_delete_card_id(message, state)

@dp.callback_query(lambda c: c.data.startswith("confirm_delete_card_"))
async def confirm_delete_card_callback(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления карты"""
    card_id = int(callback.data.split('_')[-1])
    if db.delete_card(card_id):
        await callback.message.answer(f"Карта {card_id} успешно удалена")
    else:
        await callback.message.answer("Произошла ошибка при удалении карты")
    await state.clear()

async def main():
    """Запуск бота"""
    try:
        # Запускаем проверку уведомлений
        start_notification_checker()
        
        # Запускаем бота
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main()) 