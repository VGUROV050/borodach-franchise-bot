# Registration handlers for new partners

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    AsyncSessionLocal,
    get_partner_by_telegram_id,
    create_partner,
    get_or_create_branch,
    link_partner_to_branch,
    PartnerStatus,
)
from .keyboards import (
    cancel_keyboard,
    registration_start_keyboard,
    add_more_branches_keyboard,
    BTN_CANCEL,
    BTN_START_REGISTRATION,
    BTN_ADD_MORE_BRANCH,
    BTN_FINISH_REGISTRATION,
)

logger = logging.getLogger(__name__)

router = Router()


class RegistrationStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_city = State()
    waiting_for_address = State()
    waiting_for_branch_name = State()
    waiting_for_more_branches = State()


# ═══════════════════════════════════════════════════════════════════
# Начало регистрации
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_START_REGISTRATION)
async def registration_start(message: types.Message, state: FSMContext) -> None:
    """Начало регистрации нового партнёра."""
    await state.set_state(RegistrationStates.waiting_for_full_name)
    await state.update_data(branches=[])
    
    await message.answer(
        "📝 <b>Регистрация нового партнёра</b>\n\n"
        "Введите ваше <b>ФИО</b> (как в договоре):",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_full_name)
async def registration_full_name(message: types.Message, state: FSMContext) -> None:
    """Получили ФИО → запрашиваем телефон."""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.\n\n"
            "Для доступа к боту необходимо пройти регистрацию.",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        await message.answer(
            "⚠️ Пожалуйста, введите полное ФИО:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_phone)
    
    await message.answer(
        f"✅ ФИО: <b>{full_name}</b>\n\n"
        "📱 Введите ваш <b>номер телефона</b>:\n"
        "Например: +7 999 123-45-67",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_phone)
async def registration_phone(message: types.Message, state: FSMContext) -> None:
    """Получили телефон → запрашиваем город филиала."""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    phone = message.text.strip()
    
    # Простая валидация телефона
    phone_digits = "".join(filter(str.isdigit, phone))
    if len(phone_digits) < 10:
        await message.answer(
            "⚠️ Некорректный номер телефона. Введите номер с кодом страны:\n"
            "Например: +7 999 123-45-67",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_city)
    
    await message.answer(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        "🏙 Теперь укажите <b>город</b> вашего филиала:",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_city)
async def registration_city(message: types.Message, state: FSMContext) -> None:
    """Получили город → запрашиваем адрес."""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    city = message.text.strip()
    
    if len(city) < 2:
        await message.answer(
            "⚠️ Пожалуйста, введите название города:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(current_city=city)
    await state.set_state(RegistrationStates.waiting_for_address)
    
    await message.answer(
        f"✅ Город: <b>{city}</b>\n\n"
        "📍 Введите <b>адрес</b> филиала:\n"
        "Например: ул. Ленина, 15",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_address)
async def registration_address(message: types.Message, state: FSMContext) -> None:
    """Получили адрес → запрашиваем название (ТЦ и т.д.)."""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    address = message.text.strip()
    
    if len(address) < 3:
        await message.answer(
            "⚠️ Пожалуйста, введите полный адрес:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(current_address=address)
    await state.set_state(RegistrationStates.waiting_for_branch_name)
    
    await message.answer(
        f"✅ Адрес: <b>{address}</b>\n\n"
        "🏢 Укажите <b>название</b> (ТЦ, БЦ или другое):\n"
        "Например: ТЦ Мега, БЦ Сити\n\n"
        "Или отправьте <code>-</code> если нет названия.",
        reply_markup=cancel_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_branch_name)
async def registration_branch_name(message: types.Message, state: FSMContext) -> None:
    """Получили название → спрашиваем про ещё филиалы."""
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    branch_name = message.text.strip()
    if branch_name == "-":
        branch_name = None
    
    data = await state.get_data()
    branches = data.get("branches", [])
    
    # Добавляем филиал в список
    branches.append({
        "city": data["current_city"],
        "address": data["current_address"],
        "name": branch_name,
    })
    
    await state.update_data(branches=branches)
    await state.set_state(RegistrationStates.waiting_for_more_branches)
    
    # Формируем список филиалов для отображения
    branches_text = "\n".join([
        f"  • {b['city']}, {b['address']}" + (f" ({b['name']})" if b['name'] else "")
        for b in branches
    ])
    
    await message.answer(
        f"✅ <b>Добавлен филиал:</b>\n"
        f"📍 {data['current_city']}, {data['current_address']}"
        + (f" ({branch_name})" if branch_name else "") +
        f"\n\n<b>Ваши филиалы ({len(branches)}):</b>\n{branches_text}\n\n"
        "Хотите добавить ещё филиал?",
        reply_markup=add_more_branches_keyboard(),
    )


@router.message(RegistrationStates.waiting_for_more_branches, F.text == BTN_ADD_MORE_BRANCH)
async def registration_add_more(message: types.Message, state: FSMContext) -> None:
    """Пользователь хочет добавить ещё филиал."""
    await state.set_state(RegistrationStates.waiting_for_city)
    
    await message.answer(
        "🏙 Введите <b>город</b> следующего филиала:",
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
    
    processing_msg = await message.answer("⏳ Сохраняю данные...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Создаём партнёра
            partner = await create_partner(
                db=db,
                telegram_id=user.id,
                telegram_username=user.username,
                full_name=full_name,
                phone=phone,
            )
            
            # Создаём филиалы и связываем с партнёром
            for branch_data in branches:
                from database.crud import get_or_create_branch
                branch = await get_or_create_branch(
                    db=db,
                    city=branch_data["city"],
                    address=branch_data["address"],
                    name=branch_data.get("name"),
                )
                await link_partner_to_branch(
                    db=db,
                    partner_id=partner.id,
                    branch_id=branch.id,
                    is_owner=True,
                )
        
        await processing_msg.edit_text(
            "✅ <b>Заявка на регистрацию отправлена!</b>\n\n"
            f"👤 ФИО: {full_name}\n"
            f"📱 Телефон: {phone}\n"
            f"🏢 Филиалов: {len(branches)}\n\n"
            "⏳ Ваша заявка будет рассмотрена администратором.\n"
            "Мы уведомим вас о результате.",
        )
        
        logger.info(f"New partner registration: {user.id} ({full_name}), {len(branches)} branches")
        
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

