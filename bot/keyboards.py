# Bot keyboards

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Константы для текста кнопок (используются и в handlers)
BTN_NEW_TASK = "🆕 Новая задача"
BTN_MY_TASKS = "📋 Мои задачи"
BTN_CANCEL = "🏠 Главное меню"

# Кнопки отделов
BTN_DEPT_DEVELOPMENT = "🚀 Отдел Развития"
BTN_DEPT_MARKETING = "📢 Отдел Маркетинга"
BTN_DEPT_DESIGN = "🎨 Дизайн"

# Маппинг кнопок на ключи отделов (для handlers)
DEPT_BUTTON_TO_KEY = {
    BTN_DEPT_DEVELOPMENT: "development",
    BTN_DEPT_MARKETING: "marketing",
    BTN_DEPT_DESIGN: "design",
}


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


def department_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора отдела."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DEPT_DEVELOPMENT)],
            [KeyboardButton(text=BTN_DEPT_MARKETING)],
            [KeyboardButton(text=BTN_DEPT_DESIGN)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите отдел",
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
