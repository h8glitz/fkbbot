from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
import random
from database import Database
from components.states import DiceStates
import asyncio
from dispatcher import dp, bot  # Импортируем из нового файла
from aiogram.fsm.storage.base import StorageKey

db = Database('film_bot.db')

async def show_card_for_dice(message: types.Message, user_id: int, current_index: int, for_response: bool = False):
    """Показ карты для игры в кости"""
    cards = db.get_user_cards(user_id)
    if not cards:
        await message.answer("У вас нет карт для игры")
        return None

    card = cards[current_index]
    
    # Формируем информацию о карточке
    card_info = (
        f"Название: {card[1]}\n"
        f"Редкость: {card[4]}\n"
        f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}\n\n"
        f"{current_index + 1}/{len(cards)}"
    )
    
    # Создаем клавиатуру с навигацией
    keyboard = get_dice_keyboard(current_index, len(cards), card[0], for_response)

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
            logging.error(f"Error showing card for dice: {e}")
            return None
    
    return cards

def get_dice_keyboard(current_index: int, total_cards: int, card_id: int, for_response: bool = False):
    """Создание клавиатуры для просмотра карт в игре в кости"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️", callback_data="dice_prev"),
            InlineKeyboardButton(text=f"{current_index + 1}/{total_cards}", callback_data="dice_info"),
            InlineKeyboardButton(text="➡️", callback_data="dice_next")
        ]
    ]
    
    # Добавляем кнопку выбора
    action = "respond_dice" if for_response else "dice_select"
    keyboard.append([
        InlineKeyboardButton(text="🎲 Выбрать эту карту", callback_data=f"{action}_{card_id}")
    ])
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dice")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def handle_dice_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка навигации по картам в игре в кости"""
    current_state = await state.get_state()
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    
    # Определяем, для ответа ли это (выбор второй карты)
    for_response = current_state == DiceStates.selecting_response_card
    
    if callback.data == "dice_prev":
        cards = db.get_user_cards(callback.from_user.id)
        current_index = len(cards) - 1 if current_index == 0 else current_index - 1
    elif callback.data == "dice_next":
        cards = db.get_user_cards(callback.from_user.id)
        current_index = 0 if current_index == len(cards) - 1 else current_index + 1
    elif callback.data == "dice_info":
        await callback.answer()
        return
    
    await state.update_data(current_index=current_index)
    await show_card_for_dice(callback.message, callback.from_user.id, current_index, for_response)
    await callback.answer()

