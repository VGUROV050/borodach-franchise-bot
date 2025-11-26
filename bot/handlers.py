# Bot handlers

import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import DEPARTMENTS
from .keyboards import (
    main_menu_keyboard, 
    cancel_keyboard,
    department_keyboard,
    BTN_NEW_TASK, 
    BTN_MY_TASKS,
    BTN_CANCEL,
    DEPT_BUTTON_TO_KEY,
)
from bitrix import create_task, get_user_tasks, format_task_stage, BitrixClientError

logger = logging.getLogger(__name__)

router = Router()


# ═══════════════════════════════════════════════════════════════════
# FSM States для создания задачи
# ═══════════════════════════════════════════════════════════════════

class NewTaskStates(StatesGroup):
    waiting_for_department = State()
    waiting_for_branch = State()
    waiting_for_description = State()


# ═══════════════════════════════════════════════════════════════════
# Отмена / Возврат в главное меню (из любого состояния)
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_CANCEL)
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    """Возврат в главное меню из любого состояния."""
    current_state = await state.get_state()
    
    if current_state is not None:
        logger.info(f"User {message.from_user.id} cancelled from state {current_state}")
        await state.clear()
    
    await message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=main_menu_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Обработчик команды /start."""
    # Сбрасываем состояние, если пользователь был в процессе создания задачи
    await state.clear()
    
    await message.answer(
        "👋 Привет! Это бот для франчайзи <b>BORODACH</b>.\n\n"
        "Здесь вы можете:\n"
        "• 🆕 Создать задачу в управляющую компанию\n"
        "• 📋 Посмотреть свои задачи\n\n"
        "Выберите действие в меню ниже 👇",
        reply_markup=main_menu_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Новая задача
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_NEW_TASK)
async def new_task_start(message: types.Message, state: FSMContext) -> None:
    """Начало создания новой задачи — спрашиваем отдел."""
    await state.set_state(NewTaskStates.waiting_for_department)
    
    await message.answer(
        "🏢 <b>В какой отдел вы хотите поставить задачу?</b>\n\n"
        "Выберите отдел:",
        reply_markup=department_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_department, F.text.in_(DEPT_BUTTON_TO_KEY.keys()))
async def new_task_department(message: types.Message, state: FSMContext) -> None:
    """Получили отдел — спрашиваем филиал."""
    dept_key = DEPT_BUTTON_TO_KEY[message.text]
    dept_info = DEPARTMENTS[dept_key]
    
    # Проверяем что group_id и responsible_id настроены
    if not dept_info["group_id"] or not dept_info["responsible_id"]:
        await message.answer(
            f"❌ Отдел «{dept_info['name']}» пока не настроен.\n"
            "Обратитесь к администратору.",
            reply_markup=department_keyboard(),
        )
        return
    
    # Сохраняем выбранный отдел в FSM
    await state.update_data(
        department_key=dept_key,
        department_name=dept_info["name"],
        group_id=dept_info["group_id"],
        responsible_id=dept_info["responsible_id"],
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


@router.message(NewTaskStates.waiting_for_branch)
async def new_task_branch(message: types.Message, state: FSMContext) -> None:
    """Получили филиал — спрашиваем описание задачи."""
    branch = message.text.strip()
    
    if not branch:
        await message.answer(
            "Пожалуйста, укажите филиал:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    # Сохраняем филиал в FSM
    await state.update_data(branch=branch)
    await state.set_state(NewTaskStates.waiting_for_description)
    
    await message.answer(
        "📝 <b>Опишите, пожалуйста, задачу для УК как можно конкретнее:</b>",
        reply_markup=cancel_keyboard(),
    )


@router.message(NewTaskStates.waiting_for_description)
async def new_task_description(message: types.Message, state: FSMContext) -> None:
    """Получили описание — создаём задачу в Bitrix."""
    description = message.text.strip()
    
    if not description:
        await message.answer(
            "Пожалуйста, опишите задачу:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    # Получаем сохранённые данные
    data = await state.get_data()
    group_id = data.get("group_id")
    responsible_id = data.get("responsible_id")
    department_name = data.get("department_name", "Не указан")
    branch = data.get("branch", "Не указан")
    
    # Данные пользователя
    user = message.from_user
    telegram_user_id = user.id
    telegram_username = user.username
    telegram_name = user.full_name
    
    # Отправляем сообщение о процессе
    processing_msg = await message.answer("⏳ Создаю задачу...")
    
    try:
        task_id = await create_task(
            group_id=group_id,
            responsible_id=responsible_id,
            department_name=department_name,
            branch=branch,
            description=description,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            telegram_name=telegram_name,
        )
        
        await processing_msg.edit_text(
            f"✅ <b>Задача успешно создана!</b>\n\n"
            f"📌 Номер задачи: <b>#{task_id}</b>\n"
            f"🏢 Отдел: {department_name}\n"
            f"📍 Филиал: {branch}\n\n"
            f"Мы уведомим вас об обновлениях.",
        )
        
        # Возвращаем главное меню
        await message.answer(
            "Выберите следующее действие:",
            reply_markup=main_menu_keyboard(),
        )
        
        logger.info(f"User {telegram_user_id} created task #{task_id} in {department_name}")
        
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
    
    # Сбрасываем состояние
    await state.clear()


# ═══════════════════════════════════════════════════════════════════
# Мои задачи
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_MY_TASKS)
async def my_tasks(message: types.Message, state: FSMContext) -> None:
    """Показать список задач пользователя."""
    # Сбрасываем состояние, если был в процессе создания задачи
    await state.clear()
    
    telegram_user_id = message.from_user.id
    
    processing_msg = await message.answer("⏳ Загружаю задачи...")
    
    try:
        tasks = await get_user_tasks(telegram_user_id, limit=10)
        
        if not tasks:
            await processing_msg.edit_text(
                "📭 <b>У вас пока нет задач</b>\n\n"
                "Нажмите «🆕 Новая задача», чтобы создать первую.",
            )
            return
        
        # Формируем список задач
        lines = ["📋 <b>Ваши задачи:</b>\n"]
        
        for task in tasks:
            task_id = task.get("id", "?")
            title = task.get("title", "Без названия")
            stage = format_task_stage(task.get("stage_name", ""))
            
            # Обрезаем длинные названия
            if len(title) > 40:
                title = title[:37] + "..."
            
            lines.append(f"• <b>#{task_id}</b> — {title}\n  {stage}")
        
        await processing_msg.edit_text("\n".join(lines))
        
        logger.info(f"User {telegram_user_id} viewed {len(tasks)} tasks")
        
    except BitrixClientError as e:
        logger.error(f"Failed to fetch tasks for user {telegram_user_id}: {e}")
        await processing_msg.edit_text(
            "❌ <b>Не удалось загрузить задачи</b>\n\n"
            "Попробуйте позже.",
        )
