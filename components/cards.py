from aiogram import types
import datetime
import logging
import asyncio
from database import Database
from dispatcher import bot

db = Database('film_bot.db')

# Словарь для отслеживания отправленных уведомлений
notified_users = {}

# Словарь с очками за карты разных редкостей
CARD_POINTS = {
    'Base': 250,
    'Medium': 350,
    'Episode': 500,
    'Muth': 1500,
    'Legendary': 3000,
    'Limited': 10000
}

async def check_and_notify_users():
    """Проверяет время и отправляет уведомления пользователям"""
    while True:
        try:
            # Получаем всех пользователей с активным Film Pass
            users_with_pass = db.get_all_users_with_pass()
            logging.info(f"Found {len(users_with_pass)} users with active pass")
            
            current_time = datetime.datetime.now()
            
            for user_id in users_with_pass:
                try:
                    # Пропускаем пользователя, если уведомление уже было отправлено
                    if user_id[0] in notified_users:
                        continue
                        
                    # Получаем состояние пользователя
                    state = db.get_state(user_id[0])
                    if not state or not state[0]:  # state[0] - это state_card
                        logging.info(f"No state_card for user {user_id[0]}")
                        continue
                    
                    try:
                        # Пробуем прочитать время в новом формате
                        last_card_time = datetime.datetime.strptime(state[0], '%H:%M:%S')
                    except ValueError:
                        try:
                            # Если не получилось, пробуем конвертировать из старого формата timestamp
                            timestamp = int(state[0])
                            last_card_time = datetime.datetime.fromtimestamp(timestamp)
                            # Сохраняем в новом формате
                            new_time_str = last_card_time.strftime('%H:%M:%S')
                            db.update_state(user_id[0], "state_card", new_time_str)
                            logging.info(f"Converted old timestamp {timestamp} to new format {new_time_str}")
                        except (ValueError, TypeError) as e:
                            logging.error(f"Error converting time for user {user_id[0]}: {e}")
                            continue
                    
                    last_card_time = last_card_time.replace(
                        year=current_time.year,
                        month=current_time.month,
                        day=current_time.day
                    )
                    
                    # Если текущее время меньше времени последней карты, 
                    # значит карта была получена вчера
                    if current_time.time() < last_card_time.time():
                        last_card_time = last_card_time - datetime.timedelta(days=1)
                    
                    time_passed = (current_time - last_card_time).total_seconds()
                    
                    logging.info(f"User {user_id[0]}:")
                    logging.info(f"  Last card time: {last_card_time.strftime('%H:%M:%S')}")
                    logging.info(f"  Current time: {current_time.strftime('%H:%M:%S')}")
                    logging.info(f"  Time passed: {int(time_passed)} seconds")
                    
                    # 2 часа для пользователей с пассом (7200 секунд)
                    if time_passed >= 7200:
                        # Отправляем уведомление
                        await bot.send_message(
                            user_id[0],
                            "🎉 Время прошло! Теперь вы можете получить карту!"
                        )
                        # Добавляем пользователя в список тех, кому уже отправлено уведомление
                        notified_users[user_id[0]] = True
                        logging.info(f"Sent notification to user {user_id[0]}")
                except Exception as e:
                    logging.error(f"Error processing user {user_id[0]}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error in check_and_notify_users: {e}")
            
        await asyncio.sleep(5)  # Проверяем каждые 5 секунд

# Запускаем проверку уведомлений
def start_notification_checker():
    """Запускает проверку уведомлений в фоновом режиме"""
    asyncio.create_task(check_and_notify_users())
    logging.info("Notification checker started")

