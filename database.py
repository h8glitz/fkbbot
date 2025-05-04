import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple
import time
import logging
import random

class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self.admin_id = 6087110668 # ID администратора
        self.create_tables()

    def _get_connection(self):
        """Получение соединения с базой данных с обработкой блокировок"""
        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            try:
                conn = sqlite3.connect(self.db_file, timeout=20)
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    attempt += 1
                    if attempt == max_attempts:
                        raise
                    time.sleep(0.1)
                else:
                    raise

    def create_tables(self):
        """Создание таблиц в базе данных"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            # Создание таблицы users
            cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                cards TEXT DEFAULT '',
                points INTEGER DEFAULT 0,
                shop_points INTEGER DEFAULT 0,
                family TEXT DEFAULT '',
                donate INTEGER DEFAULT 0,
                pass TEXT DEFAULT NULL,
                attempts INTEGER DEFAULT 0,
                season_points INTEGER DEFAULT 0,
                dice_rolls_count INTEGER DEFAULT 0,
                last_dice_roll_month INTEGER DEFAULT 0,
                donate_balance INTEGER DEFAULT 0
            )
            ''')

            # Создание таблицы family
            cur.execute('''
            CREATE TABLE IF NOT EXISTS family (
                leader_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                avatar_url TEXT,
                description TEXT,
                members TEXT DEFAULT '',
                points INTEGER DEFAULT 0
            )
            ''')

            # Создание таблицы states
            cur.execute('''
            CREATE TABLE IF NOT EXISTS states (
                user_id INTEGER PRIMARY KEY,
                state_card TEXT,
                state_cube TEXT
            )
            ''')

            # Создание таблицы cards
            cur.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                photo_url TEXT NOT NULL,
                limited INTEGER DEFAULT 0,
                rare TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                price INTEGER DEFAULT 0,
                counts INTEGER DEFAULT 0
            )
            ''')

            # Создание таблицы shop
            cur.execute('''
            CREATE TABLE IF NOT EXISTS shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price INTEGER NOT NULL,
                time_to_out TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                card_id INTEGER,
                FOREIGN KEY (card_id) REFERENCES cards(card_id)
            )
            ''')

            # Создание таблицы dice_stats
            cur.execute('''
            CREATE TABLE IF NOT EXISTS dice_stats (
                user_id INTEGER PRIMARY KEY,
                count_games INTEGER DEFAULT 0,
                win INTEGER DEFAULT 0,
                loss INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')

            conn.commit()
        finally:
            if conn:
                conn.close()

    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id == self.admin_id

    # Методы для работы с картами (админ-функционал)
    def add_card(self, card_name: str, photo_url: str, limited: int, rare: str, points: int, 
                 price: int, counts: int) -> int:
        """Добавление новой карты"""
        conn = None
        card_id = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('''
            INSERT INTO cards (card_name, photo_url, limited, rare, points, price, counts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (card_name, photo_url, limited, rare, points, price, counts))
            
            card_id = cur.lastrowid
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        return card_id

    def get_card(self, card_id: int) -> Optional[Tuple]:
        """Получение информации о карте по ID"""
        conn = None
        card = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT * FROM cards WHERE card_id = ?', (card_id,))
            card = cur.fetchone()
        finally:
            if conn:
                conn.close()
        return card

    def update_card(self, card_id: int, field: str, value):
        """Обновление поля карты"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute(f'UPDATE cards SET {field} = ? WHERE card_id = ?', (value, card_id))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def delete_card(self, card_id: int):
        """Удаление карты"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('DELETE FROM cards WHERE card_id = ?', (card_id,))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def get_all_cards(self) -> List[Tuple]:
        """Получение списка всех карт"""
        conn = None
        cards = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT * FROM cards')
            cards = cur.fetchall()
        finally:
            if conn:
                conn.close()
        return cards

    def add_user(self, user_id: int):
        """Добавление нового пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            # Проверяем, существует ли пользователь
            cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if cur.fetchone() is None:
                # Добавляем нового пользователя с дефолтным значением pass
                cur.execute('''
                INSERT INTO users 
                (user_id, username, cards, points, shop_points, family, donate, pass, attempts) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, None, "", 0, 0, "", 0, '2025-03-03 23:38:19', 0))
                
                # Создаем запись в таблице states
                cur.execute('INSERT INTO states (user_id) VALUES (?)', (user_id,))
                conn.commit()
                logging.info(f"Created new user with ID {user_id} with default pass")
            else:
                logging.info(f"User {user_id} already exists")

            # Проверяем создание пользователя
            cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user_data = cur.fetchone()
            logging.info(f"User data after creation/check: {user_data}")

        except Exception as e:
            logging.error(f"Error creating user {user_id}: {e}")
        finally:
            if conn:
                conn.close()

    def get_user(self, user_id: int):
        """Получение данных пользователя"""
        conn = None
        user = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cur.fetchone()
        finally:
            if conn:
                conn.close()
        return user

    def update_user_field(self, user_id: int, field: str, value):
        """Обновление поля пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Проверяем существование пользователя
            cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            if not cur.fetchone():
                # Если пользователя нет, создаем его
                self.add_user(user_id)
            
            # Выполняем обновление
            query = 'UPDATE users SET {} = ? WHERE user_id = ?'.format(field)
            cur.execute(query, (value, user_id))
            conn.commit()
            
            # Проверяем обновление
            cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            updated_user = cur.fetchone()
            logging.info(f"Updated user {user_id} field {field}. New value: {value}")
            logging.info(f"Updated user data: {updated_user}")
            return True
        except Exception as e:
            logging.error(f"Error updating user {user_id} field {field}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def create_family(self, leader_id: int, name: str, avatar_url: str, description: str):
        """Создание новой семьи"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Проверяем, не является ли пользователь уже членом какой-либо семьи
            cur.execute('SELECT family FROM users WHERE user_id = ?', (leader_id,))
            user_family = cur.fetchone()
            if user_family and user_family[0]:
                return False
            
            # Создаем новую семью
            cur.execute('''
            INSERT INTO family (leader_id, name, avatar_url, description, members)
            VALUES (?, ?, ?, ?, ?)
            ''', (leader_id, name, avatar_url, description, str(leader_id)))
            
            # Обновляем поле family у пользователя
            cur.execute('UPDATE users SET family = ? WHERE user_id = ?', (name, leader_id))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error creating family: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_family(self, family_name: str):
        """Получение информации о семье"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            logging.info(f"Searching for family with name: {family_name}")
            cur.execute('SELECT * FROM family WHERE name = ?', (family_name,))
            family = cur.fetchone()
            logging.info(f"Found family: {family}")
            return family
        finally:
            if conn:
                conn.close()

    def get_family_by_leader(self, leader_id: int):
        """Получение информации о семье по ID лидера"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT * FROM family WHERE leader_id = ?', (leader_id,))
            return cur.fetchone()
        finally:
            if conn:
                conn.close()

    def add_family_member(self, family_name: str, user_id: int) -> bool:
        """Добавление участника в семью"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем текущих участников
            cur.execute('SELECT members FROM family WHERE name = ?', (family_name,))
            result = cur.fetchone()
            if not result:
                return False
            
            members = result[0].split(',') if result[0] else []
            if str(user_id) in members:
                return False
            
            # Добавляем нового участника
            members.append(str(user_id))
            new_members = ','.join(members)
            
            # Обновляем список участников
            cur.execute('UPDATE family SET members = ? WHERE name = ?', (new_members, family_name))
            
            # Обновляем поле family у пользователя
            cur.execute('UPDATE users SET family = ? WHERE user_id = ?', (family_name, user_id))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding family member: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_family_members(self, family_name: str) -> List[Tuple]:
        """Получение списка участников семьи"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT members FROM family WHERE name = ?', (family_name,))
            result = cur.fetchone()
            if not result or not result[0]:
                return []
            
            member_ids = [int(id) for id in result[0].split(',') if id]
            members = []
            
            for member_id in member_ids:
                cur.execute('SELECT user_id, username FROM users WHERE user_id = ?', (member_id,))
                member = cur.fetchone()
                if member:
                    members.append(member)
            
            return members
        finally:
            if conn:
                conn.close()

    def update_state(self, user_id: int, state_type: str, value: str):
        """Обновление состояния пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Проверяем, существует ли запись для пользователя
            cur.execute('SELECT user_id FROM states WHERE user_id = ?', (user_id,))
            if not cur.fetchone():
                # Если записи нет, создаем ее
                cur.execute('INSERT INTO states (user_id) VALUES (?)', (user_id,))
            
            # Обновляем значение
            cur.execute(f'UPDATE states SET {state_type} = ? WHERE user_id = ?', (value, user_id))
            conn.commit()
            
            # Проверяем, что значение обновилось
            cur.execute(f'SELECT {state_type} FROM states WHERE user_id = ?', (user_id,))
            updated_value = cur.fetchone()
            logging.info(f"Updated {state_type} for user {user_id} to {value}, verified: {updated_value}")
        except Exception as e:
            logging.error(f"Error updating state for user {user_id}: {e}")
        finally:
            if conn:
                conn.close()

    def get_state(self, user_id: int):
        """Получение состояний пользователя"""
        conn = None
        state = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT state_card, state_cube FROM states WHERE user_id = ?', (user_id,))
            state = cur.fetchone()
        finally:
            if conn:
                conn.close()
        return state

    def recreate_cards_table(self):
        """Пересоздание таблицы cards"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Удаляем существующую таблицу
            cur.execute('DROP TABLE IF EXISTS cards')
            
            # Создаем таблицу заново
            cur.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                photo_url TEXT NOT NULL,
                limited INTEGER DEFAULT 0,
                rare TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                price INTEGER DEFAULT 0,
                counts INTEGER DEFAULT 0
            )
            ''')
            
            conn.commit()
        finally:
            if conn:
                conn.close()

    def update_user_points(self, user_id: int, points: int, shop_points: int):
        """Обновление очков пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('''
            UPDATE users 
            SET points = points + ?, 
                shop_points = shop_points + ?, 
                season_points = season_points + ?
            WHERE user_id = ?
            ''', (points, shop_points, points, user_id))
            
            conn.commit()
        finally:
            if conn:
                conn.close()

    def update_attempts(self, user_id: int, attempts: int):
        """Обновление попыток пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('UPDATE users SET attempts = ? WHERE user_id = ?', (attempts, user_id))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def get_random_card(self) -> Optional[Tuple]:
        """Получение случайной карты с учетом шансов"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем все доступные карты (не ограниченные и с counts > 0)
            cur.execute('''
                SELECT * FROM cards 
                WHERE limited = 0 
                AND counts > 0 
                AND card_id > 0
                AND card_name IS NOT NULL 
                AND photo_url IS NOT NULL
            ''')
            cards = cur.fetchall()
            
            if not cards:
                logging.info("No available cards found")
                return None
                
            # Распределяем шансы по редкости
            rarity_chances = {
                'Base': 0.35,      # 35%
                'Medium': 0.25,    # 25%
                'Episode': 0.20,   # 20%
                'Muth': 0.15,      # 15%
                'Legendary': 0.05  # 5%
            }
            
            # Выбираем редкость
            rarity = random.choices(
                list(rarity_chances.keys()),
                weights=list(rarity_chances.values())
            )[0]
            
            # Фильтруем карты по выбранной редкости
            cards_of_rarity = [card for card in cards if card[4] == rarity]
            
            if not cards_of_rarity:
                # Если нет карт выбранной редкости, берем случайную из доступных
                logging.info(f"No cards of rarity {rarity} found, selecting random card")
                selected_card = random.choice(cards)
            else:
                # Выбираем случайную карту из отфильтрованных
                selected_card = random.choice(cards_of_rarity)
            
            # Проверяем, что выбранная карта существует и валидна
            if not selected_card or selected_card[0] <= 0:
                logging.error("Invalid card selected")
                return None
            
            # Уменьшаем counts у выбранной карты
            cur.execute('UPDATE cards SET counts = counts - 1 WHERE card_id = ?', (selected_card[0],))
            conn.commit()
            
            logging.info(f"Selected card: {selected_card}")
            return selected_card
            
        except Exception as e:
            logging.error(f"Error getting random card: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_limited_card(self) -> Optional[Tuple]:
        """Получение случайной ограниченной карты"""
        conn = None
        limited_cards = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT * FROM cards WHERE limited = 1')
            limited_cards = cur.fetchall()
            
            if not limited_cards:
                return None
            
            selected_card = random.choice(limited_cards)
        finally:
            if conn:
                conn.close()
        return selected_card

    def add_attempts(self, user_id: int, attempts: int):
        """Добавление попыток пользователю"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('UPDATE users SET attempts = attempts + ? WHERE user_id = ?', (attempts, user_id))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def ban_user(self, user_id: int):
        """Бан пользователя (установка attempts в -1)"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('UPDATE users SET attempts = -1 WHERE user_id = ?', (user_id,))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def unban_user(self, user_id: int):
        """Разбан пользователя (установка attempts в 0)"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('UPDATE users SET attempts = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def is_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        conn = None
        result = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT attempts FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
        finally:
            if conn:
                conn.close()
        return result and result[0] == -1

    def get_user_by_username(self, username: str):
        """Получение данных пользователя по username"""
        conn = None
        user = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Убираем @ если он есть в начале username
            username = username.lstrip('@')
            logging.info(f"Searching for user with username: {username}")
            
            # Ищем пользователя по точному совпадению username
            cur.execute('SELECT * FROM users WHERE LOWER(username) = LOWER(?)', (username,))
            user = cur.fetchone()
            
            if not user:
                logging.info(f"User with username {username} not found")
                # Давайте посмотрим всех пользователей в базе для отладки
                cur.execute('SELECT user_id, username FROM users')
                all_users = cur.fetchall()
                logging.info(f"All users in database: {all_users}")
            else:
                logging.info(f"Found user: {user}")
                
        except Exception as e:
            logging.error(f"Error getting user by username {username}: {e}")
        finally:
            if conn:
                conn.close()
        return user

    def update_username(self, user_id: int, username: str):
        """Обновление username пользователя"""
        if username is None:
            return
            
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Убираем @ если он есть в начале username
            username = username.lstrip('@')
            
            cur.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def recreate_users_table(self):
        """Пересоздание таблицы users"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Сохраняем текущие данные
            cur.execute('SELECT * FROM users')
            old_data = cur.fetchall()
            
            # Удаляем старую таблицу
            cur.execute('DROP TABLE IF EXISTS users')
            
            # Создаем новую таблицу
            cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                cards TEXT DEFAULT '',
                points INTEGER DEFAULT 0,
                shop_points INTEGER DEFAULT 0,
                family TEXT DEFAULT '',
                donate INTEGER DEFAULT 0,
                pass TEXT DEFAULT NULL,
                attempts INTEGER DEFAULT 0
            )
            ''')
            
            # Восстанавливаем данные
            for user in old_data:
                if len(user) >= 8:  # Проверяем, что у нас есть все поля
                    cur.execute('''
                    INSERT INTO users (user_id, cards, points, shop_points, family, donate, pass, attempts)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user[0], user[1], user[2], user[3], user[4], user[5], user[6], user[7]))
            
            conn.commit()
        finally:
            if conn:
                conn.close()

    def get_user_cards(self, user_id: int) -> List[Tuple]:
        """Получение всех карт пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем список карт пользователя
            cur.execute('SELECT cards FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
            
            if not result or not result[0] or result[0] == '':
                logging.info(f"No cards found for user {user_id}")
                return []
            
            # Преобразуем строку с ID карт в список и берем только уникальные значения
            card_ids = list(set([int(card_id) for card_id in result[0].split(',') if card_id.strip()]))
            logging.info(f"Found unique card IDs for user {user_id}: {card_ids}")
            
            # Получаем информацию о каждой уникальной карте
            cards = []
            for card_id in card_ids:
                cur.execute('SELECT * FROM cards WHERE card_id = ?', (card_id,))
                card = cur.fetchone()
                if card:
                    cards.append(card)
                    logging.info(f"Found card {card_id} info: {card}")
                else:
                    logging.warning(f"Card with ID {card_id} not found in database")
            
            logging.info(f"Retrieved {len(cards)} unique cards for user {user_id}")
            return cards
            
        except Exception as e:
            logging.error(f"Error getting cards for user {user_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_user_cards_by_rarity(self, user_id: int, rarity: str) -> List[Tuple]:
        """Получение карт пользователя определенной редкости"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем список карт пользователя
            cur.execute('SELECT cards FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
            
            if not result or not result[0] or result[0] == '':
                logging.info(f"No cards found for user {user_id}")
                return []
            
            # Преобразуем строку с ID карт в список
            card_ids = [int(card_id) for card_id in result[0].split(',') if card_id.strip()]
            logging.info(f"Found card IDs for user {user_id}: {card_ids}")
            
            # Получаем информацию о каждой карте нужной редкости
            cards = []
            for card_id in card_ids:
                cur.execute('SELECT * FROM cards WHERE card_id = ? AND rare = ?', (card_id, rarity))
                card = cur.fetchone()
                if card:
                    cards.append(card)
                    logging.info(f"Found card {card_id} info: {card}")
                else:
                    logging.warning(f"Card with ID {card_id} not found in database or wrong rarity")
            
            logging.info(f"Retrieved {len(cards)} cards of rarity {rarity} for user {user_id}")
            return cards
            
        except Exception as e:
            logging.error(f"Error getting cards of rarity {rarity} for user {user_id}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def clean_user_cards(self, user_id: int):
        """Очистка карт пользователя"""
        self.update_user_field(user_id, 'cards', '')

    def add_card_to_user(self, user_id: int, card_id: int) -> bool:
        """Добавление карты пользователю"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        cards = user[2].split(',') if user[2] else []
        cards.append(str(card_id))
        new_cards = ','.join(cards)
        
        return self.update_user_field(user_id, 'cards', new_cards)

    def remove_card_from_user(self, user_id: int, card_id: int) -> bool:
        """Удаление карты у пользователя"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        cards = user[2].split(',') if user[2] else []
        if str(card_id) not in cards:
            return False
        
        cards.remove(str(card_id))
        new_cards = ','.join(cards)
        
        return self.update_user_field(user_id, 'cards', new_cards)

    def trade_cards(self, user1_id: int, user2_id: int, card1_id: int, card2_id: int) -> bool:
        """Обмен картами между пользователями"""
        conn = None
        try:
            conn = self._get_connection()
            conn.execute('BEGIN TRANSACTION')
            
            # Проверяем, что обе карты существуют
            card1 = self.get_card(card1_id)
            card2 = self.get_card(card2_id)
            if not card1 or not card2:
                raise ValueError("Одна из карт не существует")
            
            # Проверяем, что у пользователей есть соответствующие карты
            user1_cards = self.get_user_cards(user1_id)
            user2_cards = self.get_user_cards(user2_id)
            
            if not any(c[0] == card1_id for c in user1_cards) or not any(c[0] == card2_id for c in user2_cards):
                raise ValueError("У одного из пользователей нет указанной карты")
            
            # Удаляем карты у текущих владельцев
            if not (self.remove_card_from_user(user1_id, card1_id) and 
                   self.remove_card_from_user(user2_id, card2_id)):
                raise ValueError("Ошибка при удалении карт")
            
            # Добавляем карты новым владельцам
            if not (self.add_card_to_user(user1_id, card2_id) and 
                   self.add_card_to_user(user2_id, card1_id)):
                raise ValueError("Ошибка при добавлении карт")
            
            conn.commit()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"Error during trade between users {user1_id} and {user2_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_random_card_by_rarity(self, rarity: str) -> Optional[Tuple]:
        """Получение случайной карты определенной редкости"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM cards 
                WHERE rarity = ? 
                ORDER BY RANDOM() 
                LIMIT 1
            """, (rarity,))
            
            card = cursor.fetchone()
            conn.close()
            
            return card
        except Exception as e:
            logging.error(f"Error getting random card by rarity: {e}")
            return None

    def add_pass(self, user_id: int, months: int = 1) -> bool:
        """Добавление Film Pass пользователю"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем текущую дату
            current_date = datetime.now()
            logging.info(f"Current date: {current_date}")
            
            # Если у пользователя уже есть пасс, добавляем к существующей дате
            cur.execute('SELECT pass FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
            
            if result and result[0]:
                try:
                    # Преобразуем строку в datetime
                    current_pass_date = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                    logging.info(f"Existing pass date: {current_pass_date}")
                    if current_pass_date > current_date:
                        # Если пасс еще активен, добавляем к существующей дате
                        new_date = current_pass_date
                        logging.info(f"Using existing pass date: {new_date}")
                    else:
                        # Если пасс истек, начинаем с текущей даты
                        new_date = current_date
                        logging.info(f"Pass expired, using current date: {new_date}")
                except Exception as e:
                    logging.error(f"Error parsing existing pass date: {e}")
                    new_date = current_date
                    logging.info(f"Error parsing date, using current date: {new_date}")
            else:
                new_date = current_date
                logging.info(f"No existing pass, using current date: {new_date}")
            
            # Добавляем месяцы
            if months == 1:
                new_date = new_date.replace(month=new_date.month + 1)
            else:
                new_date = new_date.replace(year=new_date.year + (new_date.month + months - 1) // 12,
                                          month=(new_date.month + months - 1) % 12 + 1)
            logging.info(f"New pass date after adding {months} months: {new_date}")
            
            # Преобразуем дату в строку
            pass_date_str = new_date.strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"Final pass date string: {pass_date_str}")
            
            # Обновляем поле pass
            cur.execute('UPDATE users SET pass = ? WHERE user_id = ?', (pass_date_str, user_id))
            conn.commit()
            
            # Проверяем, что дата сохранилась правильно
            cur.execute('SELECT pass FROM users WHERE user_id = ?', (user_id,))
            saved_pass = cur.fetchone()
            logging.info(f"Saved pass in database: {saved_pass[0] if saved_pass else None}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error adding pass to user {user_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_pass_expiry(self, user_id: int) -> Optional[datetime]:
        """Получение даты истечения Film Pass"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT pass FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
            
            if result and result[0]:
                try:
                    # Преобразуем строку в datetime
                    expiry_date = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                    logging.info(f"Retrieved pass expiry date for user {user_id}: {expiry_date}")
                    return expiry_date
                except Exception as e:
                    logging.error(f"Error converting pass date string to datetime for user {user_id}: {e}")
                    logging.error(f"Invalid date string: {result[0]}")
                    return None
            else:
                logging.info(f"No pass found for user {user_id}")
                return None
        except Exception as e:
            logging.error(f"Error getting pass expiry for user {user_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def has_active_pass(self, user_id: int) -> bool:
        """Проверка наличия активного Film Pass"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('SELECT pass FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
            
            if not result or not result[0]:
                logging.info(f"User {user_id} has no pass")
                return False
            
            has_pass = result[0] > current_time
            logging.info(f"Pass check for user {user_id}:")
            logging.info(f"  - Pass expiry: {result[0]}")
            logging.info(f"  - Current time: {current_time}")
            logging.info(f"  - Is active: {has_pass}")
            
            return has_pass
            
        except Exception as e:
            logging.error(f"Error checking pass status for user {user_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def recreate_database(self):
        """Пересоздание всей базы данных"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Удаляем все таблицы
            cur.execute('DROP TABLE IF EXISTS users')
            cur.execute('DROP TABLE IF EXISTS family')
            cur.execute('DROP TABLE IF EXISTS states')
            cur.execute('DROP TABLE IF EXISTS cards')
            
            # Создаем таблицы заново
            self.create_tables()
            
            conn.commit()
            logging.info("Database recreated successfully")
        except Exception as e:
            logging.error(f"Error recreating database: {e}")
        finally:
            if conn:
                conn.close()

    def remove_family_member(self, family_name: str, user_id: int) -> bool:
        """Удаление участника из семьи"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем текущих участников
            cur.execute('SELECT members FROM family WHERE name = ?', (family_name,))
            result = cur.fetchone()
            if not result:
                return False
            
            members = result[0].split(',') if result[0] else []
            if str(user_id) not in members:
                return False
            
            # Удаляем участника
            members.remove(str(user_id))
            new_members = ','.join(members)
            
            # Обновляем список участников
            cur.execute('UPDATE family SET members = ? WHERE name = ?', (new_members, family_name))
            
            # Очищаем поле family у пользователя
            cur.execute('UPDATE users SET family = ? WHERE user_id = ?', ("", user_id))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error removing family member: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def disband_family(self, family_name: str) -> bool:
        """Расформирование семьи"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Получаем всех участников семьи
            cur.execute('SELECT members FROM family WHERE name = ?', (family_name,))
            result = cur.fetchone()
            if not result:
                return False
            
            members = result[0].split(',') if result[0] else []
            
            # Очищаем поле family у всех участников
            for member_id in members:
                cur.execute('UPDATE users SET family = ? WHERE user_id = ?', ("", member_id))
            
            # Удаляем семью
            cur.execute('DELETE FROM family WHERE name = ?', (family_name,))
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error disbanding family: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def add_season_points(self, user_id: int, points: int) -> bool:
        """Добавление сезонных очков пользователю"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('UPDATE users SET season_points = season_points + ? WHERE user_id = ?', (points, user_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding season points: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_user_season_points(self, user_id: int) -> int:
        """Получение сезонных очков пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT season_points FROM users WHERE user_id = ?', (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0
        finally:
            if conn:
                conn.close()

    def get_top_users_by_season_points(self, limit: int = 10) -> List[Tuple]:
        """Получение топ пользователей по сезонным очкам"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            cur.execute('''
                SELECT user_id, username, season_points 
                FROM users 
                WHERE season_points > 0 
                ORDER BY season_points DESC 
                LIMIT ?
            ''', (limit,))
            return cur.fetchall()
        finally:
            if conn:
                conn.close()

    def get_dice_rolls_count(self, user_id):
        """Получение количества бросков кубика за текущий месяц"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        try:
            # Получаем текущий месяц
            current_month = datetime.now().strftime('%Y-%m')
            
            # Получаем данные о бросках
            c.execute('SELECT dice_rolls_count, last_dice_roll_month FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            
            if not result:
                return 0
                
            rolls_count, last_month = result
            
            # Если месяц изменился, сбрасываем счетчик
            if last_month != current_month:
                c.execute('UPDATE users SET dice_rolls_count = 0, last_dice_roll_month = ? WHERE user_id = ?',
                         (current_month, user_id))
                conn.commit()
                return 0
                
            return rolls_count
            
        except Exception as e:
            logging.error(f"Error getting dice rolls count: {e}")
            return 0
        finally:
            conn.close()

    def increment_dice_rolls(self, user_id):
        """Увеличение счетчика бросков кубика"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        try:
            current_month = datetime.now().strftime('%Y-%m')
            
            c.execute('''UPDATE users 
                        SET dice_rolls_count = dice_rolls_count + 1,
                            last_dice_roll_month = ?
                        WHERE user_id = ?''',
                     (current_month, user_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error incrementing dice rolls: {e}")
            return False
        finally:
            conn.close()

    def reset_dice_rolls(self, user_id):
        """Сброс счетчика бросков кубика"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        try:
            current_month = datetime.now().strftime('%Y-%m')
            
            c.execute('''UPDATE users 
                        SET dice_rolls_count = 0,
                            last_dice_roll_month = ?
                        WHERE user_id = ?''',
                     (current_month, user_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error resetting dice rolls: {e}")
            return False
        finally:
            conn.close()

    def get_user_donate(self, user_id: int) -> int:
        """Получение баланса доната пользователя"""
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("SELECT donate FROM users WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logging.error(f"Error getting user donate: {e}")
            return 0
        finally:
            conn.close()

    def add_donate(self, user_id: int, amount: int) -> bool:
        """Добавление доната пользователю"""
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("""
                UPDATE users 
                SET donate = donate + ? 
                WHERE user_id = ?
            """, (amount, user_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding donate: {e}")
            return False
        finally:
            conn.close()

    def remove_donate(self, user_id: int, amount: int) -> bool:
        """Списание доната у пользователя"""
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            
            # Проверяем, достаточно ли средств
            current_balance = self.get_user_donate(user_id)
            if current_balance < amount:
                return False
                
            c.execute("""
                UPDATE users 
                SET donate = donate - ? 
                WHERE user_id = ?
            """, (amount, user_id))
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error removing donate: {e}")
            return False
        finally:
            conn.close()

    # --- Dice Stats Methods ---

    def _ensure_dice_stats_entry(self, cur: sqlite3.Cursor, user_id: int):
        """Убеждается, что для пользователя есть запись в dice_stats"""
        cur.execute("SELECT user_id FROM dice_stats WHERE user_id = ?", (user_id,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO dice_stats (user_id, count_games, win, loss) VALUES (?, 0, 0, 0)", (user_id,))
            logging.info(f"Created dice_stats entry for user {user_id}")

    def add_dice_win(self, user_id: int) -> bool:
        """Запись победы в игре в кости"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            self._ensure_dice_stats_entry(cur, user_id)
            cur.execute("UPDATE dice_stats SET count_games = count_games + 1, win = win + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            logging.info(f"Recorded dice win for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Error recording dice win for user {user_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def add_dice_loss(self, user_id: int) -> bool:
        """Запись поражения в игре в кости"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            self._ensure_dice_stats_entry(cur, user_id)
            cur.execute("UPDATE dice_stats SET count_games = count_games + 1, loss = loss + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            logging.info(f"Recorded dice loss for user {user_id}")
            return True
        except Exception as e:
            logging.error(f"Error recording dice loss for user {user_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_dice_stats(self, user_id: int) -> Optional[Tuple]:
        """Получение статистики игр в кости пользователя"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT count_games, win, loss FROM dice_stats WHERE user_id = ?", (user_id,))
            stats = cur.fetchone()
            return stats
        except Exception as e:
            logging.error(f"Error getting dice stats for user {user_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    # --- End Dice Stats Methods ---

    def get_all_users_with_pass(self):
        """Получает всех пользователей с активным Film Pass"""
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("""
                SELECT user_id FROM users 
                WHERE pass > ?
            """, (current_time,))
            users = cur.fetchall()
            logging.info(f"Found {len(users)} users with active pass, current time: {current_time}")
            return users
        except Exception as e:
            logging.error(f"Error getting users with pass: {e}")
            return []
        finally:
            if conn:
                conn.close() 