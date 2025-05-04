import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

def fix_database():
    conn = sqlite3.connect('film_bot.db')
    cur = conn.cursor()
    
    # Проверяем структуру таблицы users
    cur.execute("PRAGMA table_info(users)")
    columns = cur.fetchall()
    print("\nСтруктура таблицы users:")
    for col in columns:
        print(col)
    
    # Проверяем данные в таблице users
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    print("\nДанные в таблице users:")
    for user in users:
        print(user)
    
    # Пробуем принудительно обновить карты для пользователя
    try:
        user_id = 1072722982  # ID пользователя
        cards = "2"  # Тестовая карта
        
        # Проверяем текущие данные пользователя
        cur.execute("SELECT cards FROM users WHERE user_id = ?", (user_id,))
        current = cur.fetchone()
        print(f"\nТекущие карты пользователя: {current}")
        
        # Обновляем карты напрямую
        cur.execute("UPDATE users SET cards = ? WHERE user_id = ?", (cards, user_id))
        conn.commit()
        
        # Проверяем обновление
        cur.execute("SELECT cards FROM users WHERE user_id = ?", (user_id,))
        after_update = cur.fetchone()
        print(f"Карты после обновления: {after_update}")
        
        # Проверяем все поля пользователя
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_data = cur.fetchone()
        print(f"Все данные пользователя после обновления: {user_data}")
        
    except Exception as e:
        print(f"Ошибка при обновлении: {e}")
    
    conn.close()

def check_database():
    conn = sqlite3.connect('film_bot.db')
    cur = conn.cursor()
    
    # Проверяем структуру таблицы cards
    print("\nСтруктура таблицы cards:")
    cur.execute("PRAGMA table_info(cards)")
    columns = cur.fetchall()
    for col in columns:
        print(col)
    
    # Проверяем данные в таблице cards
    print("\nДанные в таблице cards:")
    cur.execute("SELECT * FROM cards")
    cards = cur.fetchall()
    for card in cards:
        print(card)
    
    # Проверяем количество карт
    cur.execute("SELECT COUNT(*) FROM cards")
    count = cur.fetchone()[0]
    print(f"\nВсего карт в базе: {count}")
    
    # Проверяем карты по редкости
    print("\nКоличество карт по редкости:")
    cur.execute("SELECT rare, COUNT(*) FROM cards GROUP BY rare")
    rare_counts = cur.fetchall()
    for rare, count in rare_counts:
        print(f"{rare}: {count}")
    
    # Проверяем ограниченные карты
    print("\nКоличество ограниченных карт:")
    cur.execute("SELECT COUNT(*) FROM cards WHERE limited = 1")
    limited_count = cur.fetchone()[0]
    print(f"Ограниченных карт: {limited_count}")
    
    conn.close()

if __name__ == "__main__":
    fix_database()
    check_database() 