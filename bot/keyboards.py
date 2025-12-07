# Bot keyboards

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Константы для текста кнопок (используются и в handlers)
BTN_TASKS = "📋 Задачи"
BTN_ACCOUNT = "👤 Аккаунт"
BTN_MY_BARBERSHOPS = BTN_ACCOUNT  # Для обратной совместимости
BTN_STATISTICS = "📊 Статистика"
BTN_AI_ASSISTANT = "🤖 AI-ассистент"
BTN_AI_MORE_DETAILS = "📖 Подробнее"

# Статистика — периоды
BTN_STATS_CURRENT_MONTH = "📅 Текущий месяц"
BTN_STATS_PREV_MONTH = "📆 Прошлый месяц"
BTN_STATS_TODAY = "📊 Сегодня"
BTN_STATS_YESTERDAY = "📊 Вчера"
BTN_STATS_RATING = "🏆 Рейтинг"

# Рейтинг — периоды
BTN_RATING_CURRENT = "📅 Текущий месяц"
BTN_RATING_PREV = "📆 Прошлый месяц"
BTN_USEFUL = "📚 Полезное"
BTN_CONTACT_OFFICE_MAIN = "📞 Связаться"
BTN_BACK = "⬅️ Назад"
BTN_MAIN_MENU = "🏠 Главное меню"

# Полезное — отделы
BTN_USEFUL_DEVELOPMENT = "🚀 Развитие"
BTN_USEFUL_MARKETING = "📢 Маркетинг"
BTN_USEFUL_DESIGN = "🎨 Дизайн"

# Полезное — действия
BTN_IMPORTANT_INFO = "📋 Важная информация"
BTN_CONTACT_DEPARTMENT = "📞 Связаться с отделом"

# Для обратной совместимости
BTN_CONTACT_OFFICE = BTN_USEFUL

# Подменю задач
BTN_NEW_TASK = "🆕 Новая задача"
BTN_MY_TASKS = "📋 Мои задачи"

# Подменю аккаунта
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
            [KeyboardButton(text=BTN_TASKS), KeyboardButton(text=BTN_USEFUL)],
            [KeyboardButton(text=BTN_STATISTICS), KeyboardButton(text=BTN_AI_ASSISTANT)],
            [KeyboardButton(text=BTN_ACCOUNT), KeyboardButton(text=BTN_CONTACT_OFFICE_MAIN)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


def ai_assistant_keyboard(show_more_button: bool = False) -> ReplyKeyboardMarkup:
    """
    Меню AI-ассистента (обучение).
    
    Args:
        show_more_button: Показать кнопку "Подробнее" после ответа
    """
    rows = []
    
    if show_more_button:
        rows.append([KeyboardButton(text=BTN_AI_MORE_DETAILS)])
    
    rows.append([KeyboardButton(text=BTN_MAIN_MENU)])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Задайте вопрос по обучению...",
    )
    return keyboard


def useful_departments_keyboard() -> ReplyKeyboardMarkup:
    """Меню выбора отдела в разделе Полезное."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_USEFUL_DEVELOPMENT)],
            [KeyboardButton(text=BTN_USEFUL_MARKETING)],
            [KeyboardButton(text=BTN_USEFUL_DESIGN)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите отдел",
    )
    return keyboard


def useful_actions_keyboard(custom_buttons: list = None) -> ReplyKeyboardMarkup:
    """
    Меню действий внутри отдела (Полезное).
    
    Args:
        custom_buttons: Список кастомных кнопок из БД (каждая кнопка - объект с button_text)
    """
    rows = []
    
    # Все кнопки кроме "Назад" берутся из БД
    if custom_buttons:
        for btn in custom_buttons:
            rows.append([KeyboardButton(text=btn.button_text)])
    
    # Только "Назад" — стандартная кнопка
    rows.append([KeyboardButton(text=BTN_BACK)])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


# Для обратной совместимости
def contact_office_keyboard() -> ReplyKeyboardMarkup:
    """Устаревшее меню - перенаправляет на useful_departments_keyboard."""
    return useful_departments_keyboard()


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


def account_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню аккаунта."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_BARBERSHOP)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
    return keyboard


def barbershops_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню барбершопов (для обратной совместимости)."""
    return account_menu_keyboard()


def statistics_period_keyboard() -> ReplyKeyboardMarkup:
    """Меню выбора периода статистики."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS_TODAY), KeyboardButton(text=BTN_STATS_YESTERDAY)],
            [KeyboardButton(text=BTN_STATS_CURRENT_MONTH), KeyboardButton(text=BTN_STATS_PREV_MONTH)],
            [KeyboardButton(text=BTN_STATS_RATING)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите период",
    )
    return keyboard


def rating_period_keyboard() -> ReplyKeyboardMarkup:
    """Меню выбора периода для рейтинга."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_RATING_CURRENT), KeyboardButton(text=BTN_RATING_PREV)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите период",
    )
    return keyboard


# Для обратной совместимости
branches_menu_keyboard = barbershops_menu_keyboard


def barbershop_select_keyboard(barbershops: list) -> ReplyKeyboardMarkup:
    """
    Клавиатура для выбора барбершопа при создании задачи.
    barbershops - список объектов с атрибутом .name
    """
    keyboard_rows = []
    
    # Добавляем кнопки барбершопов (по 1 в ряд для читаемости)
    for barbershop in barbershops:
        name = barbershop.name if hasattr(barbershop, 'name') else str(barbershop)
        keyboard_rows.append([KeyboardButton(text=f"💈 {name}")])
    
    # Добавляем кнопку отмены
    keyboard_rows.append([KeyboardButton(text=BTN_MAIN_MENU)])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите барбершоп",
    )


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
