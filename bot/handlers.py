# Bot handlers

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import DEPARTMENTS
from database import AsyncSessionLocal, get_partner_by_telegram_id, PartnerStatus
from .keyboards import (
    main_menu_keyboard,
    tasks_menu_keyboard,
    branches_menu_keyboard,
    cancel_keyboard,
    department_keyboard,
    confirm_description_keyboard,
    attach_files_keyboard,
    done_files_keyboard,
    active_tasks_keyboard,
    all_tasks_actions_keyboard,
    confirm_cancel_keyboard,
    registration_start_keyboard,
    pending_verification_keyboard,
    BTN_TASKS,
    BTN_MY_BRANCHES,
    BTN_STATISTICS,
    BTN_MAIN_MENU,
    BTN_ADD_BRANCH,
    BTN_NEW_TASK, 
    BTN_MY_TASKS,
    BTN_CANCEL,
    BTN_ADD_COMMENT,
    BTN_CONTINUE,
    BTN_ATTACH_FILES,
    BTN_SKIP_FILES,
    BTN_DONE_FILES,
    BTN_SHOW_ALL_TASKS,
    BTN_CANCEL_TASK,
    BTN_CONFIRM_CANCEL,
    BTN_REJECT_CANCEL,
    DEPT_BUTTON_TO_KEY,
)
from bitrix import (
    create_task, 
    get_user_tasks, 
    format_task_stage, 
    BitrixClientError, 
    upload_file_to_task,
    get_task_by_id,
    cancel_task,
    verify_task_ownership,
    check_task_can_be_cancelled,
)

logger = logging.getLogger(__name__)

router = Router()


# ═══════════════════════════════════════════════════════════════════
# FSM States для создания задачи
# ═══════════════════════════════════════════════════════════════════

class NewTaskStates(StatesGroup):
    waiting_for_department = State()
    waiting_for_branch = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_confirm = State()
    waiting_for_comment = State()
    waiting_for_files_choice = State()
    waiting_for_files = State()


class CancelTaskStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_confirm = State()


class AddBranchStates(StatesGroup):
    waiting_for_branch_text = State()


# ═══════════════════════════════════════════════════════════════════
# Helper: проверка верификации (вынесено вверх для использования)
# ═══════════════════════════════════════════════════════════════════

async def _check_verified(message: types.Message) -> bool:
    """Проверить, что пользователь верифицирован. Возвращает True если ок."""
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
    
    if partner is None:
        await message.answer(
            "❌ Вы не зарегистрированы.\n"
            "Нажмите /start для регистрации.",
            reply_markup=registration_start_keyboard(),
        )
        return False
    
    if partner.status != PartnerStatus.VERIFIED:
        await message.answer(
            "⏳ Ваша заявка ещё не подтверждена.\n"
            "Дождитесь верификации администратором.",
            reply_markup=pending_verification_keyboard(),
        )
        return False
    
    return True


# ═══════════════════════════════════════════════════════════════════
# Главное меню и навигация
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_MAIN_MENU)
async def main_menu_handler(message: types.Message, state: FSMContext) -> None:
    """Возврат в главное меню из любого состояния."""
    current_state = await state.get_state()
    
    if current_state is not None:
        logger.info(f"User {message.from_user.id} returned to main menu from state {current_state}")
        await state.clear()
    
    # Проверяем верификацию
    if not await _check_verified(message):
        return
    
    await message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_TASKS)
async def tasks_menu_handler(message: types.Message, state: FSMContext) -> None:
    """Меню задач."""
    if not await _check_verified(message):
        return
    
    await state.clear()
    await message.answer(
        "📋 <b>Задачи</b>\n\nВыберите действие:",
        reply_markup=tasks_menu_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Мои филиалы
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_MY_BRANCHES)
async def my_branches_handler(message: types.Message, state: FSMContext) -> None:
    """Показать салоны пользователя."""
    if not await _check_verified(message):
        return
    
    await state.clear()
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        
        companies = []
        if partner:
            from database import get_partner_companies
            companies = await get_partner_companies(db, partner.id)
    
    if companies:
        companies_text = "\n".join([
            f"• <b>{c.name}</b>" + (f" ({c.city})" if c.city else "")
            for c in companies
        ])
        text = (
            f"🏢 <b>Ваши салоны</b>\n\n"
            f"{companies_text}\n\n"
            "Вы можете запросить добавление ещё одного салона, нажав кнопку ниже."
        )
    else:
        text = (
            "🏢 <b>Ваши салоны</b>\n\n"
            "У вас пока нет привязанных салонов.\n\n"
            "Нажмите кнопку ниже, чтобы запросить добавление салона."
        )
    
    await message.answer(text, reply_markup=branches_menu_keyboard())


