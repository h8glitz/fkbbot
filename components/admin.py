from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Database
from components.states import AddCard, AdminStates
import logging
from datetime import datetime
from dispatcher import bot

db = Database('film_bot.db')

# --- Вспомогательная функция для создания клавиатуры Отмены ---
def create_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_admin_state")]
    ])

def get_admin_keyboard():
    """Создание админ-клавиатуры"""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Добавить карту", callback_data="add_card"),
            InlineKeyboardButton(text="📋 Список карт", callback_data="list_cards")
        ],
        [
            InlineKeyboardButton(text="🔍 Найти карту", callback_data="find_card"),
            InlineKeyboardButton(text="❌ Удалить карту", callback_data="delete_card")
        ],
        [
            InlineKeyboardButton(text="🎯 Добавить попытки", callback_data="add_attempts"),
            InlineKeyboardButton(text="🚫 Забанить", callback_data="ban_user")
        ],
        [
            InlineKeyboardButton(text="✅ Разбанить", callback_data="unban_user"),
            InlineKeyboardButton(text="🎫 Добавить Film Pass", callback_data="add_pass")
        ],
        [
            InlineKeyboardButton(text="💰 Выдать донат", callback_data="add_donate")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def process_add_card(callback: types.CallbackQuery, state: FSMContext):
    """Обработка добавления карты"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    await callback.answer()
    await callback.message.answer(
        "Введите название карты:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_name)

async def process_name(message: types.Message, state: FSMContext):
    """Обработка ввода названия карты"""
    await state.update_data(card_name=message.text)
    await message.answer(
        "Отправьте фото карты:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_photo)

async def process_photo(message: types.Message, state: FSMContext):
    """Обработка загрузки фото карты"""
    if not message.photo:
        await message.answer(
            "Пожалуйста, отправьте фото карты.",
            reply_markup=create_cancel_keyboard()
        )
        return

    photo_url = message.photo[-1].file_id
    await state.update_data(photo_url=photo_url)
    await message.answer(
        "Карта ограниченная? (1 - да, 0 - нет):",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_limited)

async def process_limited(message: types.Message, state: FSMContext):
    """Обработка ввода ограниченности карты"""
    if not message.text.isdigit() or int(message.text) not in [0, 1]:
        await message.answer(
            "Пожалуйста, введите 0 или 1",
            reply_markup=create_cancel_keyboard()
        )
        return

    await state.update_data(limited=int(message.text))
    await message.answer(
        "Введите редкость карты:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_rare)

async def process_rare(message: types.Message, state: FSMContext):
    """Обработка ввода редкости карты"""
    await state.update_data(rare=message.text)
    await message.answer(
        "Введите количество очков:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_points)

async def process_points(message: types.Message, state: FSMContext):
    """Обработка ввода очков карты"""
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите число",
            reply_markup=create_cancel_keyboard()
        )
        return

    await state.update_data(points=int(message.text))
    await message.answer(
        "Введите цену:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_price)

async def process_price(message: types.Message, state: FSMContext):
    """Обработка ввода цены карты"""
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите число",
            reply_markup=create_cancel_keyboard()
        )
        return

    await state.update_data(price=int(message.text))
    await message.answer(
        "Введите количество counts:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AddCard.waiting_for_counts)

async def process_counts(message: types.Message, state: FSMContext):
    """Обработка ввода количества counts - финальный шаг"""
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите число",
            reply_markup=create_cancel_keyboard()
        )
        return
    # Здесь кнопка Отмены уже не так критична, т.к. это последний шаг
    # Но добавим на случай ошибки ввода
    try:
        data = await state.get_data()
        card_id = db.add_card(
            data['card_name'],
            data['photo_url'],
            data['limited'],
            data['rare'],
            data['points'],
            data['price'],
            int(message.text)
        )
        await message.answer(f"Карта успешно добавлена! ID карты: {card_id}")
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении карты: {str(e)}")
    finally:
        await state.clear()

async def process_list_cards(callback: types.CallbackQuery):
    """Показ списка всех карт"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    cards = db.get_all_cards()
    if not cards:
        await callback.message.answer("Список карт пуст")
        return

    for card in cards:
        card_info = (
            f"ID: {card[0]}\n"
            f"Название: {card[1]}\n"
            f"Редкость: {card[4]}\n"
            f"Очки: {card[5]}\n"
            f"Цена: {card[6]}\n"
            f"Counts: {card[7]}\n"
            f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}"
        )
        try:
             await callback.message.answer_photo(
                photo=card[2],
                caption=card_info
            )
        except Exception as e:
            logging.error(f"Error sending card {card[0]}: {e}")
            await callback.message.answer(f"Ошибка при отправке карты ID {card[0]}: {e}")

