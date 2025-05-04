from database import Database

def clean_users_cards():
    db = Database('film_bot.db')
    
    # Получаем всех пользователей
    conn = db._get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT user_id FROM users')
        users = cur.fetchall()
        
        print("\nОчистка некорректных ссылок на карты...")
        for user in users:
            user_id = user[0]
            print(f"\nОбработка пользователя ID: {user_id}")
            db.clean_user_cards(user_id)
            
            # Проверяем результат
            cur.execute('SELECT cards FROM users WHERE user_id = ?', (user_id,))
            cards = cur.fetchone()[0]
            print(f"Карты после очистки: {cards}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    clean_users_cards() 