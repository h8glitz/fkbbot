from aiogram.fsm.state import State, StatesGroup

class AddCard(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_limited = State()
    waiting_for_rare = State()
    waiting_for_points = State()
    waiting_for_price = State()
    waiting_for_counts = State()

class AdminStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_limited = State()
    waiting_for_rare = State()
    waiting_for_points = State()
    waiting_for_price = State()
    waiting_for_counts = State()
    waiting_for_user_id = State()
    waiting_for_attempts = State()
    waiting_for_ban_user_id = State()
    waiting_for_unban_user_id = State()
    waiting_for_pass_user_id = State()
    waiting_for_pass_months = State()
    waiting_for_donate_user_id = State()
    waiting_for_delete_card_id = State()
    waiting_for_donate_amount = State()
    casino_game = State()

class CollectionStates(StatesGroup):
    viewing = State()

class TradeStates(StatesGroup):
    selecting_card = State()
    waiting_for_username = State()
    waiting_for_response = State()
    selecting_response_card = State()

class RandomCardStates(StatesGroup):
    rolling = State()

class DiceStates(StatesGroup):
    selecting_card = State()
    waiting_for_username = State()
    waiting_for_response = State()
    selecting_response_card = State()
    waiting_for_confirmation = State()
    waiting_for_first_roll = State()
    waiting_for_second_roll = State()

class FamilyStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_avatar = State()
    waiting_for_description = State()
    waiting_for_invite_username = State() 