async def process_find_card(callback: types.CallbackQuery):
    """Поиск карты по ID"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return
    # Здесь state не используется, кнопка отмены не нужна
    await callback.message.answer("Введите ID карты:")

# --- Функции удаления карты ---
async def process_delete_card(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса удаления карты"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return
    
    logging.info(f"Admin {callback.from_user.id} initiated delete card process.")
    await callback.answer()
    await callback.message.answer(
        "Введите ID карты для удаления:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_delete_card_id)
    logging.info(f"Admin {callback.from_user.id} set state to {await state.get_state()}")

async def process_delete_card_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID карты для удаления"""
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите ID карты (число).",
            reply_markup=create_cancel_keyboard()
        )
        return
        
    card_id = int(message.text)
    card = db.get_card(card_id)
    
    if not card:
        await message.answer(
            f"Карта с ID {card_id} не найдена. Попробуйте еще раз.",
            reply_markup=create_cancel_keyboard()
        )
        return
        
    # Показываем карту для подтверждения
    card_info = (
        f"ID: {card[0]}\n"
        f"Название: {card[1]}\n"
        f"Редкость: {card[4]}"
    )
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_card_{card_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_admin_state")]
    ]
    
    try:
        await message.answer_photo(
            photo=card[2],
            caption=f"Вы уверены, что хотите удалить эту карту?\n\n{card_info}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        # Сохраняем ID в состоянии на случай, если подтверждение придет позже
        await state.update_data(card_to_delete_id=card_id) 
    except Exception as e:
        logging.error(f"Error sending confirmation photo for delete card {card_id}: {e}")
        await message.answer(
            f"Не удалось отправить фото карты {card_id}.\n" 
            f"Вы уверены, что хотите удалить карту: {card[1]} ({card[4]})?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await state.update_data(card_to_delete_id=card_id)

# --- Конец функций удаления карты ---

async def process_add_attempts(callback: types.CallbackQuery, state: FSMContext):
    """Добавление попыток пользователю"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    await callback.answer()
    await callback.message.answer(
        "Введите ID пользователя или @username:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_user_id)

async def process_user_id_for_attempts(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для добавления попыток"""
    user_id = None
    username = None
    
    input_text = message.text.lstrip('@')
    if input_text.isdigit():
        user_id = int(input_text)
        user = db.get_user(user_id)
    else:
        username = input_text
        user = db.get_user_by_username(username)
    
    if not user:
        await message.answer(
            "Пользователь не найден. Введите ID или @username",
             reply_markup=create_cancel_keyboard()
        )
        return

    user_id = user[0]
    username = user[1]
    await state.update_data(target_user_id=user_id, target_username=username)
    await message.answer(
        f"Введите количество попыток для добавления пользователю @{username or user_id}:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_attempts)

async def process_attempts_count(message: types.Message, state: FSMContext):
    """Обработка ввода количества попыток - финальный шаг"""
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите число",
            reply_markup=create_cancel_keyboard()
        )
        return

    data = await state.get_data()
    user_id = data['target_user_id']
    username = data.get('target_username') # Получаем username из state
    attempts = int(message.text)

    db.add_attempts(user_id, attempts)
    await message.answer(f"Пользователю @{username or user_id} добавлено {attempts} попыток")
    await state.clear()

async def process_ban_user(callback: types.CallbackQuery, state: FSMContext):
    """Бан пользователя"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    logging.info(f"Admin {callback.from_user.id} initiated ban process.")
    await callback.answer()
    await callback.message.answer(
        "Введите ID или @username пользователя для бана:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_ban_user_id)
    logging.info(f"Admin {callback.from_user.id} set state to {await state.get_state()}")

async def process_ban_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для бана - финальный шаг"""
    user_id = None
    username = None
    
    input_text = message.text.lstrip('@')
    if input_text.isdigit():
        user_id = int(input_text)
        user = db.get_user(user_id)
    else:
        username = input_text
        user = db.get_user_by_username(username)
    
    if not user:
        await message.answer(
            "Пользователь не найден. Введите ID или @username",
             reply_markup=create_cancel_keyboard()
        )
        return # Не очищаем state, даем шанс ввести снова

    user_id = user[0]
    username = user[1] # Сохраняем username для сообщения
    if db.is_banned(user_id):
        await message.answer(f"Пользователь @{username or user_id} уже забанен")
        await state.clear()
        return

    db.ban_user(user_id)
    await message.answer(f"Пользователь @{username or user_id} забанен")
    await state.clear()

async def process_unban_user(callback: types.CallbackQuery, state: FSMContext):
    """Разбан пользователя"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    logging.info(f"Admin {callback.from_user.id} initiated unban process.")
    await callback.answer()
    await callback.message.answer(
        "Введите ID или @username пользователя для разбана:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_unban_user_id)
    logging.info(f"Admin {callback.from_user.id} set state to {await state.get_state()}")

async def process_unban_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для разбана - финальный шаг"""
    user_id = None
    username = None
    
    input_text = message.text.lstrip('@')
    if input_text.isdigit():
        user_id = int(input_text)
        user = db.get_user(user_id)
    else:
        username = input_text
        user = db.get_user_by_username(username)
    
    if not user:
        await message.answer(
            "Пользователь не найден. Введите ID или @username",
            reply_markup=create_cancel_keyboard()
        )
        return

    user_id = user[0]
    username = user[1]
    if not db.is_banned(user_id):
        await message.answer(f"Пользователь @{username or user_id} не забанен")
        await state.clear()
        return

    db.unban_user(user_id)
    await message.answer(f"Пользователь @{username or user_id} разбанен")
    await state.clear()

async def process_add_pass(callback: types.CallbackQuery, state: FSMContext):
    """Добавление Film Pass пользователю"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    logging.info(f"Admin {callback.from_user.id} started adding Film Pass")
    await callback.answer()
    
    try:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="Введите ID пользователя или @username:",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_pass_user_id)
        logging.info(f"Admin state set to {await state.get_state()}")
    except Exception as e:
        logging.error(f"Error in process_add_pass: {e}")
        await callback.message.answer("Произошла ошибка при отправке сообщения")

async def process_pass_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для добавления Film Pass"""
    logging.info(f"Received user input for pass: {message.text}")
    
    user_id = None
    username = None
    
    input_text = message.text.lstrip('@')
    logging.info(f"Processed input text: {input_text}")
    
    if input_text.isdigit():
        user_id = int(input_text)
        logging.info(f"Searching user by ID: {user_id}")
        user = db.get_user(user_id)
    else:
        username = input_text
        logging.info(f"Searching user by username: {username}")
        user = db.get_user_by_username(username)
    
    if not user:
        logging.warning(f"User not found for input: {message.text}")
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text="Пользователь не найден. Введите ID или @username",
                reply_markup=create_cancel_keyboard()
            )
        except Exception as e:
            logging.error(f"Error in process_pass_user_id: {e}")
            await message.answer("Произошла ошибка при отправке сообщения")
        return

    logging.info(f"Found user: {user}")
    user_id = user[0]
    username = user[1]
    await state.update_data(target_user_id=user_id, target_username=username)
    
    expiry_date = db.get_pass_expiry(user_id)
    logging.info(f"Current pass expiry date: {expiry_date}")
    
    prompt_text = f"Введите количество месяцев для Film Pass пользователю @{username or user_id} (1-12):"
    if expiry_date and expiry_date > datetime.now():
        prompt_text = (
            f"У пользователя @{username or user_id} уже есть активный Film Pass до {expiry_date.strftime('%d.%m.%Y')}\n"
            f"Введите количество месяцев для продления (1-12):"
        )
    
    try:
        await bot.send_message(
            chat_id=message.from_user.id,
            text=prompt_text,
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_pass_months)
    except Exception as e:
        logging.error(f"Error in process_pass_user_id: {e}")
        await message.answer("Произошла ошибка при отправке сообщения")

async def process_pass_months(message: types.Message, state: FSMContext):
    """Обработка ввода количества месяцев для Film Pass - финальный шаг"""
    logging.info(f"Received months input: {message.text}")
    
    if not message.text.isdigit() or not (1 <= int(message.text) <= 12):
        logging.warning(f"Invalid months input: {message.text}")
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text="Пожалуйста, введите число от 1 до 12",
                reply_markup=create_cancel_keyboard()
            )
        except Exception as e:
            logging.error(f"Error in process_pass_months: {e}")
            await message.answer("Произошла ошибка при отправке сообщения")
        return

    data = await state.get_data()
    user_id = data['target_user_id']
    username = data.get('target_username') # Получаем username из state
    months = int(message.text)
    logging.info(f"Adding {months} months of pass to user {user_id}")

    if db.add_pass(user_id, months):
        expiry_date = db.get_pass_expiry(user_id)
        logging.info(f"Successfully added pass, new expiry date: {expiry_date}")
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=f"Film Pass для @{username or user_id} успешно добавлен!\n"
                     f"Действует до: {expiry_date.strftime('%d.%m.%Y')}"
            )
        except Exception as e:
            logging.error(f"Error in process_pass_months: {e}")
            await message.answer("Произошла ошибка при отправке сообщения")
    else:
        logging.error(f"Failed to add pass for user {user_id}")
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text="Произошла ошибка при добавлении Film Pass"
            )
        except Exception as e:
            logging.error(f"Error in process_pass_months: {e}")
            await message.answer("Произошла ошибка при отправке сообщения")
    
    await state.clear()

