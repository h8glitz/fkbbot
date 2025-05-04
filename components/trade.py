from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
from database import Database
from components.states import TradeStates

db = Database('film_bot.db')

async def show_card_for_trade(message: types.Message, user_id: int, current_index: int, for_response: bool = False):
    """Показ карты для обмена"""
    cards = db.get_user_cards(user_id)
    if not cards:
        await message.answer("У вас нет карт для обмена")
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
    keyboard = get_trade_keyboard(current_index, len(cards), card[0], for_response)

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
            logging.error(f"Error showing card for trade: {e}")
            return None
    
    return cards

def get_trade_keyboard(current_index: int, total_cards: int, card_id: int, for_response: bool = False):
    """Создание клавиатуры для просмотра карт при обмене"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️", callback_data="trade_prev"),
            InlineKeyboardButton(text=f"{current_index + 1}/{total_cards}", callback_data="trade_info"),
            InlineKeyboardButton(text="➡️", callback_data="trade_next")
        ]
    ]
    
    # Добавляем кнопку выбора
    action = "respond_select" if for_response else "trade_select"
    keyboard.append([
        InlineKeyboardButton(text="✅ Выбрать эту карту", callback_data=f"{action}_{card_id}")
    ])
    
    # Добавляем кнопку отмены
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_trade")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def start_trade(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса обмена"""
    await state.set_state(TradeStates.selecting_card)
    await state.update_data(current_index=0)
    
    cards = await show_card_for_trade(callback.message, callback.from_user.id, 0)
    if not cards:
        await state.clear()
        return

async def handle_trade_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка навигации по картам при обмене"""
    current_state = await state.get_state()
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    
    # Определяем, для ответа ли это (выбор второй карты)
    for_response = current_state == TradeStates.selecting_response_card
    
    if callback.data == "trade_prev":
        cards = db.get_user_cards(callback.from_user.id)
        current_index = len(cards) - 1 if current_index == 0 else current_index - 1
    elif callback.data == "trade_next":
        cards = db.get_user_cards(callback.from_user.id)
        current_index = 0 if current_index == len(cards) - 1 else current_index + 1
    elif callback.data == "trade_info":
        await callback.answer()
        return
    
    await state.update_data(current_index=current_index)
    await show_card_for_trade(callback.message, callback.from_user.id, current_index, for_response)
    await callback.answer()

async def handle_card_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора карты для обмена"""
    card_id = int(callback.data.split('_')[2])
    card = db.get_card(card_id)
    if not card:
        await callback.answer("Карта не найдена")
        return

    await state.update_data(offered_card_id=card_id)
    await state.set_state(TradeStates.waiting_for_username)
    
    card_info = (
        f"Вы выбрали карту:\n"
        f"Название: {card[1]}\n"
        f"Редкость: {card[4]}\n"
        f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}"
    )
    
    await callback.message.answer_photo(
        photo=card[2],
        caption=f"{card_info}\n\nВведите @username пользователя для обмена:"
    )

