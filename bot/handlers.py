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
    confirm_description_keyboard,
    attach_files_keyboard,
    done_files_keyboard,
    BTN_NEW_TASK, 
    BTN_MY_TASKS,
    BTN_CANCEL,
    BTN_ADD_COMMENT,
    BTN_CONTINUE,
    BTN_ATTACH_FILES,
    BTN_SKIP_FILES,
    BTN_DONE_FILES,
    DEPT_BUTTON_TO_KEY,
)
from bitrix import create_task, get_user_tasks, format_task_stage, BitrixClientError, upload_file_to_task

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
# Новая задача — Шаг 1: Выбор отдела
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_NEW_TASK)
async def new_task_start(message: types.Message, state: FSMContext) -> None:
    """Начало создания задачи — выбор отдела."""
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
        "✏️ <b>Введите краткий заголовок задачи:</b>\n\n"
        "Например: «Ремонт кондиционера» или «Заказ расходников»",
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
            "Пожалуйста, введите заголовок задачи:",
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
        f"✏️ Заголовок: {data['title']}\n\n"
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
        f"✏️ Заголовок: {data['title']}\n\n"
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
        
        await processing_msg.edit_text(
            f"✅ <b>Задача успешно создана!</b>\n\n"
            f"📌 Номер задачи: <b>#{task_id}</b>\n"
            f"🏢 Отдел: {department_name}\n"
            f"📍 Филиал: {branch}\n"
            f"✏️ Заголовок: {title}"
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

@router.message(F.text == BTN_MY_TASKS)
async def my_tasks(message: types.Message, state: FSMContext) -> None:
    """Показать список задач пользователя."""
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
        
        lines = ["📋 <b>Ваши задачи:</b>\n"]
        
        for task in tasks:
            task_id = task.get("id", "?")
            title = task.get("title", "Без названия")
            stage = format_task_stage(task.get("stage_name", ""))
            
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