async def process_add_donate(callback: types.CallbackQuery, state: FSMContext):
    """Выдача доната пользователю"""
    if not db.is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции")
        return

    logging.info(f"Admin {callback.from_user.id} started adding donate")
    await callback.answer()
    await callback.message.answer(
        "Введите ID пользователя или @username:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_donate_user_id)

async def process_donate_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для выдачи доната"""
    logging.info(f"Received user input for donate: {message.text}")
    
    user_id = None
    username = None
    
    input_text = message.text.lstrip('@')
    logging.info(f"Processed input text: {input_text}")
    
    if input_text.isdigit():
        user_id = int(input_text)
        logging.info(f"Searching user by ID: {user_id}")
        user = db.get_user(user_id)
    else:
        username = input_text
        logging.info(f"Searching user by username: {username}")
        user = db.get_user_by_username(username)
    
    if not user:
        logging.warning(f"User not found for input: {message.text}")
        await message.answer(
            "Пользователь не найден. Введите ID или @username",
            reply_markup=create_cancel_keyboard()
        )
        return

    logging.info(f"Found user: {user}")
    user_id = user[0]
    username = user[1]
    await state.update_data(target_user_id=user_id, target_username=username)
    
    current_donate = db.get_user_donate(user_id)
    logging.info(f"Current donate balance: {current_donate}")
    
    await message.answer(
        f"Текущий баланс доната пользователя @{username or user_id}: {current_donate}\n"
        f"Введите количество доната для выдачи:",
        reply_markup=create_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_donate_amount)

async def process_donate_amount(message: types.Message, state: FSMContext):
    """Обработка ввода количества доната - финальный шаг"""
    logging.info(f"Received donate amount input: {message.text}")
    
    if not message.text.isdigit() or int(message.text) <= 0:
        logging.warning(f"Invalid donate amount input: {message.text}")
        await message.answer(
            "Пожалуйста, введите положительное число",
            reply_markup=create_cancel_keyboard()
        )
        return

    data = await state.get_data()
    user_id = data['target_user_id']
    username = data.get('target_username')
    amount = int(message.text)
    logging.info(f"Adding {amount} donate to user {user_id}")

    if db.add_donate(user_id, amount):
        new_balance = db.get_user_donate(user_id)
        logging.info(f"Successfully added donate, new balance: {new_balance}")
        await message.answer(
            f"Донат успешно выдан пользователю @{username or user_id}!\n"
            f"Новый баланс: {new_balance}"
        )
    else:
        logging.error(f"Failed to add donate for user {user_id}")
        await message.answer("Произошла ошибка при выдаче доната")
    
    await state.clear() 