@router.message(F.text == BTN_ADD_BRANCH)
async def add_branch_start(message: types.Message, state: FSMContext) -> None:
    """Начало добавления филиала."""
    if not await _check_verified(message):
        return
    
    await state.set_state(AddBranchStates.waiting_for_branch_text)
    
    await message.answer(
        "🏢 <b>Добавление филиала</b>\n\n"
        "Укажите информацию о вашем филиале:\n"
        "• Город\n"
        "• Адрес\n"
        "• Название (если есть)\n\n"
        "Например: <i>Москва, ул. Примерная, д.1, БЦ Пример</i>",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddBranchStates.waiting_for_branch_text)
async def add_branch_process(message: types.Message, state: FSMContext) -> None:
    """Обработка текста филиала."""
    if message.text == BTN_MAIN_MENU:
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    branch_text = message.text.strip()
    
    if len(branch_text) < 5:
        await message.answer(
            "❌ Слишком короткое описание. Пожалуйста, укажите город и адрес.",
            reply_markup=cancel_keyboard(),
        )
        return
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        
        if partner:
            from database import update_partner_for_branch_request
            await update_partner_for_branch_request(db, partner.id, branch_text)
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Заявка на добавление филиала отправлена!</b>\n\n"
        f"📍 {branch_text}\n\n"
        "Администратор рассмотрит вашу заявку и привяжет филиал.\n"
        "Вы получите уведомление, когда филиал будет добавлен.",
        reply_markup=main_menu_keyboard(),
    )
    
    logger.info(f"Partner {message.from_user.id} requested new branch: {branch_text}")


