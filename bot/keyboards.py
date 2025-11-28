# Bot keyboards

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Константы для текста кнопок (используются и в handlers)
BTN_TASKS = "📋 Задачи"
BTN_MY_BARBERSHOPS = "💈 Мои барбершопы"
BTN_STATISTICS = "📊 Статистика"
BTN_BACK = "⬅️ Назад"
BTN_MAIN_MENU = "🏠 Главное меню"

# Подменю задач
BTN_NEW_TASK = "🆕 Новая задача"
BTN_MY_TASKS = "📋 Мои задачи"

# Подменю барбершопов
BTN_ADD_BARBERSHOP = "➕ Добавить барбершоп"

# Для совместимости (старые названия)
BTN_CANCEL = BTN_MAIN_MENU
BTN_MY_BRANCHES = BTN_MY_BARBERSHOPS  # Для обратной совместимости
BTN_ADD_BRANCH = BTN_ADD_BARBERSHOP   # Для обратной совместимости

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

# Кнопки регистрации
BTN_START_REGISTRATION = "📝 Пройти регистрацию"
BTN_ADD_MORE_BARBERSHOP = "➕ Добавить ещё барбершоп"
BTN_FINISH_REGISTRATION = "✅ Завершить регистрацию"
BTN_CANCEL_REGISTRATION = "❌ Отменить"

# Для обратной совместимости
BTN_ADD_MORE_BRANCH = BTN_ADD_MORE_BARBERSHOP

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
            [KeyboardButton(text=BTN_TASKS), KeyboardButton(text=BTN_MY_BARBERSHOPS)],
            [KeyboardButton(text=BTN_STATISTICS)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


def tasks_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню задач."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_TASK), KeyboardButton(text=BTN_MY_TASKS)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


def barbershops_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню барбершопов."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_BARBERSHOP)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


# Для обратной совместимости
branches_menu_keyboard = barbershops_menu_keyboard


def back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой назад."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BACK)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
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


def active_tasks_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура после показа задач в работе."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CANCEL_TASK), KeyboardButton(text=BTN_SHOW_ALL_TASKS)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
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


# ═══════════════════════════════════════════════════════════════════
# Клавиатуры регистрации
# ═══════════════════════════════════════════════════════════════════

def registration_start_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для начала регистрации."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_START_REGISTRATION)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Нажмите для регистрации",
    )
    return keyboard


def share_contact_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса контакта."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL_REGISTRATION)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Поделитесь контактом",
    )
    return keyboard


def cancel_registration_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены регистрации."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CANCEL_REGISTRATION)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите данные или отмените",
    )
    return keyboard


def add_more_barbershops_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура добавления барбершопов."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_MORE_BARBERSHOP)],
            [KeyboardButton(text=BTN_FINISH_REGISTRATION)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Добавить барбершоп или завершить?",
    )
    return keyboard


# Для обратной совместимости
add_more_branches_keyboard = add_more_barbershops_keyboard


def pending_verification_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для ожидающих верификации."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Проверить статус")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Ожидайте верификации",
    )
    return keyboard