async def handle_dice_card_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора карты для игры"""
    try:
        card_id = int(callback.data.split('_')[2])
        card = db.get_card(card_id)
        if not card:
            await callback.answer("Карта не найдена")
            return

        # Сохраняем ID карты в состоянии
        await state.update_data(offered_card_id=card_id)
        await state.set_state(DiceStates.waiting_for_username)
        
        card_info = (
            f"Вы выбрали карту:\n"
            f"Название: {card[1]}\n"
            f"Редкость: {card[4]}\n"
            f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}"
        )
        
        await callback.message.answer_photo(
            photo=card[2],
            caption=f"{card_info}\n\nВведите @username пользователя для игры:"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_dice_card_selection: {e}")
        await callback.message.answer("Произошла ошибка при выборе карты")
        await state.clear()

async def handle_dice_username_input(message: types.Message, state: FSMContext):
    """Обработка ввода username пользователя для игры"""
    try:
        username = message.text.lstrip('@')
        logging.info(f"Processing dice game username input: {username}")
        
        target_user = db.get_user_by_username(username)
        if not target_user:
            await message.answer("Пользователь не найден")
            return
        
        if target_user[0] == message.from_user.id:
            await message.answer("Вы не можете играть сами с собой")
            return
        
        data = await state.get_data()
        logging.info(f"Current state data: {data}")
        
        if 'offered_card_id' not in data:
            await message.answer("Ошибка: не удалось найти выбранную карту")
            await state.clear()
            return
            
        offered_card = db.get_card(data['offered_card_id'])
        if not offered_card:
            await message.answer("Ошибка: выбранная карта не найдена")
            await state.clear()
            return
        
        # Создаем клавиатуру для принятия/отклонения игры с ID карты в callback_data
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"accept_dice_{message.from_user.id}_{data['offered_card_id']}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_dice_{message.from_user.id}_{data['offered_card_id']}"
                )
            ]
        ]
        
        # Отправляем предложение игры
        dice_message = (
            f"🎲 Предложение игры в кости\n"
            f"От: @{message.from_user.username or message.from_user.id}\n\n"
            f"Ставит карту:\n"
            f"Название: {offered_card[1]}\n"
            f"Редкость: {offered_card[4]}\n"
            f"{'🔒 Ограниченная' if offered_card[3] else '🔓 Обычная'}"
        )
        
        try:
            await message.bot.send_photo(
                chat_id=target_user[0],
                photo=offered_card[2],
                caption=dice_message,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            # Сохраняем ID целевого пользователя в состоянии
            await state.update_data(target_user_id=target_user[0])
            
            await message.answer("Предложение игры отправлено! Ожидайте ответа.")
        except Exception as e:
            logging.error(f"Error sending dice game proposal: {e}")
            await message.answer("Ошибка при отправке предложения игры")
            await state.clear()
            
    except Exception as e:
        logging.error(f"Error in handle_dice_username_input: {e}")
        await message.answer("Произошла ошибка при обработке запроса")
        await state.clear()

async def handle_dice_response(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на предложение игры"""
    try:
        parts = callback.data.split('_')
        action = parts[1]
        sender_id = int(parts[2])
        offered_card_id = int(parts[3])  # Получаем ID карты из callback_data
        
        logging.info(f"=== DICE RESPONSE HANDLER ===")
        logging.info(f"Action: {action}, Sender ID: {sender_id}, Offered card ID: {offered_card_id}")
        
        if action == "reject":
            # Отклоняем игру
            await callback.message.edit_caption(
                caption=callback.message.caption + "\n\n❌ Игра отклонена",
                reply_markup=None
            )
            await callback.bot.send_message(
                chat_id=sender_id,
                text="❌ Ваше предложение игры было отклонено"
            )
            await state.clear()
        else:
            # Принимаем игру и предлагаем выбрать карту
            # Получаем username отправителя
            sender = await callback.bot.get_chat(sender_id)
            sender_username = sender.username or str(sender_id)
            
            # Сохраняем данные в состоянии
            await state.update_data(
                sender_id=sender_id,
                sender_username=sender_username,
                target_user_id=callback.from_user.id,
                offered_card_id=offered_card_id,
                current_index=0
            )
            
            logging.info(f"State data after accepting: {await state.get_data()}")
            
            await state.set_state(DiceStates.selecting_response_card)
            
            # Показываем первую карту для выбора
            await show_card_for_dice(callback.message, callback.from_user.id, 0, True)
            
    except Exception as e:
        logging.error(f"Error in handle_dice_response: {e}")
        await callback.message.answer("Произошла ошибка при обработке ответа")
        await state.clear()