# ═══════════════════════════════════════════════════════════════════
# Статистика по филиалам (YClients)
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_STATISTICS)
async def statistics_handler(message: types.Message, state: FSMContext) -> None:
    """Показать статистику по филиалам из YClients."""
    if not await _check_verified(message):
        return
    
    await state.clear()
    
    # Показываем сообщение о загрузке
    loading_msg = await message.answer("⏳ Загружаю статистику из YClients...")
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        
        if not partner:
            await loading_msg.delete()
            await message.answer("❌ Партнёр не найден", reply_markup=main_menu_keyboard())
            return
        
        from database import get_partner_branches, get_network_rating_by_company
        partner_branches = await get_partner_branches(db, partner.id)
    
    if not partner_branches:
        await loading_msg.delete()
        await message.answer(
            "📊 <b>Статистика по филиалам</b>\n\n"
            "У вас пока нет привязанных филиалов.\n"
            "Обратитесь к администратору для привязки.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    # Получаем статистику по каждому филиалу
    from yclients import get_monthly_revenue
    
    stats_text = "📊 <b>Статистика за текущий месяц</b>\n"
    total_revenue = 0
    total_completed = 0
    period = ""
    
    for pb in partner_branches:
        branch = pb.branch
        branch_name = branch.display_name or branch.name or f"{branch.city}, {branch.address}"
        
        if not branch.yclients_id:
            stats_text += f"\n🏢 <b>{branch_name}</b>\n"
            stats_text += "   ⚠️ YClients ID не указан\n"
            continue
        
        # Получаем выручку
        result = await get_monthly_revenue(branch.yclients_id)
        
        if result.get("success"):
            revenue = result.get("revenue", 0)
            completed = result.get("completed_count", 0)
            total_count = result.get("total_count", 0)
            
            # Период из первого успешного ответа
            if not period:
                period = result.get("period", "")
                stats_text += f"📅 <b>{period}</b>\n"
            
            total_revenue += revenue
            total_completed += completed
            
            stats_text += f"\n🏢 <b>{branch_name}</b>\n"
            stats_text += f"   💰 Выручка: <b>{revenue:,.0f} ₽</b>\n"
            stats_text += f"   ✅ Завершено: {completed} из {total_count} записей\n"
            
            # Получаем место в рейтинге сети и средний чек
            async with AsyncSessionLocal() as db:
                rating = await get_network_rating_by_company(db, branch.yclients_id)
            
            if rating and rating.rank > 0:
                stats_text += f"   🏆 Место в сети: <b>{rating.rank}</b> из {rating.total_companies}\n"
                if rating.avg_check > 0:
                    stats_text += f"   💵 Средний чек: <b>{rating.avg_check:,.0f} ₽</b>\n"
        else:
            stats_text += f"\n🏢 <b>{branch_name}</b>\n"
            stats_text += f"   ❌ {result.get('error', 'Ошибка загрузки')}\n"
    
    # Итого (если несколько филиалов)
    if len(partner_branches) > 1 and total_revenue > 0:
        stats_text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        stats_text += f"📈 <b>Итого:</b>\n"
        stats_text += f"   💰 Выручка: <b>{total_revenue:,.0f} ₽</b>\n"
        stats_text += f"   ✅ Завершено записей: {total_completed}"
    
    # Удаляем сообщение о загрузке и отправляем результат
    await loading_msg.delete()
    await message.answer(stats_text, reply_markup=main_menu_keyboard())


# ═══════════════════════════════════════════════════════════════════
# /start — с проверкой верификации
# ═══════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Обработчик команды /start с проверкой верификации."""
    await state.clear()
    
    telegram_id = message.from_user.id
    
    # Проверяем партнёра в БД
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, telegram_id)
    
    if partner is None:
        # Новый пользователь — нужна регистрация
        await message.answer(
            "👋 Добро пожаловать в бот для франчайзи <b>BORODACH</b>!\n\n"
            "Для доступа к функциям бота необходимо пройти регистрацию.\n\n"
            "Нажмите кнопку ниже, чтобы начать:",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    if partner.status == PartnerStatus.PENDING:
        # Ожидает верификации
        await message.answer(
            "⏳ <b>Ваша заявка на рассмотрении</b>\n\n"
            f"👤 {partner.full_name}\n"
            f"📱 {partner.phone}\n\n"
            "Пожалуйста, дождитесь подтверждения администратором.\n"
            "Мы уведомим вас, когда заявка будет рассмотрена.",
            reply_markup=pending_verification_keyboard(),
        )
        return
    
    if partner.status == PartnerStatus.REJECTED:
        # Заявка отклонена
        rejection_reason = partner.rejection_reason or "Причина не указана"
        await message.answer(
            "❌ <b>Ваша заявка отклонена</b>\n\n"
            f"Причина: {rejection_reason}\n\n"
            "Если вы считаете, что это ошибка, обратитесь в поддержку.",
        )
        return
    
    # Верифицированный партнёр — показываем главное меню
    await message.answer(
        f"👋 Привет, <b>{partner.full_name}</b>!\n\n"
        "Это бот для франчайзи <b>BORODACH</b>.\n\n"
        "Здесь вы можете:\n"
        "• 📋 Работать с задачами\n"
        "• 🏢 Управлять своими филиалами\n\n"
        "Выберите раздел в меню ниже 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "🔄 Проверить статус")
async def check_status(message: types.Message, state: FSMContext) -> None:
    """Проверка статуса верификации."""
    telegram_id = message.from_user.id
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, telegram_id)
    
    if partner is None:
        await message.answer(
            "❌ Вы не зарегистрированы.\n"
            "Нажмите /start для регистрации.",
        )
        return
    
    if partner.status == PartnerStatus.PENDING:
        await message.answer(
            "⏳ <b>Статус: Ожидает рассмотрения</b>\n\n"
            "Ваша заявка ещё не рассмотрена.\n"
            "Пожалуйста, подождите.",
            reply_markup=pending_verification_keyboard(),
        )
    elif partner.status == PartnerStatus.VERIFIED:
        await message.answer(
            "✅ <b>Статус: Верифицирован</b>\n\n"
            "Добро пожаловать!",
            reply_markup=main_menu_keyboard(),
        )
    elif partner.status == PartnerStatus.REJECTED:
        await message.answer(
            "❌ <b>Статус: Отклонён</b>\n\n"
            f"Причина: {partner.rejection_reason or 'Не указана'}",
        )


# ═══════════════════════════════════════════════════════════════════
# Новая задача — Шаг 1: Выбор отдела
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_NEW_TASK)
async def new_task_start(message: types.Message, state: FSMContext) -> None:
    """Начало создания задачи — выбор отдела."""
    # Проверка верификации
    if not await _check_verified(message):
        return
    
    await state.set_state(NewTaskStates.waiting_for_department)
    
    await message.answer(
        "🏢 <b>В какой отдел вы хотите поставить задачу?</b>\n\n"
        "Выберите отдел:",
        reply_markup=department_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_department, F.text.in_(DEPT_BUTTON_TO_KEY.keys()))
