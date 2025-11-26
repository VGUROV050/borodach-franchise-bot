# Bot handlers

import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from .keyboards import main_menu_keyboard, BTN_NEW_TASK, BTN_MY_TASKS
from bitrix import create_task, get_user_tasks, format_task_status, BitrixClientError

logger = logging.getLogger(__name__)

router = Router()


# ═══════════════════════════════════════════════════════════════════
# FSM States для создания задачи
# ═══════════════════════════════════════════════════════════════════

class NewTaskStates(StatesGroup):
    waiting_for_branch = State()
    waiting_for_description = State()


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
    """Начало создания новой задачи — спрашиваем филиал."""
    await state.set_state(NewTaskStates.waiting_for_branch)
    
    await message.answer(
        "📍 <b>По какому филиалу вы хотите поставить задачу?</b>\n\n"
        "Укажите город, ТЦ или адрес:",
    )


@router.message(NewTaskStates.waiting_for_branch)
async def new_task_branch(message: types.Message, state: FSMContext) -> None:
    """Получили филиал — спрашиваем описание задачи."""
    branch = message.text.strip()
    
    if not branch:
        await message.answer("Пожалуйста, укажите филиал:")
        return
    
    # Сохраняем филиал в FSM
    await state.update_data(branch=branch)
    await state.set_state(NewTaskStates.waiting_for_description)
    
    await message.answer(
        "📝 <b>Опишите, пожалуйста, задачу для УК как можно конкретнее:</b>",
    )


@router.message(NewTaskStates.waiting_for_description)
async def new_task_description(message: types.Message, state: FSMContext) -> None:
    """Получили описание — создаём задачу в Bitrix."""
    description = message.text.strip()
    
    if not description:
        await message.answer("Пожалуйста, опишите задачу:")
        return
    
    # Получаем сохранённый филиал
    data = await state.get_data()
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
            branch=branch,
            description=description,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            telegram_name=telegram_name,
        )
        
        await processing_msg.edit_text(
            f"✅ <b>Задача успешно создана!</b>\n\n"
            f"📌 Номер задачи: <b>#{task_id}</b>\n"
            f"📍 Филиал: {branch}\n\n"
            f"Мы уведомим вас об обновлениях.",
        )
        
        logger.info(f"User {telegram_user_id} created task #{task_id}")
        
    except BitrixClientError as e:
        logger.error(f"Failed to create task for user {telegram_user_id}: {e}")
        await processing_msg.edit_text(
            "❌ <b>Не удалось создать задачу</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
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
            status = format_task_status(task.get("status", ""))
            
            # Обрезаем длинные названия
            if len(title) > 40:
                title = title[:37] + "..."
            
            lines.append(f"• <b>#{task_id}</b> — {title}\n  {status}")
        
        await processing_msg.edit_text("\n".join(lines))
        
        logger.info(f"User {telegram_user_id} viewed {len(tasks)} tasks")
        
    except BitrixClientError as e:
        logger.error(f"Failed to fetch tasks for user {telegram_user_id}: {e}")
        await processing_msg.edit_text(
            "❌ <b>Не удалось загрузить задачи</b>\n\n"
            "Попробуйте позже.",
        )