async def handle_dice_response_card_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора карты для ответа в игре"""
    try:
        card_id = int(callback.data.split('_')[2])
        data = await state.get_data()
        
        logging.info(f"=== DICE RESPONSE CARD SELECTION ===")
        logging.info(f"Card ID: {card_id}")
        logging.info(f"Current state data: {data}")
        
        # Проверяем наличие необходимых данных
        required_fields = ['sender_id', 'offered_card_id', 'target_user_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logging.error(f"Missing required data. Current state data: {data}")
            logging.error(f"Missing fields: {missing_fields}")
            await callback.message.answer("Ошибка: не удалось получить данные об игре")
            await state.clear()
            return
        
        sender_id = data['sender_id']
        
        # Проверяем, что карта принадлежит пользователю
        user_cards = db.get_user_cards(callback.from_user.id)
        if not any(card[0] == card_id for card in user_cards):
            await callback.answer("Эта карта вам не принадлежит", show_alert=True)
            return
        
        # Получаем информацию о картах
        response_card = db.get_card(card_id)
        offered_card = db.get_card(data['offered_card_id'])
        
        if not response_card or not offered_card:
            logging.error(f"Cards not found. Response card ID: {card_id}, Offered card ID: {data['offered_card_id']}")
            await callback.message.answer("Ошибка: одна из карт не найдена")
            await state.clear()
            return

        # Создаем клавиатуру для подтверждения игры первым игроком
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Начать игру",
                    callback_data=f"confirm_dice_start_{card_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отказаться",
                    callback_data="cancel_dice"
                )
            ]
        ]

        # Сохраняем все необходимые данные в состоянии
        state_data = {
            'response_card_id': card_id,
            'target_user_id': callback.from_user.id,
            'offered_card_id': data['offered_card_id'],
            'sender_id': sender_id,
            'sender_username': data.get('sender_username', ''),
            'current_state': 'waiting_for_confirmation'
        }
        
        # ВАЖНО: сначала устанавливаем состояние, потом обновляем данные
        await state.set_state(DiceStates.waiting_for_confirmation)
        await state.update_data(state_data)
        
        logging.info(f"Updated state data: {await state.get_data()}")
        logging.info(f"Current state after update: {await state.get_state()}")

        # Отправляем сообщение первому игроку для подтверждения
        try:
            await callback.bot.send_photo(
                chat_id=sender_id,
                photo=response_card[2],
                caption=(
                    f"Игрок @{callback.from_user.username or callback.from_user.id} выбрал карту для игры:\n\n"
                    f"Название: {response_card[1]}\n"
                    f"Редкость: {response_card[4]}\n"
                    f"{'🔒 Ограниченная' if response_card[3] else '🔓 Обычная'}\n\n"
                    "Хотите начать игру с этой картой?"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            # Уведомляем второго игрока
            await callback.message.answer(
                "Ваш выбор карты отправлен. Ожидайте подтверждения первого игрока."
            )
        except Exception as e:
            logging.error(f"Error sending confirmation message: {e}")
            await callback.message.answer("Ошибка при отправке подтверждения. Пожалуйста, попробуйте еще раз.")
            await state.clear()
            return
        
    except Exception as e:
        logging.error(f"Error in handle_dice_response_card_selection: {e}")
        logging.error("Full error details:", exc_info=True)
        await callback.message.answer("Произошла ошибка при выборе карты")
        await state.clear()

@dp.callback_query(lambda c: c.data.startswith("confirm_dice_start_"))
async def handle_dice_game_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения начала игры первым игроком"""
    try:
        logging.info("=== DICE GAME CONFIRMATION ===")
        
        # Получаем ID карты из callback данных
        response_card_id = int(callback.data.split('_')[3])
        logging.info(f"Response card ID from callback: {response_card_id}")
        
        # Получаем текущие данные состояния подтверждающего игрока
        current_user_data = await state.get_data()
        logging.info(f"Current user ({callback.from_user.id}) state data: {current_user_data}")
        
        # Проверяем наличие необходимых данных
        required_fields = ['offered_card_id', 'target_user_id']
        missing_fields = [field for field in required_fields if field not in current_user_data]
        
        if missing_fields:
            logging.error(f"Missing required fields for user {callback.from_user.id}: {missing_fields}")
            await callback.message.answer("Ошибка: данные игры были потеряны (1). Пожалуйста, начните игру заново.")
            await state.clear()
            # Также очистим состояние другого игрока
            target_user_id = current_user_data.get('target_user_id')
            if target_user_id:
                target_key = StorageKey(bot_id=callback.bot.id, chat_id=target_user_id, user_id=target_user_id)
                await dp.storage.set_state(key=target_key, state=None)
                await dp.storage.set_data(key=target_key, data={})
            return
            
        target_user_id = current_user_data['target_user_id'] # ID второго игрока (который выбрал карту)
        sender_id = callback.from_user.id # ID первого игрока (который предложил игру и подтвердил)
        offered_card_id = current_user_data['offered_card_id']
        
        # Создаем общие данные игры
        game_data = {
            'response_card_id': response_card_id,
            'offered_card_id': offered_card_id,
            'target_user_id': target_user_id, 
            'sender_id': sender_id,
            'game_state': 'waiting_for_first_roll'
        }
        
        # Устанавливаем состояние и данные для ОБОИХ игроков
        await state.set_state(DiceStates.waiting_for_first_roll) # Для текущего игрока (sender_id)
        await state.update_data(game_data)
        logging.info(f"Updated state data for user {sender_id}: {await state.get_data()}")
        
        # Устанавливаем состояние и данные для второго игрока (target_user_id)
        try:
            target_key = StorageKey(bot_id=callback.bot.id, chat_id=target_user_id, user_id=target_user_id)
            await dp.storage.set_state(key=target_key, state=DiceStates.waiting_for_first_roll)
            await dp.storage.set_data(key=target_key, data=game_data)
            logging.info(f"Updated state data for user {target_user_id}: {await dp.storage.get_data(key=target_key)}")
        except Exception as e:
             logging.error(f"Failed to update state for target user {target_user_id}: {e}")
             await callback.message.answer("Ошибка: не удалось обновить состояние второго игрока. Попробуйте начать заново.")
             await state.clear()
             return

        # Получаем информацию о картах
        response_card = db.get_card(response_card_id)
        offered_card = db.get_card(offered_card_id)

        if not response_card or not offered_card:
            logging.error("Failed to get card info")
            logging.error(f"Response card ID: {response_card_id}")
            logging.error(f"Offered card ID: {offered_card_id}")
            await callback.message.answer("Ошибка: не удалось получить информацию о картах")
            await state.clear()
            target_key = StorageKey(bot_id=callback.bot.id, chat_id=target_user_id, user_id=target_user_id)
            await dp.storage.set_state(key=target_key, state=None)
            await dp.storage.set_data(key=target_key, data={})
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
            chat_id=target_user_id,
            text=game_message
        )

        # Подбрасываем монетку (анимация)
        coin_msg = await callback.message.answer_dice(emoji="🎯")
        coin_value = coin_msg.dice.value

        # Ждем окончания анимации
        await asyncio.sleep(4)

        # Определяем первого игрока (нечетное - первый игрок (sender_id), четное - второй (target_user_id))
        first_player = sender_id if coin_value % 2 == 1 else target_user_id
        second_player = target_user_id if first_player == sender_id else sender_id

        # Обновляем данные ИГРЫ с информацией об игроках для ОБОИХ
        game_data.update({
            'first_player_id': first_player,
            'second_player_id': second_player
        })
        
        await state.update_data(game_data) # Для текущего игрока (sender_id)
        target_key = StorageKey(bot_id=callback.bot.id, chat_id=target_user_id, user_id=target_user_id)
        await dp.storage.set_data(key=target_key, data=game_data) # Для второго игрока (target_user_id)
        
        logging.info(f"Final state data for user {sender_id}: {await state.get_data()}")
        logging.info(f"Final state data for user {target_user_id}: {await dp.storage.get_data(key=target_key)}")
        
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

        # Отправляем сообщение с кнопкой первому игроку
        await callback.bot.send_message(
            chat_id=first_player,
            text=result_message + "\n\nВаш ход! Бросайте кости!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Отправляем сообщение второму игроку
        await callback.bot.send_message(
            chat_id=second_player,
            text=result_message + "\n\nОжидайте своего хода!"
        )
        
        logging.info("Game confirmation completed successfully")
        
    except Exception as e:
        logging.error(f"Error in handle_dice_game_confirmation: {e}")
        logging.error("Full error details:", exc_info=True)
        await callback.message.answer("Произошла ошибка при подтверждении игры")
        # Очищаем состояние обоих игроков при ошибке
        try:
            current_user_data_on_error = await state.get_data()
            target_user_id_on_error = current_user_data_on_error.get('target_user_id')
            await state.clear()
            if target_user_id_on_error:
                target_key = StorageKey(bot_id=callback.bot.id, chat_id=target_user_id_on_error, user_id=target_user_id_on_error)
                await dp.storage.set_state(key=target_key, state=None)
                await dp.storage.set_data(key=target_key, data={})
        except Exception as clear_error:
            logging.error(f"Error clearing state during exception handling: {clear_error}")

async def handle_first_roll(callback: types.CallbackQuery, state: FSMContext):
    """Обработка первого броска костей"""
    try:
        logging.info(f"=== FIRST ROLL HANDLER ===")
        logging.info(f"User ID attempting roll: {callback.from_user.id}")
        
        # Получаем данные состояния текущего игрока
        data = await state.get_data()
        logging.info(f"Current state data for user {callback.from_user.id} before processing: {data}")
        
        # Проверяем состояние игры в данных
        game_state = data.get('game_state')
        if game_state != 'waiting_for_first_roll':
            logging.error(f"Invalid game state in data for user {callback.from_user.id}: {game_state}")
            await callback.message.answer("Ошибка: неверное состояние игры (1). Пожалуйста, начните игру заново.")
            await state.clear()
            # Попытка очистить состояние другого игрока
            second_player_id = data.get('second_player_id')
            if second_player_id:
                try:
                    target_key = StorageKey(bot_id=callback.bot.id, chat_id=second_player_id, user_id=second_player_id)
                    await dp.storage.set_state(key=target_key, state=None)
                    await dp.storage.set_data(key=target_key, data={})
                except Exception as clear_error:
                    logging.error(f"Error clearing second player state during error handling: {clear_error}")
            return
        
        # Проверяем наличие всех необходимых данных
        required_fields = ['first_player_id', 'second_player_id', 'response_card_id', 'offered_card_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logging.error(f"Missing required fields for user {callback.from_user.id}: {missing_fields}")
            await callback.message.answer("Ошибка: данные игры были потеряны (2). Пожалуйста, начните игру заново.")
            await state.clear()
            # Попытка очистить состояние другого игрока
            second_player_id = data.get('second_player_id')
            if second_player_id:
                 try:
                    target_key = StorageKey(bot_id=callback.bot.id, chat_id=second_player_id, user_id=second_player_id)
                    await dp.storage.set_state(key=target_key, state=None)
                    await dp.storage.set_data(key=target_key, data={})
                 except Exception as clear_error:
                    logging.error(f"Error clearing second player state during error handling: {clear_error}")
            return
        
        # Извлекаем ID игрока из callback данных
        expected_player_id = int(callback.data.split('_')[3])
        first_player_id = data.get('first_player_id')
        
        logging.info(f"Expected first player ID: {first_player_id}")
        logging.info(f"Expected player ID from callback: {expected_player_id}")
        logging.info(f"Current user ID: {callback.from_user.id}")
        
        # Проверяем, что бросает первый игрок
        is_correct_player = (
            callback.from_user.id == first_player_id or 
            callback.from_user.id == expected_player_id
        )
        
        if not is_correct_player:
            logging.warning(f"Wrong player attempting first roll.")
            logging.warning(f"Expected: {first_player_id} (or {expected_player_id}), Got: {callback.from_user.id}")
            await callback.answer("Сейчас не ваша очередь бросать кости!", show_alert=True)
            return
        
        logging.info("First roll validation passed, proceeding with dice roll")

        # Сразу удаляем кнопку броска
        await callback.message.edit_reply_markup(reply_markup=None)
        
        dice_msg = await callback.message.answer_dice(emoji="🎲")
        first_roll = dice_msg.dice.value
        logging.info(f"First roll value: {first_roll}")
        
        # Обновляем данные состояния ДЛЯ ОБОИХ ИГРОКОВ
        data['first_roll'] = first_roll
        data['game_state'] = 'waiting_for_second_roll'
        
        # 1. Обновляем для текущего игрока (кто бросил)
        await state.update_data(data)
        logging.info(f"Updated state data for user {callback.from_user.id}: {await state.get_data()}")
        
        # 2. Обновляем для второго игрока
        second_player_id = data.get('second_player_id')
        if not second_player_id:
            logging.error(f"Second player ID not found in state data for user {callback.from_user.id}")
            await callback.message.answer("Ошибка: не найден ID второго игрока. Пожалуйста, начните заново.")
            await state.clear()
            return 
            
        try:
            target_key = StorageKey(bot_id=callback.bot.id, chat_id=second_player_id, user_id=second_player_id)
            await dp.storage.set_data(key=target_key, data=data)
            logging.info(f"Updated state data for user {second_player_id}: {await dp.storage.get_data(key=target_key)}")
        except Exception as e:
            logging.error(f"Failed to update state data for second player {second_player_id}: {e}")
            await callback.message.answer("Ошибка: не удалось обновить состояние второго игрока (3). Пожалуйста, начните заново.")
            await state.clear()
            # Попытка очистить состояние другого игрока
            try:
                await dp.storage.set_state(key=target_key, state=None)
                await dp.storage.set_data(key=target_key, data={})
            except Exception as clear_error:
                logging.error(f"Error clearing second player state during error handling: {clear_error}")
            return
            
        # Проверяем, что данные обновились у текущего игрока
        updated_data = await state.get_data()
        if updated_data.get('game_state') != 'waiting_for_second_roll':
            logging.error("Failed to update game state for current player")
            await callback.message.answer("Ошибка: не удалось обновить состояние игры (4). Пожалуйста, начните заново.")
            await state.clear()
            # Попытка очистить состояние другого игрока
            try:
                target_key = StorageKey(bot_id=callback.bot.id, chat_id=second_player_id, user_id=second_player_id)
                await dp.storage.set_state(key=target_key, state=None)
                await dp.storage.set_data(key=target_key, data={})
            except Exception as clear_error:
                logging.error(f"Error clearing second player state during error handling: {clear_error}")
            return
        
        # Ждем окончания анимации кубика
        await asyncio.sleep(4)
        
        # Устанавливаем новое FSM состояние для текущего игрока
        await state.set_state(DiceStates.waiting_for_second_roll)
        current_state = await state.get_state()
        logging.info(f"FSM state for user {callback.from_user.id} changed to {current_state}")
        
        # Устанавливаем FSM состояние для второго игрока
        try:
            target_key = StorageKey(bot_id=callback.bot.id, chat_id=second_player_id, user_id=second_player_id)
            await dp.storage.set_state(key=target_key, state=DiceStates.waiting_for_second_roll)
            logging.info(f"FSM state for user {second_player_id} set to {await dp.storage.get_state(key=target_key)}")
        except Exception as e:
            logging.error(f"Failed to set FSM state for second player {second_player_id}: {e}")
            # Не прерываем игру, так как данные уже обновлены, но логируем ошибку
        
        # Создаем клавиатуру для второго броска
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🎲 Бросить кости",
                    callback_data=f"roll_dice_second_{second_player_id}" # Используем ID второго игрока
                )
            ]
        ]
        
        # Отправляем сообщение второму игроку с кнопкой
        await callback.bot.send_message(
            chat_id=second_player_id,
            text=f"Первый игрок выбросил: {first_roll}\nВаш ход! Бросайте кости!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        logging.info(f"Sent roll button to second player: {second_player_id}")
        
        # Отправляем сообщение первому игроку
        await callback.message.answer(
            f"Вы выбросили: {first_roll}\nОжидайте броска второго игрока!"
        )
        logging.info("First roll handler completed successfully")
            
    except Exception as e:
        logging.error(f"Error in handle_first_roll: {e}")
        logging.error(f"Full error details:", exc_info=True)
        await callback.message.answer("Произошла ошибка при обработке броска")
        await state.clear()
        # Попытка очистить состояние другого игрока
        try:
            data_on_error = await state.get_data()
            second_player_id_on_error = data_on_error.get('second_player_id')
            if second_player_id_on_error:
                target_key = StorageKey(bot_id=callback.bot.id, chat_id=second_player_id_on_error, user_id=second_player_id_on_error)
                await dp.storage.set_state(key=target_key, state=None)
                await dp.storage.set_data(key=target_key, data={})
        except Exception as clear_error:
             logging.error(f"Error clearing second player state during main exception handling: {clear_error}")

async def handle_second_roll(callback: types.CallbackQuery, state: FSMContext):
    """Обработка второго броска костей"""
    try:
        logging.info(f"=== SECOND ROLL HANDLER ===")
        logging.info(f"User ID attempting roll: {callback.from_user.id}")
        
        # Получаем данные состояния
        data = await state.get_data()
        logging.info(f"Current state data before processing: {data}")
        
        # Проверяем состояние игры в данных
        game_state = data.get('game_state')
        logging.info(f"Game state from data: {game_state}")
        
        if game_state != 'waiting_for_second_roll':
            logging.error(f"Invalid game state in data: {game_state}")
            await callback.message.answer("Ошибка: неверное состояние игры. Пожалуйста, начните игру заново.")
            await state.clear()
            return
        
        # Проверяем наличие всех необходимых данных
        required_fields = ['first_roll', 'first_player_id', 'second_player_id', 'response_card_id', 'offered_card_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logging.error(f"Missing required fields: {missing_fields}")
            await callback.message.answer("Ошибка: данные игры были потеряны. Пожалуйста, начните игру заново.")
            await state.clear()
            return
        
        # Извлекаем ID игрока из callback данных
        expected_player_id = int(callback.data.split('_')[3])
        second_player_id = data.get('second_player_id')
        
        logging.info(f"Expected second player ID: {second_player_id}")
        logging.info(f"Expected player ID from callback: {expected_player_id}")
        logging.info(f"Current user ID: {callback.from_user.id}")
        
        # Проверяем, что бросает второй игрок
        is_correct_player = (
            callback.from_user.id == second_player_id or 
            callback.from_user.id == expected_player_id
        )
        
        if not is_correct_player:
            logging.warning(f"Wrong player attempting second roll.")
            logging.warning(f"Expected: {second_player_id} (or {expected_player_id}), Got: {callback.from_user.id}")
            await callback.answer("Сейчас не ваша очередь бросать кости!", show_alert=True)
            return
        
        logging.info("Second roll validation passed, proceeding with dice roll")

        # Сразу удаляем кнопку броска
        await callback.message.edit_reply_markup(reply_markup=None)
        
        dice_msg = await callback.message.answer_dice(emoji="🎲")
        second_roll = dice_msg.dice.value
        logging.info(f"Second roll value: {second_roll}")
        
        # Ждем окончания анимации кубика
        await asyncio.sleep(4)
        
        first_roll = data['first_roll']
        logging.info(f"First roll was: {first_roll}")
        
        # Получаем информацию о картах
        response_card = db.get_card(data['response_card_id'])
        offered_card = db.get_card(data['offered_card_id'])
        
        if not response_card or not offered_card:
            logging.error(f"Failed to get cards. Response card ID: {data['response_card_id']}, Offered card ID: {data['offered_card_id']}")
            await callback.message.answer("Ошибка: не удалось получить информацию о картах")
            await state.clear()
            return

        logging.info(f"Processing game result. First roll: {first_roll}, Second roll: {second_roll}")

        # Определяем победителя
        if first_roll > second_roll:
            winner_id = data['first_player_id']
            loser_id = data['second_player_id']
            winner_roll = first_roll
            loser_roll = second_roll
        elif second_roll > first_roll:
            winner_id = data['second_player_id']
            loser_id = data['first_player_id']
            winner_roll = second_roll
            loser_roll = first_roll
        else:
            logging.info("Game ended in a draw")
            result_message = (
                f"🎲 Игра завершена!\n\n"
                f"Первый бросок: {first_roll}\n"
                f"Второй бросок: {second_roll}\n\n"
                f"🤝 Ничья! Карты остаются у своих владельцев."
            )
            
            await callback.message.answer(result_message)
            await callback.bot.send_message(
                chat_id=data['first_player_id'],
                text=result_message
            )
            await state.clear()
            return

        logging.info(f"Winner determined: {winner_id}")
        winner_username = (await callback.bot.get_chat(winner_id)).username or str(winner_id)
        
        # Передаем карты победителю
        try:
            if winner_id == data['first_player_id']:
                logging.info("Transferring response card to first player")
                # Удаляем карту у проигравшего (loser_id - второй игрок)
                if not db.remove_card_from_user(loser_id, response_card[0]):
                    logging.warning(f"Failed to remove card {response_card[0]} from loser {loser_id}")
                # Добавляем карту победителю (winner_id - первый игрок)
                if not db.add_card_to_user(winner_id, response_card[0]):
                     logging.warning(f"Failed to add card {response_card[0]} to winner {winner_id}")
            else: # winner_id == data['second_player_id']
                logging.info("Transferring offered card to second player")
                 # Удаляем карту у проигравшего (loser_id - первый игрок)
                if not db.remove_card_from_user(loser_id, offered_card[0]):
                     logging.warning(f"Failed to remove card {offered_card[0]} from loser {loser_id}")
                # Добавляем карту победителю (winner_id - второй игрок)
                if not db.add_card_to_user(winner_id, offered_card[0]):
                     logging.warning(f"Failed to add card {offered_card[0]} to winner {winner_id}")
                     
            # Записываем статистику
            logging.info(f"Recording stats: Winner={winner_id}, Loser={loser_id}")
            db.add_dice_win(winner_id)
            db.add_dice_loss(loser_id)
            
        except Exception as e:
            logging.error(f"Error transferring cards or recording stats: {e}")
            logging.error("Full error details:", exc_info=True)
            await callback.message.answer("Произошла ошибка при передаче карт или записи статистики")
            await state.clear()
            # Попытка очистить состояние другого игрока
            other_player_id = data['first_player_id'] if callback.from_user.id == data['second_player_id'] else data['second_player_id']
            try:
                target_key = StorageKey(bot_id=callback.bot.id, chat_id=other_player_id, user_id=other_player_id)
                await dp.storage.set_state(key=target_key, state=None)
                await dp.storage.set_data(key=target_key, data={})
            except Exception as clear_error:
                logging.error(f"Error clearing other player state during error handling: {clear_error}")
            return
        
        # Отправляем сообщение о результатах
        result_message = (
            f"🎲 Игра завершена!\n\n"
            f"Первый бросок: {first_roll}\n"
            f"Второй бросок: {second_roll}\n\n"
            f"Победитель: @{winner_username}\n"
            f"Выигранная карта: {offered_card[1] if winner_id == data['second_player_id'] else response_card[1]}"
        )
        
        logging.info("Sending final results to players")
        await callback.message.answer(result_message)
        await callback.bot.send_message(
            chat_id=data['first_player_id'],
            text=result_message
        )
        
        await state.clear()
        logging.info("Game completed successfully")
        
    except Exception as e:
        logging.error(f"Error in handle_second_roll: {e}")
        logging.error("Full error details:", exc_info=True)
        await callback.message.answer("Произошла ошибка при обработке броска")
        await state.clear()

async def cancel_dice(callback: types.CallbackQuery, state: FSMContext):
    """Отмена игры в кости"""
    logging.info(f"Dice game cancelled by user {callback.from_user.id}")
    await state.clear()
    try:
        await callback.message.delete()
        logging.info(f"Deleted dice message {callback.message.message_id} for user {callback.from_user.id}")
    except Exception as e:
        # Если сообщение уже удалено или что-то пошло не так, просто логируем
        logging.warning(f"Could not delete dice message {callback.message.message_id}: {e}")
        # Попытаемся отредактировать текст, если удаление не удалось
        try:
            await callback.message.edit_text("Игра отменена.")
        except Exception as edit_e:
             logging.warning(f"Could not edit dice message {callback.message.message_id} after delete failed: {edit_e}")
    await callback.answer() # Подтверждаем нажатие кнопки 