async def get_card(message: types.Message):
    """Получение карты пользователем"""
    # Удаляем пользователя из списка уведомленных при получении карты
    if message.from_user.id in notified_users:
        del notified_users[message.from_user.id]
        
    user = db.get_user(message.from_user.id)
    if not user:
        logging.error(f"User {message.from_user.id} not found")
        db.add_user(message.from_user.id)
        user = db.get_user(message.from_user.id)
        if not user:
            await message.answer("Ошибка: не удалось создать пользователя")
            return

    # Проверка на бан
    if db.is_banned(message.from_user.id):
        await message.answer("Вы забанены и не можете получать карты")
        return

    # Проверяем количество попыток
    attempts = user[8]
    if attempts == 0:
        # Если нет попыток, проверяем время последнего получения карты
        current_time = datetime.datetime.now()
        state = db.get_state(message.from_user.id)
        
        # Если state не существует или не содержит state_card, создаем его
        if not state or not state[0]:
            current_time_str = current_time.strftime('%H:%M:%S')
            db.update_state(message.from_user.id, "state_card", current_time_str)
            logging.info(f"Created new state for user {message.from_user.id}")
            state = db.get_state(message.from_user.id)
        
        try:
            # Пробуем прочитать время в новом формате
            last_card_time = datetime.datetime.strptime(state[0], '%H:%M:%S')
        except ValueError:
            try:
                # Если не получилось, пробуем конвертировать из старого формата timestamp
                timestamp = int(state[0])
                last_card_time = datetime.datetime.fromtimestamp(timestamp)
                # Сохраняем в новом формате
                new_time_str = last_card_time.strftime('%H:%M:%S')
                db.update_state(message.from_user.id, "state_card", new_time_str)
                logging.info(f"Converted old timestamp {timestamp} to new format {new_time_str}")
            except (ValueError, TypeError) as e:
                # Если и это не получилось, создаем новое время
                last_card_time = current_time
                new_time_str = current_time.strftime('%H:%M:%S')
                db.update_state(message.from_user.id, "state_card", new_time_str)
                logging.error(f"Error converting time, using current time: {e}")
        
        last_card_time = last_card_time.replace(
            year=current_time.year,
            month=current_time.month,
            day=current_time.day
        )
        
        # Если текущее время меньше времени последней карты, 
        # значит карта была получена вчера
        if current_time.time() < last_card_time.time():
            last_card_time = last_card_time - datetime.timedelta(days=1)
        
        time_diff = (current_time - last_card_time).total_seconds()
        
        # Определяем время ожидания в зависимости от наличия pass
        has_pass = db.has_active_pass(message.from_user.id)
        wait_time = 7200 if has_pass else 14400  # 2 часа с pass, 4 часа без (в секундах)
        
        if time_diff < wait_time:
            remaining_time = wait_time - time_diff
            
            # Если у пользователя есть пасс, отправляем уведомление о времени
            if has_pass:
                next_time = (last_card_time + datetime.timedelta(seconds=wait_time)).strftime('%H:%M:%S')
                await message.answer(
                    f"⏳ Подождите еще {int(remaining_time/3600)} ч. {int((remaining_time%3600)/60)} мин. перед следующей попыткой\n"
                    f"⏰ Следующая попытка будет доступна в {next_time}"
                )
            else:
                await message.answer(
                    f"⏳ Подождите еще {int(remaining_time/3600)} ч. {int((remaining_time%3600)/60)} мин. перед следующей попыткой"
                )
            return

    # Если есть попытки, уменьшаем их на 1
    if attempts > 0:
        db.update_attempts(message.from_user.id, attempts - 1)
        logging.info(f"User {message.from_user.id} used one attempt. Remaining: {attempts - 1}")

    # Получаем случайную карту
    card = db.get_random_card()
    if not card:
        await message.answer("К сожалению, сейчас нет доступных карт")
        return

    # Получаем очки за карту
    points = CARD_POINTS.get(card[4], 0)  # card[4] - это редкость карты
    
    # Добавляем карту пользователю
    logging.info(f"Adding card {card[0]} to user {message.from_user.id}")
    if not db.add_card_to_user(message.from_user.id, card[0]):
        logging.error(f"Failed to add card {card[0]} to user {message.from_user.id}")
        await message.answer("Произошла ошибка при сохранении карты")
        return
        
    # Проверяем, что карта добавилась
    updated_user = db.get_user(message.from_user.id)
    logging.info(f"User data after adding card: {updated_user}")
    
    # Обновляем очки пользователя
    db.update_user_points(message.from_user.id, points, points)
    
    # Обновляем время получения карты в state
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    db.update_state(message.from_user.id, "state_card", current_time)
    logging.info(f"Updated state_card for user {message.from_user.id} to {current_time}")
    
    # Формируем сообщение о полученной карте
    card_info = (
        f"🎉 Поздравляем! Вы получили карту:\n\n"
        f"Название: {card[1]}\n"
        f"Редкость: {card[4]}\n"
        f"Получено очков: {points}\n"
        f"{'🔒 Ограниченная' if card[3] else '🔓 Обычная'}"
    )
    
    if attempts > 0:
        card_info += f"\n\nОсталось попыток: {attempts - 1}"
    
    await message.answer_photo(
        photo=card[2],
        caption=card_info
    ) 