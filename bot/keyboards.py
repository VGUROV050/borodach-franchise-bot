# Bot keyboards

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Константы для текста кнопок (используются и в handlers)
BTN_NEW_TASK = "🆕 Новая задача"
BTN_MY_TASKS = "📋 Мои задачи"
BTN_CANCEL = "🏠 Главное меню"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_TASK), KeyboardButton(text=BTN_MY_TASKS)]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены (для выхода из любого состояния)."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CANCEL)]
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите ответ или вернитесь в меню",
    )
    return keyboard