async def new_task_department(message: types.Message, state: FSMContext) -> None:
    """Шаг 1: Получили отдел → спрашиваем филиал."""
    dept_key = DEPT_BUTTON_TO_KEY[message.text]
    dept_info = DEPARTMENTS[dept_key]
    
    if not dept_info["group_id"] or not dept_info["responsible_id"]:
        await message.answer(
            f"❌ Отдел «{dept_info['name']}» пока не настроен.\n"
            "Обратитесь к администратору.",
            reply_markup=department_keyboard(),
        )
        return
    
    await state.update_data(
        department_key=dept_key,
        department_name=dept_info["name"],
        group_id=dept_info["group_id"],
        responsible_id=dept_info["responsible_id"],
        files=[],  # Список для файлов
    )
    await state.set_state(NewTaskStates.waiting_for_branch)
    
    await message.answer(
        f"✅ Отдел: <b>{dept_info['name']}</b>\n\n"
        "📍 <b>По какому филиалу вы хотите поставить задачу?</b>\n\n"
        "Укажите город, ТЦ или адрес:",
        reply_markup=cancel_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_department)
async def new_task_department_invalid(message: types.Message, state: FSMContext) -> None:
    """Неверный выбор отдела."""
    await message.answer(
        "⚠️ Пожалуйста, выберите отдел из списка ниже:",
        reply_markup=department_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Новая задача — Шаг 2: Филиал
# ═══════════════════════════════════════════════════════════════════

@router.message(NewTaskStates.waiting_for_branch)
async def new_task_branch(message: types.Message, state: FSMContext) -> None:
    """Шаг 2: Получили филиал → спрашиваем заголовок."""
    branch = message.text.strip()
    
    if not branch:
        await message.answer(
            "Пожалуйста, укажите филиал:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(branch=branch)
    await state.set_state(NewTaskStates.waiting_for_title)
    
    await message.answer(
        "✏️ <b>Введите краткое название задачи:</b>\n\n"
        "Например: «Обновить цены в филиале» или «Добавить сотрудника в Yclients»",
        reply_markup=cancel_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Новая задача — Шаг 3: Заголовок
# ═══════════════════════════════════════════════════════════════════

@router.message(NewTaskStates.waiting_for_title)
async def new_task_title(message: types.Message, state: FSMContext) -> None:
    """Шаг 3: Получили заголовок → спрашиваем описание."""
    title = message.text.strip()
    
    if not title:
        await message.answer(
            "Пожалуйста, введите название задачи:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(title=title)
    await state.set_state(NewTaskStates.waiting_for_description)
    
    await message.answer(
        "📝 <b>Опишите задачу подробнее:</b>\n\n"
        "Укажите все детали, которые помогут выполнить задачу.",
        reply_markup=cancel_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Новая задача — Шаг 4: Описание
# ═══════════════════════════════════════════════════════════════════

@router.message(NewTaskStates.waiting_for_description)
async def new_task_description(message: types.Message, state: FSMContext) -> None:
    """Шаг 4: Получили описание → показываем подтверждение."""
    description = message.text.strip()
    
    if not description:
        await message.answer(
            "Пожалуйста, опишите задачу:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(description=description)
    await state.set_state(NewTaskStates.waiting_for_confirm)
    
    # Показываем превью задачи
    data = await state.get_data()
    
    await message.answer(
        f"📋 <b>Проверьте вашу задачу:</b>\n\n"
        f"🏢 Отдел: {data['department_name']}\n"
        f"📍 Филиал: {data['branch']}\n"
        f"✏️ Задача: {data['title']}\n\n"
        f"📝 Описание:\n{description}\n\n"
        "Хотите добавить комментарий или продолжить?",
        reply_markup=confirm_description_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Новая задача — Шаг 5: Подтверждение / Добавить комментарий
# ═══════════════════════════════════════════════════════════════════

@router.message(NewTaskStates.waiting_for_confirm, F.text == BTN_ADD_COMMENT)
async def new_task_add_comment(message: types.Message, state: FSMContext) -> None:
    """Пользователь хочет добавить комментарий."""
    await state.set_state(NewTaskStates.waiting_for_comment)
    
    await message.answer(
        "💬 <b>Введите дополнительный комментарий:</b>",
        reply_markup=cancel_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_comment)
async def new_task_comment(message: types.Message, state: FSMContext) -> None:
    """Получили комментарий → добавляем к описанию."""
    comment = message.text.strip()
    
    if not comment:
        await message.answer(
            "Пожалуйста, введите комментарий:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    # Добавляем комментарий к описанию
    data = await state.get_data()
    updated_description = data["description"] + f"\n\n💬 Дополнение: {comment}"
    await state.update_data(description=updated_description)
    
    await state.set_state(NewTaskStates.waiting_for_confirm)
    
    # Показываем обновлённое превью
    await message.answer(
        f"📋 <b>Обновлённое описание:</b>\n\n"
        f"🏢 Отдел: {data['department_name']}\n"
        f"📍 Филиал: {data['branch']}\n"
        f"✏️ Задача: {data['title']}\n\n"
        f"📝 Описание:\n{updated_description}\n\n"
        "Хотите добавить ещё комментарий или продолжить?",
        reply_markup=confirm_description_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_confirm, F.text == BTN_CONTINUE)
async def new_task_continue(message: types.Message, state: FSMContext) -> None:
    """Пользователь подтвердил описание → спрашиваем про файлы."""
    await state.set_state(NewTaskStates.waiting_for_files_choice)
    
    await message.answer(
        "📎 <b>Хотите прикрепить файлы к задаче?</b>\n\n"
        "Вы можете отправить фото, документы или другие файлы.",
        reply_markup=attach_files_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_confirm)
async def new_task_confirm_invalid(message: types.Message, state: FSMContext) -> None:
    """Неверный выбор на этапе подтверждения."""
    await message.answer(
        "⚠️ Пожалуйста, выберите действие из кнопок ниже:",
        reply_markup=confirm_description_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Новая задача — Шаг 6: Файлы
# ═══════════════════════════════════════════════════════════════════

@router.message(NewTaskStates.waiting_for_files_choice, F.text == BTN_SKIP_FILES)
async def new_task_skip_files(message: types.Message, state: FSMContext) -> None:
    """Пропустить прикрепление файлов → создаём задачу."""
    await _create_task_final(message, state)


@router.message(NewTaskStates.waiting_for_files_choice, F.text == BTN_ATTACH_FILES)
async def new_task_attach_files(message: types.Message, state: FSMContext) -> None:
    """Пользователь хочет прикрепить файлы."""
    await state.set_state(NewTaskStates.waiting_for_files)
    
    await message.answer(
        "📎 <b>Отправьте файлы</b>\n\n"
        "Вы можете отправить несколько фото или документов.\n"
        "Когда закончите — нажмите «✅ Готово».",
        reply_markup=done_files_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_files_choice)
async def new_task_files_choice_invalid(message: types.Message, state: FSMContext) -> None:
    """Неверный выбор на этапе файлов."""
    await message.answer(
        "⚠️ Пожалуйста, выберите действие из кнопок ниже:",
        reply_markup=attach_files_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_files, F.text == BTN_DONE_FILES)
async def new_task_files_done(message: types.Message, state: FSMContext) -> None:
    """Пользователь закончил загружать файлы → создаём задачу."""
    await _create_task_final(message, state)


@router.message(NewTaskStates.waiting_for_files, F.photo)
async def new_task_receive_photo(message: types.Message, state: FSMContext) -> None:
    """Получили фото — сохраняем file_id."""
    data = await state.get_data()
    files = data.get("files", [])
    
    # Берём фото максимального размера
    photo = message.photo[-1]
    files.append({"type": "photo", "file_id": photo.file_id})
    
    await state.update_data(files=files)
    
    await message.answer(
        f"✅ Фото добавлено (всего файлов: {len(files)})\n\n"
        "Отправьте ещё файлы или нажмите «✅ Готово».",
        reply_markup=done_files_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_files, F.document)
async def new_task_receive_document(message: types.Message, state: FSMContext) -> None:
    """Получили документ — сохраняем file_id."""
    data = await state.get_data()
    files = data.get("files", [])
    
    files.append({
        "type": "document",
        "file_id": message.document.file_id,
        "file_name": message.document.file_name,
    })
    
    await state.update_data(files=files)
    
    await message.answer(
        f"✅ Документ «{message.document.file_name}» добавлен (всего файлов: {len(files)})\n\n"
        "Отправьте ещё файлы или нажмите «✅ Готово».",
        reply_markup=done_files_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_files)
async def new_task_files_invalid(message: types.Message, state: FSMContext) -> None:
    """Неподдерживаемый тип файла или текст."""
    await message.answer(
        "📎 Отправьте фото или документ, либо нажмите «✅ Готово».",
        reply_markup=done_files_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Финальное создание задачи
# ═══════════════════════════════════════════════════════════════════

async def _create_task_final(message: types.Message, state: FSMContext) -> None:
    """Создание задачи в Bitrix с учётом всех данных."""
    data = await state.get_data()
    
    group_id = data.get("group_id")
    responsible_id = data.get("responsible_id")
    department_name = data.get("department_name", "Не указан")
    branch = data.get("branch", "Не указан")
    title = data.get("title", "Задача от франчайзи")
    description = data.get("description", "")
    files = data.get("files", [])
    
    user = message.from_user
    telegram_user_id = user.id
    telegram_username = user.username
    telegram_name = user.full_name
    
    processing_msg = await message.answer("⏳ Создаю задачу...")
    
    try:
        # 1. Создаём задачу
        task_id = await create_task(
            group_id=group_id,
            responsible_id=responsible_id,
            department_name=department_name,
            branch=branch,
            title=title,
            description=description,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            telegram_name=telegram_name,
            files=files,
        )
        
        # 2. Загружаем файлы в Bitrix (если есть)
        uploaded_count = 0
        if files:
            await processing_msg.edit_text("⏳ Загружаю файлы...")
            bot = message.bot
            
            for file_info in files:
                try:
                    file_id = file_info.get("file_id")
                    file_type = file_info.get("type")
                    
                    # Определяем имя файла
                    if file_type == "photo":
                        file_name = f"photo_{telegram_user_id}_{uploaded_count + 1}.jpg"
                    else:
                        file_name = file_info.get("file_name", f"file_{uploaded_count + 1}")
                    
                    # Скачиваем файл из Telegram
                    file = await bot.get_file(file_id)
                    file_content = await bot.download_file(file.file_path)
                    file_bytes = file_content.read()
                    
                    # Загружаем в Bitrix
                    result = await upload_file_to_task(task_id, file_bytes, file_name)
                    if result:
                        uploaded_count += 1
                        logger.info(f"Uploaded file {file_name} to task #{task_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to upload file: {e}")
                    continue
        
        files_text = f"\n📎 Загружено файлов: {uploaded_count}" if uploaded_count > 0 else ""
        
        # Текущее время в Москве
        moscow_tz = ZoneInfo("Europe/Moscow")
        created_at = datetime.now(moscow_tz).strftime("%d.%m.%Y %H:%M")
        
        await processing_msg.edit_text(
            f"✅ <b>Задача успешно создана!</b>\n\n"
            f"📌 Номер задачи: <b>#{task_id}</b>\n"
            f"🏢 Отдел: {department_name}\n"
            f"📍 Филиал: {branch}\n"
            f"✏️ Задача: {title}\n"
            f"🕐 Создана: {created_at}"
            f"{files_text}\n\n"
            f"Мы уведомим вас об обновлениях.",
        )
        
        await message.answer(
            "Выберите следующее действие:",
            reply_markup=main_menu_keyboard(),
        )
        
        logger.info(f"User {telegram_user_id} created task #{task_id} in {department_name}, files: {uploaded_count}")
        
    except BitrixClientError as e:
        logger.error(f"Failed to create task for user {telegram_user_id}: {e}")
        await processing_msg.edit_text(
            "❌ <b>Не удалось создать задачу</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
        )
        await message.answer(
            "Выберите действие:",
            reply_markup=main_menu_keyboard(),
        )
    
    await state.clear()


# ═══════════════════════════════════════════════════════════════════
# Мои задачи
# ═══════════════════════════════════════════════════════════════════

def _format_task_date(created_date: str) -> str:
    """Форматировать дату создания задачи."""
    if not created_date:
        return ""
    try:
        dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
        moscow_tz = ZoneInfo("Europe/Moscow")
        dt_moscow = dt.astimezone(moscow_tz)
        return dt_moscow.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return ""


# Порядок сортировки этапов и их эмодзи
STAGE_ORDER = [
    "новая",
    "выполня",  # выполняется, выполняются
    "проверк",  # на проверке
    "заверш",   # завершена, завершено
    "выполнен", # выполнена
    "отменен",  # отменена
]

STAGE_EMOJI = {
    "новая": "🆕",
    "выполня": "⏳",
    "проверк": "👀",
    "заверш": "✅",
    "выполнен": "✅",
    "отменен": "🚫",
}


def _get_stage_sort_key(stage_name: str) -> int:
    """Получить ключ сортировки для этапа."""
    stage_lower = stage_name.lower()
    for i, pattern in enumerate(STAGE_ORDER):
        if pattern in stage_lower:
            return i
    return 100  # Неизвестные этапы в конец


def _get_stage_emoji(stage_name: str) -> str:
    """Получить эмодзи для этапа."""
    stage_lower = stage_name.lower()
    for pattern, emoji in STAGE_EMOJI.items():
        if pattern in stage_lower:
            return emoji
    return "📋"


def _format_tasks_list(tasks: list, title: str) -> str:
    """Форматировать список задач, сгруппированных по отделам и этапам."""
    if not tasks:
        return "📭 <b>Задач не найдено</b>"
    
    # Группируем по отделам, затем по этапам
    depts_dict: dict[str, dict[str, list]] = {}
    
    for task in tasks:
        dept_name = task.get("department_name", "Без отдела")
        stage_name = task.get("stage_name", "") or "Без этапа"
        
        if dept_name not in depts_dict:
            depts_dict[dept_name] = {}
        if stage_name not in depts_dict[dept_name]:
            depts_dict[dept_name][stage_name] = []
        
        depts_dict[dept_name][stage_name].append(task)
    
    lines = [f"📋 <b>{title}</b>\n"]
    
    for dept_name, stages in depts_dict.items():
        # Заголовок отдела
        lines.append(f"\n<b>{dept_name}</b>")
        
        # Сортируем этапы в нужном порядке
        sorted_stages = sorted(stages.keys(), key=_get_stage_sort_key)
        
        for stage_name in sorted_stages:
            stage_tasks = stages[stage_name]
            emoji = _get_stage_emoji(stage_name)
            lines.append(f"  <i>{emoji} {stage_name}:</i>")
            
            for task in stage_tasks:
                task_id = task.get("id", "?")
                title_text = task.get("title", "Без названия")
                date_str = _format_task_date(task.get("createdDate", ""))
                
                if len(title_text) > 55:
                    title_text = title_text[:52] + "..."
                
                date_display = f" • {date_str}" if date_str else ""
                lines.append(f"    • <b>#{task_id}</b> — {title_text}{date_display}")
    
    return "\n".join(lines)


@router.message(F.text == BTN_MY_TASKS)
async def my_tasks(message: types.Message, state: FSMContext) -> None:
    """Показать задачи в работе, сгруппированные по отделам."""
    # Проверка верификации
    if not await _check_verified(message):
        return
    
    await state.clear()
    
    telegram_user_id = message.from_user.id
    
    processing_msg = await message.answer("⏳ Загружаю задачи...")
    
    try:
        # Получаем только задачи в работе (не завершённые, не отменённые)
        tasks = await get_user_tasks(telegram_user_id, limit=30, only_active=True)
        
        if not tasks:
            await processing_msg.edit_text(
                "📭 <b>У вас нет задач в работе</b>\n\n"
                "Все задачи завершены или вы ещё не создавали задач.",
            )
            await message.answer(
                "Хотите посмотреть все задачи, включая завершённые?",
                reply_markup=active_tasks_keyboard(),
            )
            return
        
        text = _format_tasks_list(tasks, f"Ваши задачи в работе ({len(tasks)})")
        
        await processing_msg.edit_text(text)
        
        await message.answer(
            "Показаны только <b>задачи в работе</b>.",
            reply_markup=active_tasks_keyboard(),
        )
        
        logger.info(f"User {telegram_user_id} viewed {len(tasks)} active tasks")
        
    except BitrixClientError as e:
        logger.error(f"Failed to fetch tasks for user {telegram_user_id}: {e}")
        await processing_msg.edit_text(
            "❌ <b>Не удалось загрузить задачи</b>\n\n"
            "Попробуйте позже.",
        )


@router.message(F.text == BTN_SHOW_ALL_TASKS)
async def show_all_tasks(message: types.Message, state: FSMContext) -> None:
    """Показать все задачи пользователя, включая завершённые."""
    await state.clear()
    telegram_user_id = message.from_user.id
    
    processing_msg = await message.answer("⏳ Загружаю все задачи...")
    
    try:
        # Получаем все задачи
        tasks = await get_user_tasks(telegram_user_id, limit=50, only_active=False)
        
        if not tasks:
            await processing_msg.edit_text(
                "📭 <b>У вас пока нет задач</b>\n\n"
                "Нажмите «🆕 Новая задача», чтобы создать первую.",
            )
            await message.answer(
                "Выберите действие:",
                reply_markup=main_menu_keyboard(),
            )
            return
        
        text = _format_tasks_list(tasks, f"Все ваши задачи ({len(tasks)})")
        
        await processing_msg.edit_text(text)
        
        await message.answer(
            "Вы можете отменить задачу или вернуться в меню:",
            reply_markup=all_tasks_actions_keyboard(),
        )
        
        logger.info(f"User {telegram_user_id} viewed all {len(tasks)} tasks")
        
    except BitrixClientError as e:
        logger.error(f"Failed to fetch all tasks for user {telegram_user_id}: {e}")
        await processing_msg.edit_text(
            "❌ <b>Не удалось загрузить задачи</b>\n\n"
            "Попробуйте позже.",
        )
        await message.answer(
            "Выберите действие:",
            reply_markup=main_menu_keyboard(),
        )


# ═══════════════════════════════════════════════════════════════════
# Отмена задачи
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_CANCEL_TASK)
async def cancel_task_start(message: types.Message, state: FSMContext) -> None:
    """Начало процесса отмены задачи."""
    await state.set_state(CancelTaskStates.waiting_for_task_id)
    
    await message.answer(
        "🔢 <b>Введите номер задачи для отмены</b>\n\n"
        "Укажите только цифры, например: <code>39802</code>",
        reply_markup=cancel_keyboard(),
    )


@router.message(CancelTaskStates.waiting_for_task_id)
async def cancel_task_receive_id(message: types.Message, state: FSMContext) -> None:
    """Получили ID задачи для отмены."""
    # Проверка на кнопку "Главное меню"
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(
            "🏠 Вы вернулись в главное меню.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    # Валидация: должно быть число
    task_id_text = message.text.strip()
    if not task_id_text.isdigit():
        await message.answer(
            "❌ Введите только цифры (номер задачи).\n"
            "Например: <code>39802</code>",
            reply_markup=cancel_keyboard(),
        )
        return
    
    task_id = int(task_id_text)
    telegram_user_id = message.from_user.id
    
    # Получаем задачу из Bitrix
    processing_msg = await message.answer("⏳ Проверяю задачу...")
    
    task = await get_task_by_id(task_id)
    
    if not task:
        await processing_msg.edit_text(
            f"❌ Задача <b>#{task_id}</b> не найдена.\n\n"
            "Проверьте номер и попробуйте снова.",
        )
        return
    
    # Проверяем, что задача принадлежит пользователю
    if not verify_task_ownership(task, telegram_user_id):
        await processing_msg.edit_text(
            f"❌ Задача <b>#{task_id}</b> не принадлежит вам.\n\n"
            "Вы можете отменять только свои задачи.",
        )
        return
    
    # Проверяем, можно ли отменить задачу
    can_cancel, reason = await check_task_can_be_cancelled(task)
    if not can_cancel:
        if reason == "completed":
            await processing_msg.edit_text(
                f"❌ <b>Нельзя отменить завершённую задачу</b>\n\n"
                f"Задача <b>#{task_id}</b> уже выполнена.",
            )
        elif reason == "cancelled":
            await processing_msg.edit_text(
                f"❌ <b>Задача уже отменена</b>\n\n"
                f"Задача <b>#{task_id}</b> уже находится в статусе «Отменена».",
            )
        else:
            await processing_msg.edit_text(
                f"❌ <b>Невозможно отменить задачу</b>\n\n"
                f"Задача <b>#{task_id}</b> не может быть отменена.",
            )
        await message.answer(
            "Выберите действие:",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    # Сохраняем данные для подтверждения
    await state.update_data(
        cancel_task_id=task_id,
        cancel_task_title=task.get("title", "Без названия"),
        cancel_task_group_id=task.get("groupId", ""),
    )
    
    await state.set_state(CancelTaskStates.waiting_for_confirm)
    
    await processing_msg.edit_text(
        f"⚠️ <b>Подтвердите отмену задачи</b>\n\n"
        f"<b>#{task_id}</b> — {task.get('title', 'Без названия')}\n\n"
        f"Вы уверены, что хотите отменить эту задачу?",
    )
    
    await message.answer(
        "Выберите действие:",
        reply_markup=confirm_cancel_keyboard(),
    )


@router.message(CancelTaskStates.waiting_for_confirm, F.text == BTN_CONFIRM_CANCEL)
async def cancel_task_confirm(message: types.Message, state: FSMContext) -> None:
    """Подтверждение отмены задачи."""
    data = await state.get_data()
    
    task_id = data.get("cancel_task_id")
    task_title = data.get("cancel_task_title", "Без названия")
    group_id = data.get("cancel_task_group_id", "")
    
    processing_msg = await message.answer("⏳ Отменяю задачу...")
    
    success = await cancel_task(task_id, group_id)
    
    if success:
        await processing_msg.edit_text(
            f"✅ <b>Задача отменена</b>\n\n"
            f"<b>#{task_id}</b> — {task_title}\n\n"
            f"Задача переведена на этап «Отменена».",
        )
        logger.info(f"User {message.from_user.id} cancelled task #{task_id}")
    else:
        await processing_msg.edit_text(
            f"❌ <b>Не удалось отменить задачу</b>\n\n"
            f"Возможно, в проекте нет этапа «Отменена».\n"
            f"Попробуйте позже или обратитесь в поддержку.",
        )
    
    await state.clear()
    await message.answer(
        "Выберите действие:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(CancelTaskStates.waiting_for_confirm, F.text == BTN_REJECT_CANCEL)
async def cancel_task_reject(message: types.Message, state: FSMContext) -> None:
    """Отказ от отмены задачи."""
    await state.clear()
    await message.answer(
        "👌 Отмена задачи отменена.\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard(),
    )
