# Registration handlers for new partners

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import AsyncSessionLocal, create_partner
from .keyboards import (
    cancel_registration_keyboard,
    registration_start_keyboard,
    share_contact_keyboard,
    add_more_barbershops_keyboard,
    BTN_CANCEL_REGISTRATION,
    BTN_START_REGISTRATION,
    BTN_ADD_MORE_BARBERSHOP,
    BTN_FINISH_REGISTRATION,
)

logger = logging.getLogger(__name__)

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_contact = State()
    waiting_for_full_name = State()
    waiting_for_barbershop = State()
    waiting_for_more_barbershops = State()


# ═══════════════════════════════════════════════════════════════════
# Начало регистрации
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_START_REGISTRATION)
async def registration_start(message: types.Message, state: FSMContext) -> None:
    """Начало регистрации нового партнёра."""
    await state.set_state(RegistrationStates.waiting_for_contact)
    await state.update_data(barbershops=[])
    
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
    await _process_contact(message, state)


async def _process_contact(message: types.Message, state: FSMContext) -> None:
    """Обработка контакта (общая логика)."""
    logger.info(f"_process_contact called: user={message.from_user.id}")
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
    
    # Инициализируем данные если их нет (после перезапуска бота)
    data = await state.get_data()
    if not data.get("barbershops"):
        await state.update_data(barbershops=[])
    
    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_full_name)
    
    current_state = await state.get_state()
    logger.info(f"State set to: {current_state} for user {message.from_user.id}")
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        "👤 Введите ваше <b>ФИО</b> (как в договоре франшизы):",
        reply_markup=cancel_registration_keyboard(),
    )


# Fallback: контакт без состояния (после перезапуска бота)
@router.message(F.contact)
async def registration_contact_fallback(message: types.Message, state: FSMContext) -> None:
    """Получили контакт без FSM состояния — начинаем регистрацию."""
    logger.info(f"Contact received without state, processing as registration: {message.from_user.id}")
    await _process_contact(message, state)


@router.message(RegistrationStates.waiting_for_contact, F.text == BTN_CANCEL_REGISTRATION)
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

@router.message(RegistrationStates.waiting_for_full_name, F.text == BTN_CANCEL_REGISTRATION)
async def registration_name_cancel(message: types.Message, state: FSMContext) -> None:
    """Отмена на этапе ФИО."""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.",
        reply_markup=registration_start_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_full_name, F.contact)
async def registration_name_contact_ignored(message: types.Message, state: FSMContext) -> None:
    """Игнорируем контакт на этапе ФИО."""
    await message.answer(
        "⚠️ Контакт уже получен. Пожалуйста, введите ваше <b>ФИО</b>:",
        reply_markup=cancel_registration_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_full_name, F.text)
async def registration_full_name(message: types.Message, state: FSMContext) -> None:
    """Получили ФИО → запрашиваем барбершоп."""
    logger.info(f"registration_full_name called: user={message.from_user.id}, text={message.text}")
    
    if message.text == BTN_CANCEL_REGISTRATION:
        return  # Обрабатывается другим хендлером
    
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        await message.answer(
            "⚠️ Пожалуйста, введите полное ФИО:",
            reply_markup=cancel_registration_keyboard(),
        )
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_barbershop)
    
    await message.answer(
        f"✅ ФИО: <b>{full_name}</b>\n\n"
        "💈 <b>Укажите ваш барбершоп</b>\n\n"
        "Напишите как вам удобно, например:\n"
        "• Москва, Мега Тёплый Стан\n"
        "• Казань, ТЦ Кольцо\n"
        "• СПб Невский проспект",
        reply_markup=cancel_registration_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 3: Барбершоп
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_barbershop, F.text == BTN_CANCEL_REGISTRATION)
async def registration_barbershop_cancel(message: types.Message, state: FSMContext) -> None:
    """Отмена на этапе барбершопа."""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.",
        reply_markup=registration_start_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_barbershop, F.contact)
