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

# Кнопки подтверждения описания
BTN_ADD_COMMENT = "💬 Добавить комментарий"
BTN_CONTINUE = "✅ Продолжить"

# Кнопки прикрепления файлов
BTN_ATTACH_FILES = "📎 Прикрепить файлы"
BTN_SKIP_FILES = "⏭ Пропустить"
BTN_DONE_FILES = "✅ Готово"

# Кнопки просмотра задач
BTN_SHOW_ALL_TASKS = "📋 Показать все задачи"
BTN_CANCEL_TASK = "❌ Отменить задачу"
BTN_CONFIRM_CANCEL = "✅ Да, отменить"
BTN_REJECT_CANCEL = "❌ Нет"

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


def confirm_description_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения описания задачи."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_COMMENT), KeyboardButton(text=BTN_CONTINUE)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Добавить комментарий или продолжить?",
    )
    return keyboard


def attach_files_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для прикрепления файлов."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ATTACH_FILES), KeyboardButton(text=BTN_SKIP_FILES)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Прикрепить файлы?",
    )
    return keyboard


def done_files_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после загрузки файлов."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DONE_FILES)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Отправьте файлы или нажмите Готово",
    )
    return keyboard


def show_all_tasks_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после показа активных задач."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHOW_ALL_TASKS)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Показать все или в меню?",
    )
    return keyboard


def all_tasks_actions_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после показа всех задач (с возможностью отмены)."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CANCEL_TASK)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Отменить задачу или в меню?",
    )
    return keyboard


def confirm_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения отмены задачи."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CONFIRM_CANCEL), KeyboardButton(text=BTN_REJECT_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Подтвердите отмену",
    )
    return keyboard
