from database import Database

def add_test_cards():
    db = Database('film_bot.db')
    
    # Добавляем тестовые карты разной редкости
    cards = [
        {
            'name': 'Test Base Card',
            'photo': 'AgACAgIAAxkBAAIBPGXEEQABYXR_AAFhR9aaJ-0nVwABB0wAAuDKMRuqAAHZSWIVAAEeAQADAgADeAADNAQ',
            'limited': 0,
            'rare': 'Base',
            'points': 250,
            'price': 500,
            'counts': 100
        },
        {
            'name': 'Test Medium Card',
            'photo': 'AgACAgIAAxkBAAIBPGXEEQABYXR_AAFhR9aaJ-0nVwABB0wAAuDKMRuqAAHZSWIVAAEeAQADAgADeAADNAQ',
            'limited': 0,
            'rare': 'Medium',
            'points': 350,
            'price': 700,
            'counts': 50
        },
        {
            'name': 'Test Episode Card',
            'photo': 'AgACAgIAAxkBAAIBPGXEEQABYXR_AAFhR9aaJ-0nVwABB0wAAuDKMRuqAAHZSWIVAAEeAQADAgADeAADNAQ',
            'limited': 0,
            'rare': 'Episode',
            'points': 500,
            'price': 1000,
            'counts': 25
        }
    ]
    
    for card in cards:
        card_id = db.add_card(
            card_name=card['name'],
            photo_url=card['photo'],
            limited=card['limited'],
            rare=card['rare'],
            points=card['points'],
            price=card['price'],
            counts=card['counts']
        )
        print(f"Added card {card['name']} with ID {card_id}")

if __name__ == "__main__":
    add_test_cards() 