async def handle_username_input(message: types.Message, state: FSMContext):
    """Обработка ввода username пользователя для обмена"""
    username = message.text.lstrip('@')
    target_user = db.get_user_by_username(username)
    
    if not target_user:
        await message.answer("Пользователь не найден")
        return
    
    if target_user[0] == message.from_user.id:
        await message.answer("Вы не можете обменяться картами с самим собой")
        return
    
    data = await state.get_data()
    offered_card = db.get_card(data['offered_card_id'])
    
    await state.update_data(target_user_id=target_user[0])
    await state.set_state(TradeStates.waiting_for_response)
    
    # Создаем клавиатуру для принятия/отклонения обмена
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_trade_{data['offered_card_id']}_{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_trade_{data['offered_card_id']}_{message.from_user.id}")
        ]
    ]
    
    # Отправляем предложение обмена
    trade_message = (
        f"📨 Предложение обмена\n"
        f"От: @{message.from_user.username or message.from_user.id}\n\n"
        f"Предлагает карту:\n"
        f"Название: {offered_card[1]}\n"
        f"Редкость: {offered_card[4]}\n"
        f"{'🔒 Ограниченная' if offered_card[3] else '🔓 Обычная'}"
    )
    
    await message.bot.send_photo(
        chat_id=target_user[0],
        photo=offered_card[2],
        caption=trade_message,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await message.answer("Предложение обмена отправлено! Ожидайте ответа.")

async def handle_trade_response(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на предложение обмена"""
    try:
        parts = callback.data.split('_')
        action = parts[1]
        second_user_id = int(parts[2])
        card_id = int(parts[3]) if len(parts) > 3 else None
        
        logging.info(f"=== TRADE RESPONSE HANDLER ===")
        logging.info(f"Action: {action}, Second User ID: {second_user_id}, Card ID: {card_id}")
        
        if action == "reject":
            # Отклоняем обмен
            logging.info(f"Trade rejected by {callback.from_user.id}")
            await state.clear()
            try:
                await callback.message.delete()
                logging.info(f"Deleted trade message {callback.message.message_id} for user {callback.from_user.id}")
            except Exception as e:
                logging.warning(f"Could not delete trade message {callback.message.message_id}: {e}")
                # Попытка отредактировать, если удаление не удалось
                try:
                    await callback.message.edit_caption(
                        caption=callback.message.caption + "\n\n❌ Обмен отклонен",
                        reply_markup=None
                    )
                except Exception as edit_e:
                    logging.warning(f"Could not edit trade message {callback.message.message_id}: {edit_e}")
            
            await callback.bot.send_message(
                chat_id=second_user_id,
                text="❌ Ваше предложение обмена было отклонено"
            )
        else:  # accept
            if card_id is None:
                logging.error("Card ID is required for accept action")
                await callback.answer("Ошибка: не удалось определить карту для обмена")
                return
                
            # Сохраняем данные в состоянии
            await state.update_data(
                sender_id=second_user_id,
                offered_card_id=card_id,
                current_index=0
            )
            await state.set_state(TradeStates.selecting_response_card)
            
            # Показываем первую карту для выбора
            await show_card_for_trade(callback.message, callback.from_user.id, 0, True)

        await callback.answer()
    except Exception as e:
        logging.error(f"Error in handle_trade_response: {e}")
        await callback.answer("Произошла ошибка при обработке ответа")
        await state.clear()

async def handle_response_card_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора карты для ответного обмена"""
    card_id = int(callback.data.split('_')[2])
    data = await state.get_data()
    
    # Проверяем наличие необходимых данных
    if 'sender_id' not in data or 'offered_card_id' not in data:
        await callback.message.answer("Ошибка: не удалось получить данные об обмене")
        await state.clear()
        return
    
    sender_id = data['sender_id']
    
    # Получаем информацию о картах
    response_card = db.get_card(card_id)
    offered_card = db.get_card(data['offered_card_id'])
    
    if not response_card or not offered_card:
        await callback.message.answer("Ошибка: одна из карт не найдена")
        await state.clear()
        return

    # Создаем клавиатуру для подтверждения обмена первым игроком
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Подтвердить обмен",
                callback_data=f"confirm_trade_{card_id}_{callback.from_user.id}"
            ),
            InlineKeyboardButton(text="❌ Отклонить обмен", callback_data=f"reject_trade_{card_id}_{callback.from_user.id}")
        ]
    ]

    # Отправляем сообщение первому игроку для подтверждения
    await callback.bot.send_photo(
        chat_id=sender_id,
        photo=response_card[2],
        caption=(
            f"Пользователь @{callback.from_user.username or callback.from_user.id} "
            f"предлагает вам обменять вашу карту \"{offered_card[1]}\" "
            f"на его карту \"{response_card[1]}\". Хотите подтвердить?"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    # Уведомляем второго игрока
    await callback.message.answer(
        "Ваше предложение отправлено. Ожидайте подтверждения первого игрока."
    )
    await callback.answer()

async def handle_trade_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения обмена первым игроком"""
    try:
        parts = callback.data.split('_')
        action = parts[1]
        card_id = int(parts[2]) # Карта второго игрока
        second_user_id = int(parts[3]) # ID второго игрока
        
        logging.info(f"=== TRADE CONFIRMATION HANDLER ===")
        logging.info(f"Action: {action}, Card ID: {card_id}, Second User ID: {second_user_id}")
        
        if action == "confirm":
            logging.info(f"Trade confirmed by {callback.from_user.id}")
            # Получаем данные из состояния (нужна карта, предложенная первым игроком)
            data = await state.get_data()
            if 'offered_card_id' not in data:
                # Пытаемся получить карту из контекста второго игрока (маловероятно, но на всякий случай)
                try:
                    second_user_key = StorageKey(bot_id=callback.bot.id, chat_id=second_user_id, user_id=second_user_id)
                    second_user_data = await dp.storage.get_data(key=second_user_key)
                    if 'offered_card_id' in second_user_data:
                         data['offered_card_id'] = second_user_data['offered_card_id']
                         logging.info("Restored offered_card_id from second user context")
                    else:
                        raise ValueError("Offered card ID not found in either context")
                except Exception as restore_e:
                     logging.error(f"Failed to restore offered_card_id: {restore_e}")
                     await callback.answer("Ошибка: не удалось найти исходную карту обмена. Попробуйте начать заново.")
                     await state.clear()
                     return
            
            offered_card_id = data['offered_card_id'] # Карта первого игрока
            logging.info(f"Using offered card ID: {offered_card_id}")
            
            # Выполняем обмен
            trade_successful = db.trade_cards(
                callback.from_user.id, second_user_id,
                offered_card_id, card_id
            )
            
            if trade_successful:
                logging.info("Trade completed successfully in DB")
                # Уведомляем обоих пользователей
                try:
                    await callback.message.delete()
                    logging.info(f"Deleted confirmation message {callback.message.message_id}")
                except Exception as e:
                    logging.warning(f"Could not delete confirmation message {callback.message.message_id}: {e}")
                    # Попытка отредактировать
                    try:
                        await callback.message.edit_caption(
                            caption=callback.message.caption + "\n\n✅ Обмен успешно завершен!",
                            reply_markup=None
                        )
                    except Exception as edit_e:
                         logging.warning(f"Could not edit confirmation message: {edit_e}")
                
                await callback.bot.send_message(
                    chat_id=second_user_id,
                    text="✅ Ваше предложение обмена было принято!"
                )
                await callback.answer("Обмен успешно завершен!")
            else:
                 logging.error("Database trade failed")
                 await callback.answer("Ошибка базы данных при обмене")
                 await callback.bot.send_message(
                    chat_id=second_user_id,
                    text="Произошла ошибка базы данных при обмене"
                )
            
        elif action == "reject":
            logging.info(f"Trade rejected by {callback.from_user.id}")
            await state.clear()
            try:
                await callback.message.delete()
                logging.info(f"Deleted confirmation message {callback.message.message_id}")
            except Exception as e:
                 logging.warning(f"Could not delete confirmation message {callback.message.message_id}: {e}")
                 # Попытка отредактировать
                 try:
                     await callback.message.edit_caption(
                        caption=callback.message.caption + "\n\n❌ Обмен отклонен",
                        reply_markup=None
                    )
                 except Exception as edit_e:
                     logging.warning(f"Could not edit confirmation message: {edit_e}")
            await callback.bot.send_message(
                chat_id=second_user_id,
                text="❌ Ваше предложение обмена было отклонено"
            )
            await callback.answer("Обмен отклонен")

    except Exception as e:
        logging.error(f"Error in handle_trade_confirmation: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при подтверждении обмена")
    finally:
        await state.clear()
        # Очистим состояние и у второго пользователя
        try:
            parts_clear = callback.data.split('_')
            second_user_id_clear = int(parts_clear[3])
            second_user_key_clear = StorageKey(bot_id=callback.bot.id, chat_id=second_user_id_clear, user_id=second_user_id_clear)
            await dp.storage.set_state(key=second_user_key_clear, state=None)
            await dp.storage.set_data(key=second_user_key_clear, data={})
            logging.info(f"Cleared state for second user {second_user_id_clear}")
        except Exception as clear_e:
             logging.error(f"Error clearing state for second user in finally block: {clear_e}")

async def cancel_trade(callback: types.CallbackQuery, state: FSMContext):
    """Отмена процесса обмена"""
    logging.info(f"Trade cancelled by user {callback.from_user.id}")
    await state.clear()
    try:
        await callback.message.delete()
        logging.info(f"Deleted trade message {callback.message.message_id}")
    except Exception as e:
        logging.warning(f"Could not delete trade message {callback.message.message_id}: {e}")
        try:
            await callback.message.edit_text("Обмен отменен.")
        except Exception as edit_e:
            logging.warning(f"Could not edit trade message {callback.message.message_id}: {edit_e}")
    await callback.answer() 