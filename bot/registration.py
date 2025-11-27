# Registration handlers for new partners

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import AsyncSessionLocal, create_partner
from .keyboards import (
    cancel_keyboard,
    registration_start_keyboard,
    share_contact_keyboard,
    add_more_branches_keyboard,
    BTN_CANCEL,
    BTN_START_REGISTRATION,
    BTN_ADD_MORE_BRANCH,
    BTN_FINISH_REGISTRATION,
)

logger = logging.getLogger(__name__)

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_contact = State()
    waiting_for_full_name = State()
    waiting_for_branch = State()
    waiting_for_more_branches = State()


# ═══════════════════════════════════════════════════════════════════
# Начало регистрации
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_START_REGISTRATION)
async def registration_start(message: types.Message, state: FSMContext) -> None:
    """Начало регистрации нового партнёра."""
    await state.set_state(RegistrationStates.waiting_for_contact)
    await state.update_data(branches=[])
    
    await message.answer(
        "📝 <b>Регистрация нового партнёра</b>\n\n"
        "Для начала поделитесь вашим контактом.\n"
        "Нажмите кнопку ниже 👇",
        reply_markup=share_contact_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 1: Получение контакта
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_contact, F.contact)
async def registration_contact(message: types.Message, state: FSMContext) -> None:
    """Получили контакт → запрашиваем ФИО."""
    contact = message.contact
    
    # Проверяем, что это контакт самого пользователя
    if contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Пожалуйста, поделитесь <b>своим</b> контактом, а не чужим.",
            reply_markup=share_contact_keyboard(),
        )
        return
    
    # Сохраняем телефон
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    
    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_full_name)
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        "👤 Введите ваше <b>ФИО</b> (как в договоре франшизы):",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_contact, F.text == BTN_CANCEL)
async def registration_contact_cancel(message: types.Message, state: FSMContext) -> None:
    """Отмена на этапе контакта."""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.\n\n"
        "Для доступа к боту необходимо пройти регистрацию.",
        reply_markup=registration_start_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_contact)
async def registration_contact_invalid(message: types.Message, state: FSMContext) -> None:
    """Неверный ввод — ждём контакт."""
    await message.answer(
        "⚠️ Пожалуйста, нажмите кнопку «📱 Поделиться контактом» ниже.\n\n"
        "Это необходимо для верификации.",
        reply_markup=share_contact_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 2: ФИО
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_full_name, F.text == BTN_CANCEL)
async def registration_name_cancel(message: types.Message, state: FSMContext) -> None:
    """Отмена на этапе ФИО."""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.",
        reply_markup=registration_start_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_full_name)
async def registration_full_name(message: types.Message, state: FSMContext) -> None:
    """Получили ФИО → запрашиваем филиал."""
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        await message.answer(
            "⚠️ Пожалуйста, введите полное ФИО:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_branch)
    
    await message.answer(
        f"✅ ФИО: <b>{full_name}</b>\n\n"
        "🏢 <b>Укажите ваш филиал</b>\n\n"
        "Напишите как вам удобно, например:\n"
        "• Москва, Мега Тёплый Стан\n"
        "• Казань, ТЦ Кольцо\n"
        "• СПб Невский проспект",
        reply_markup=cancel_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 3: Филиал
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_branch, F.text == BTN_CANCEL)
async def registration_branch_cancel(message: types.Message, state: FSMContext) -> None:
    """Отмена на этапе филиала."""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.",
        reply_markup=registration_start_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_branch)
async def registration_branch(message: types.Message, state: FSMContext) -> None:
    """Получили филиал → спрашиваем про ещё филиалы."""
    branch_text = message.text.strip()
    
    if len(branch_text) < 3:
        await message.answer(
            "⚠️ Пожалуйста, укажите филиал подробнее:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    data = await state.get_data()
    branches = data.get("branches", [])
    branches.append(branch_text)
    
    await state.update_data(branches=branches)
    await state.set_state(RegistrationStates.waiting_for_more_branches)
    
    # Формируем список филиалов для отображения
    branches_list = "\n".join([f"  • {b}" for b in branches])
    
    await message.answer(
        f"✅ <b>Филиал добавлен:</b> {branch_text}\n\n"
        f"<b>Ваши филиалы ({len(branches)}):</b>\n{branches_list}\n\n"
        "Хотите добавить ещё филиал?",
        reply_markup=add_more_branches_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 4: Ещё филиалы или завершение
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_more_branches, F.text == BTN_ADD_MORE_BRANCH)
async def registration_add_more(message: types.Message, state: FSMContext) -> None:
    """Пользователь хочет добавить ещё филиал."""
    await state.set_state(RegistrationStates.waiting_for_branch)
    
    await message.answer(
        "🏢 Укажите следующий филиал:",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_more_branches, F.text == BTN_FINISH_REGISTRATION)
async def registration_finish(message: types.Message, state: FSMContext) -> None:
    """Завершение регистрации — сохраняем в БД."""
    data = await state.get_data()
    
    user = message.from_user
    full_name = data.get("full_name")
    phone = data.get("phone")
    branches = data.get("branches", [])
    
    # Формируем текст филиалов для сохранения
    branches_text = "\n".join(branches) if branches else None
    
    processing_msg = await message.answer("⏳ Сохраняю данные...")
    
    try:
        async with AsyncSessionLocal() as db:
            partner = await create_partner(
                db=db,
                telegram_id=user.id,
                telegram_username=user.username,
                telegram_first_name=user.first_name,
                telegram_last_name=user.last_name,
                full_name=full_name,
                phone=phone,
                branches_text=branches_text,
            )
        
        branches_list = "\n".join([f"  • {b}" for b in branches])
        
        await processing_msg.edit_text(
            "✅ <b>Заявка на регистрацию отправлена!</b>\n\n"
            f"👤 ФИО: {full_name}\n"
            f"📱 Телефон: {phone}\n"
            f"🏢 Филиалы:\n{branches_list}\n\n"
            "⏳ Ваша заявка будет рассмотрена администратором.\n"
            "Мы уведомим вас о результате.",
        )
        
        # Показываем кнопку проверки статуса
        from .keyboards import pending_verification_keyboard
        await message.answer(
            "Нажмите кнопку ниже, чтобы проверить статус заявки:",
            reply_markup=pending_verification_keyboard(),
        )
        
        logger.info(f"New partner registration: {user.id} ({full_name}), branches: {branches}")
        
    except Exception as e:
        logger.error(f"Failed to create partner: {e}")
        await processing_msg.edit_text(
            "❌ <b>Ошибка при регистрации</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
        )
    
    await state.clear()


@router.message(RegistrationStates.waiting_for_more_branches)
async def registration_more_invalid(message: types.Message, state: FSMContext) -> None:
    """Неверный выбор."""
    await message.answer(
        "⚠️ Выберите действие из кнопок ниже:",
        reply_markup=add_more_branches_keyboard(),
    )