async def registration_barbershop_contact_ignored(message: types.Message, state: FSMContext) -> None:
    """Игнорируем контакт на этапе барбершопа."""
    await message.answer(
        "⚠️ Контакт уже получен. Пожалуйста, укажите ваш барбершоп:",
        reply_markup=cancel_registration_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_barbershop, F.text)
async def registration_barbershop(message: types.Message, state: FSMContext) -> None:
    """Получили барбершоп → спрашиваем про ещё барбершопы."""
    if message.text == BTN_CANCEL_REGISTRATION:
        return  # Обрабатывается другим хендлером
    
    barbershop_text = message.text.strip()
    
    if len(barbershop_text) < 3:
        await message.answer(
            "⚠️ Пожалуйста, укажите барбершоп подробнее:",
            reply_markup=cancel_registration_keyboard(),
        )
        return
    
    data = await state.get_data()
    barbershops = data.get("barbershops", [])
    barbershops.append(barbershop_text)
    
    await state.update_data(barbershops=barbershops)
    await state.set_state(RegistrationStates.waiting_for_more_barbershops)
    
    # Формируем список барбершопов для отображения
    barbershops_list = "\n".join([f"  • {b}" for b in barbershops])
    
    await message.answer(
        f"✅ <b>Барбершоп добавлен:</b> {barbershop_text}\n\n"
        f"<b>Ваши барбершопы ({len(barbershops)}):</b>\n{barbershops_list}\n\n"
        "Хотите добавить ещё барбершоп?",
        reply_markup=add_more_barbershops_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 4: Ещё барбершопы или завершение
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_more_barbershops, F.text == BTN_ADD_MORE_BARBERSHOP)
async def registration_add_more(message: types.Message, state: FSMContext) -> None:
    """Пользователь хочет добавить ещё барбершоп."""
    await state.set_state(RegistrationStates.waiting_for_barbershop)
    
    await message.answer(
        "💈 Укажите следующий барбершоп:",
        reply_markup=cancel_registration_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_more_barbershops, F.text == BTN_FINISH_REGISTRATION)
async def registration_finish(message: types.Message, state: FSMContext) -> None:
    """Завершение регистрации — сохраняем в БД."""
    data = await state.get_data()
    
    user = message.from_user
    full_name = data.get("full_name")
    phone = data.get("phone")
    barbershops = data.get("barbershops", [])
    
    # Формируем текст барбершопов для сохранения
    branches_text = "\n".join(barbershops) if barbershops else None
    
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
        
        barbershops_list = "\n".join([f"  • {b}" for b in barbershops])
        
        await processing_msg.edit_text(
            "✅ <b>Заявка на регистрацию отправлена!</b>\n\n"
            f"👤 ФИО: {full_name}\n"
            f"📱 Телефон: {phone}\n"
            f"💈 Барбершопы:\n{barbershops_list}\n\n"
            "⏳ Ваша заявка будет рассмотрена администратором.\n"
            "Мы уведомим вас о результате.",
        )
        
        # Показываем кнопку проверки статуса
        from .keyboards import pending_verification_keyboard
        await message.answer(
            "Нажмите кнопку ниже, чтобы проверить статус заявки:",
            reply_markup=pending_verification_keyboard(),
        )
        
        logger.info(f"New partner registration: {user.id} ({full_name}), barbershops: {barbershops}")
        
    except Exception as e:
        logger.error(f"Failed to create partner: {e}")
        await processing_msg.edit_text(
            "❌ <b>Ошибка при регистрации</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
        )
    
    await state.clear()


@router.message(RegistrationStates.waiting_for_more_barbershops)
async def registration_more_invalid(message: types.Message, state: FSMContext) -> None:
    """Неверный выбор."""
    await message.answer(
        "⚠️ Выберите действие из кнопок ниже:",
        reply_markup=add_more_barbershops_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Fallback: кнопка отмены без состояния
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_CANCEL_REGISTRATION)
async def registration_cancel_fallback(message: types.Message, state: FSMContext) -> None:
    """Отмена без FSM состояния (после перезапуска бота)."""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.\n\n"
        "Для доступа к боту необходимо пройти регистрацию.",
        reply_markup=registration_start_keyboard(),
    )
