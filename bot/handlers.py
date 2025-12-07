# Bot handlers

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import DEPARTMENTS


def clean_html_for_telegram(text: str) -> str:
    """
    Очистить HTML от неподдерживаемых Telegram тегов.
    Telegram поддерживает: <b>, <i>, <u>, <s>, <code>, <pre>, <a>, <tg-spoiler>
    """
    if not text:
        return text
    
    # Убираем span и другие неподдерживаемые теги, оставляя содержимое
    text = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', text, flags=re.DOTALL)
    
    # Убираем style атрибуты из разрешённых тегов
    text = re.sub(r'<(b|i|u|s|code|pre|a)([^>]*?)style="[^"]*"([^>]*)>', r'<\1\2\3>', text)
    
    # Заменяем <br> на перенос строки
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # Убираем любые другие неизвестные теги
    allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler']
    pattern = r'<(?!/?({})\b)[^>]+>'.format('|'.join(allowed_tags))
    text = re.sub(pattern, '', text)
    
    # Убираем множественные переносы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
from database import AsyncSessionLocal, get_partner_by_telegram_id, PartnerStatus
from .keyboards import (
    main_menu_keyboard,
    tasks_menu_keyboard,
    barbershops_menu_keyboard,
    account_menu_keyboard,
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
    useful_departments_keyboard,
    useful_actions_keyboard,
    statistics_period_keyboard,
    rating_period_keyboard,
    ai_assistant_keyboard,
    BTN_TASKS,
    BTN_ACCOUNT,
    BTN_MY_BARBERSHOPS,
    BTN_STATISTICS,
    BTN_STATS_CURRENT_MONTH,
    BTN_STATS_PREV_MONTH,
    BTN_STATS_TODAY,
    BTN_STATS_YESTERDAY,
    BTN_STATS_RATING,
    BTN_RATING_CURRENT,
    BTN_RATING_PREV,
    BTN_USEFUL,
    BTN_CONTACT_OFFICE_MAIN,
    BTN_USEFUL_DEVELOPMENT,
    BTN_USEFUL_MARKETING,
    BTN_USEFUL_DESIGN,
    BTN_IMPORTANT_INFO,
    BTN_CONTACT_DEPARTMENT,
    BTN_MAIN_MENU,
    BTN_BACK,
    BTN_ADD_BARBERSHOP,
    BTN_NEW_TASK,
    BTN_AI_ASSISTANT,
    BTN_AI_MORE_DETAILS, 
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
    waiting_for_barbershop = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_confirm = State()
    waiting_for_comment = State()
    waiting_for_files_choice = State()
    waiting_for_files = State()


class CancelTaskStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_confirm = State()


class AddBarbershopStates(StatesGroup):
    waiting_for_barbershop_text = State()


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


@router.message(F.text == BTN_CONTACT_OFFICE_MAIN)
async def contact_office_handler(message: types.Message, state: FSMContext) -> None:
    """Показать информацию для связи с офисом."""
    if not await _check_verified(message):
        return
    
    await state.clear()
    
    # Получаем текст из настроек бота
    from database import get_bot_setting, init_default_bot_settings
    
    async with AsyncSessionLocal() as db:
        # Инициализируем настройки по умолчанию если их нет
        await init_default_bot_settings(db)
        text = await get_bot_setting(db, "contact_office_text")
    
    if not text:
        text = (
            "📞 <b>Связаться с офисом</b>\n\n"
            "Информация временно недоступна.\n"
            "Обратитесь к администратору."
        )
    
    await message.answer(
        text,
        reply_markup=main_menu_keyboard(),
        disable_web_page_preview=True,
    )


# ═══════════════════════════════════════════════════════════════════
# Аккаунт
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_ACCOUNT)
async def account_handler(message: types.Message, state: FSMContext) -> None:
    """Показать информацию об аккаунте пользователя."""
    if not await _check_verified(message):
        return
    
    await state.clear()
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        
        if not partner:
            await message.answer("❌ Профиль не найден.", reply_markup=main_menu_keyboard())
            return
        
        from database import get_partner_companies
        companies = await get_partner_companies(db, partner.id)
        has_pending = partner.has_pending_branch
        pending_text = partner.branches_text or ""
    
    # Формируем информацию об аккаунте
    text_parts = ["👤 <b>Ваш аккаунт</b>\n"]
    
    # Имя
    text_parts.append(f"📛 <b>Имя:</b> {partner.full_name}")
    
    # Телефон (скрываем первые цифры)
    if partner.phone:
        phone_masked = f"****{partner.phone[-4:]}" if len(partner.phone) >= 4 else "****"
        text_parts.append(f"📱 <b>Телефон:</b> +7 {phone_masked}")
    
    # Барбершопы (показываем все)
    text_parts.append(f"\n💈 <b>Барбершопы:</b> {len(companies)}")
    if companies:
        for c in companies:
            text_parts.append(f"   • {c.name}")
    else:
        text_parts.append("   Нет привязанных барбершопов")
    
    # Показываем информацию о заявке если есть
    if has_pending and pending_text:
        text_parts.append(
            f"\n📝 <b>Заявка на добавление:</b>\n"
            f"   <i>{pending_text}</i>\n"
            f"   ⏳ Статус: <b>На рассмотрении</b>"
        )
    
    # Получаем статистику по задачам
    try:
        tasks = await get_user_tasks(message.from_user.id, only_active=False)
        
        # Считаем задачи по статусам
        task_counts = {"new": 0, "in_progress": 0, "on_review": 0, "completed": 0, "cancelled": 0}
        for task in tasks:
            stage = format_task_stage(task.get("stage"))
            if stage == "Новая":
                task_counts["new"] += 1
            elif stage == "В работе":
                task_counts["in_progress"] += 1
            elif stage == "На проверке":
                task_counts["on_review"] += 1
            elif stage == "Завершена":
                task_counts["completed"] += 1
            elif stage == "Отменена":
                task_counts["cancelled"] += 1
        
        total_tasks = len(tasks)
        text_parts.append(f"\n📋 <b>Задачи:</b> {total_tasks}")
        if total_tasks > 0:
            text_parts.append(f"   🆕 Новые: {task_counts['new']}")
            text_parts.append(f"   ⏳ В работе: {task_counts['in_progress']}")
            text_parts.append(f"   🔍 На проверке: {task_counts['on_review']}")
            text_parts.append(f"   ✅ Завершено: {task_counts['completed']}")
    except Exception:
        text_parts.append("\n📋 <b>Задачи:</b> —")
    
    # Даты
    if partner.created_at:
        tz = ZoneInfo("Europe/Moscow")
        created = partner.created_at.astimezone(tz).strftime("%d.%m.%Y")
        text_parts.append(f"\n📅 <b>Регистрация:</b> {created}")
    
    if partner.verified_at:
        tz = ZoneInfo("Europe/Moscow")
        verified = partner.verified_at.astimezone(tz).strftime("%d.%m.%Y")
        text_parts.append(f"✅ <b>Верификация:</b> {verified}")
    
    await message.answer("\n".join(text_parts), reply_markup=account_menu_keyboard())


@router.message(F.text == BTN_ADD_BARBERSHOP)
async def add_barbershop_start(message: types.Message, state: FSMContext) -> None:
    """Начало добавления барбершопа."""
    if not await _check_verified(message):
        return
    
    # Проверяем, нет ли уже заявки на рассмотрении
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        if partner and partner.has_pending_branch:
            await message.answer(
                "⏳ <b>У вас уже есть заявка на рассмотрении</b>\n\n"
                f"📝 <i>{partner.branches_text}</i>\n\n"
                "Дождитесь её обработки администратором.",
                reply_markup=account_menu_keyboard(),
            )
            return
    
    await state.set_state(AddBarbershopStates.waiting_for_barbershop_text)
    
    await message.answer(
        "💈 <b>Добавление барбершопа</b>\n\n"
        "Укажите информацию о вашем барбершопе:\n"
        "• Город\n"
        "• Адрес\n"
        "• Название (если есть)\n\n"
        "Например: <i>Москва, ул. Примерная, д.1, БЦ Пример</i>",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddBarbershopStates.waiting_for_barbershop_text)
async def add_barbershop_process(message: types.Message, state: FSMContext) -> None:
    """Обработка текста барбершопа."""
    if message.text == BTN_MAIN_MENU:
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    barbershop_text = message.text.strip()
    
    if len(barbershop_text) < 5:
        await message.answer(
            "❌ Слишком короткое описание. Пожалуйста, укажите город и адрес.",
            reply_markup=cancel_keyboard(),
        )
        return
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        
        if partner:
            from database import update_partner_for_branch_request
            await update_partner_for_branch_request(db, partner.id, barbershop_text)
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Заявка на добавление барбершопа отправлена!</b>\n\n"
        f"📍 {barbershop_text}\n\n"
        "Администратор рассмотрит вашу заявку и привяжет барбершоп.\n"
        "Вы получите уведомление, когда барбершоп будет добавлен.",
        reply_markup=main_menu_keyboard(),
    )
    
    logger.info(f"Partner {message.from_user.id} requested new barbershop: {barbershop_text}")


# ═══════════════════════════════════════════════════════════════════
# Статистика по барбершопам (YClients)
# ═══════════════════════════════════════════════════════════════════

class StatisticsStates(StatesGroup):
    """Состояния для раздела Статистика."""
    selecting_period = State()


class RatingStates(StatesGroup):
    """Состояния для раздела Рейтинг."""
    selecting_period = State()


class AIAssistantStates(StatesGroup):
    """Состояния для AI-ассистента (обучение)."""
    waiting_for_question = State()


@router.message(F.text == BTN_STATISTICS)
async def statistics_handler(message: types.Message, state: FSMContext) -> None:
    """Показать статистику по барбершопам из YClients (текущий месяц по умолчанию)."""
    if not await _check_verified(message):
        return
    
    # Показываем статистику за текущий месяц и меню выбора периода
    await _show_statistics(message, state, period_type="current_month")


async def _show_statistics(
    message: types.Message, 
    state: FSMContext, 
    period_type: str = "current_month"
) -> None:
    """Показать статистику за указанный период."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    await state.set_state(StatisticsStates.selecting_period)
    
    # Показываем сообщение о загрузке
    loading_msg = await message.answer("⏳ Загружаю статистику из YClients...")
    
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        
        if not partner:
            await loading_msg.delete()
            await message.answer("❌ Партнёр не найден", reply_markup=main_menu_keyboard())
            return
        
        from database import get_partner_companies, get_network_rating_by_company
        companies = await get_partner_companies(db, partner.id)
    
    if not companies:
        await loading_msg.delete()
        await message.answer(
            "📊 <b>Статистика по барбершопам</b>\n\n"
            "У вас пока нет привязанных барбершопов.\n"
            "Обратитесь к администратору для привязки.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    # Определяем период
    tz = ZoneInfo("Europe/Moscow")
    today = datetime.now(tz)
    
    if period_type == "today":
        date_from = today.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = today
        period_title = f"📊 <b>Статистика за сегодня</b>\n📅 {today.strftime('%d.%m.%Y')}\n"
    elif period_type == "yesterday":
        yesterday = today - timedelta(days=1)
        date_from = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = yesterday.replace(hour=23, minute=59, second=59)
        period_title = f"📊 <b>Статистика за вчера</b>\n📅 {yesterday.strftime('%d.%m.%Y')}\n"
    elif period_type == "prev_month":
        # Первый день прошлого месяца
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        date_from = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_to = last_day_prev_month.replace(hour=23, minute=59, second=59)
        period_title = f"📊 <b>Статистика за прошлый месяц</b>\n📅 {date_from.strftime('%d.%m')} - {date_to.strftime('%d.%m.%Y')}\n"
    else:  # current_month
        date_from = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_to = today
        period_title = f"📊 <b>Статистика за текущий месяц</b>\n📅 {date_from.strftime('%d.%m')} - {date_to.strftime('%d.%m.%Y')}\n"
    
    # Получаем статистику по каждому барбершопу
    from yclients import get_period_revenue
    
    stats_text = period_title
    total_revenue = 0
    total_completed = 0
    
    for company in companies:
        barbershop_name = company.name
        yclients_id = company.yclients_id
        
        if not yclients_id:
            stats_text += f"\n💈 <b>{barbershop_name}</b>\n"
            stats_text += "   ⚠️ YClients ID не указан\n"
            continue
        
        # Получаем выручку за период
        result = await get_period_revenue(
            yclients_id, 
            date_from.strftime("%Y-%m-%d"),
            date_to.strftime("%Y-%m-%d")
        )
        
        if result.get("success"):
            revenue = result.get("revenue", 0)
            completed = result.get("completed_count", 0)
            total_count = result.get("total_count", 0)
            
            total_revenue += revenue
            total_completed += completed
            
            stats_text += f"\n💈 <b>{barbershop_name}</b>\n"
            stats_text += f"   💰 Выручка: <b>{revenue:,.0f} ₽</b>\n"
            stats_text += f"   ✅ Завершено: {completed} из {total_count} записей\n"
            
            # Рейтинг показываем для текущего и прошлого месяца
            if period_type in ("current_month", "prev_month"):
                async with AsyncSessionLocal() as db:
                    if period_type == "current_month":
                        # Текущий рейтинг
                        rating = await get_network_rating_by_company(db, yclients_id)
                        if rating and rating.rank > 0:
                            rank_text = f"   🏆 Рейтинг в сети: <b>{rating.rank}</b> из {rating.total_companies}"
                            
                            if rating.previous_rank and rating.previous_rank > 0:
                                change = rating.previous_rank - rating.rank
                                if change > 0:
                                    rank_text += f" <b>↑{change}</b> 📈"
                                elif change < 0:
                                    rank_text += f" <b>↓{abs(change)}</b> 📉"
                                else:
                                    rank_text += " ➡️"
                            
                            stats_text += rank_text + "\n"
                            
                            if rating.avg_check > 0:
                                stats_text += f"   💵 Средний чек: <b>{rating.avg_check:,.0f} ₽</b>\n"
                    else:
                        # Рейтинг за прошлый месяц из истории
                        from database import get_rating_history
                        
                        prev_month_date = date_from
                        history = await get_rating_history(db, prev_month_date.year, prev_month_date.month)
                        
                        # Ищем рейтинг для этого барбершопа
                        rating_entry = next((h for h in history if h.yclients_company_id == yclients_id), None)
                        
                        if rating_entry and rating_entry.rank > 0:
                            total_in_history = len(history)
                            rank_text = f"   🏆 Рейтинг в сети: <b>{rating_entry.rank}</b> из {total_in_history}"
                            stats_text += rank_text + "\n"
                            
                            if rating_entry.avg_check and rating_entry.avg_check > 0:
                                stats_text += f"   💵 Средний чек: <b>{rating_entry.avg_check:,.0f} ₽</b>\n"
        else:
            stats_text += f"\n💈 <b>{barbershop_name}</b>\n"
            stats_text += f"   ❌ {result.get('error', 'Ошибка загрузки')}\n"
    
    # Итого (если несколько барбершопов)
    if len(companies) > 1 and total_revenue > 0:
        stats_text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        stats_text += f"📈 <b>Итого:</b>\n"
        stats_text += f"   💰 Выручка: <b>{total_revenue:,.0f} ₽</b>\n"
        stats_text += f"   ✅ Завершено записей: {total_completed}"
    
    # Удаляем сообщение о загрузке и отправляем результат
    await loading_msg.delete()
    await message.answer(stats_text, reply_markup=statistics_period_keyboard())


# Обработчики периодов статистики
@router.message(StatisticsStates.selecting_period, F.text == BTN_STATS_CURRENT_MONTH)
async def stats_current_month(message: types.Message, state: FSMContext) -> None:
    """Статистика за текущий месяц."""
    await _show_statistics(message, state, "current_month")


@router.message(StatisticsStates.selecting_period, F.text == BTN_STATS_PREV_MONTH)
async def stats_prev_month(message: types.Message, state: FSMContext) -> None:
    """Статистика за прошлый месяц."""
    await _show_statistics(message, state, "prev_month")


@router.message(StatisticsStates.selecting_period, F.text == BTN_STATS_TODAY)
async def stats_today(message: types.Message, state: FSMContext) -> None:
    """Статистика за сегодня."""
    await _show_statistics(message, state, "today")


@router.message(StatisticsStates.selecting_period, F.text == BTN_STATS_YESTERDAY)
async def stats_yesterday(message: types.Message, state: FSMContext) -> None:
    """Статистика за вчера."""
    await _show_statistics(message, state, "yesterday")


@router.message(StatisticsStates.selecting_period, F.text == BTN_BACK)
async def stats_back_to_menu(message: types.Message, state: FSMContext) -> None:
    """Назад в главное меню."""
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=main_menu_keyboard())


# ═══════════════════════════════════════════════════════════════════
# Рейтинг сети
# ═══════════════════════════════════════════════════════════════════

@router.message(StatisticsStates.selecting_period, F.text == BTN_STATS_RATING)
async def rating_menu_handler(message: types.Message, state: FSMContext) -> None:
    """Переход в раздел рейтинга."""
    await state.set_state(RatingStates.selecting_period)
    await message.answer(
        "🏆 <b>Рейтинг сети</b>\n\n"
        "Выберите период:",
        reply_markup=rating_period_keyboard(),
    )


@router.message(RatingStates.selecting_period, F.text == BTN_RATING_CURRENT)
async def rating_current_month(message: types.Message, state: FSMContext) -> None:
    """Рейтинг за текущий месяц."""
    await _show_rating(message, state, is_current_month=True)


@router.message(RatingStates.selecting_period, F.text == BTN_RATING_PREV)
async def rating_prev_month(message: types.Message, state: FSMContext) -> None:
    """Рейтинг за прошлый месяц."""
    await _show_rating(message, state, is_current_month=False)


@router.message(RatingStates.selecting_period, F.text == BTN_BACK)
async def rating_back_to_stats(message: types.Message, state: FSMContext) -> None:
    """Назад к статистике."""
    await state.set_state(StatisticsStates.selecting_period)
    await message.answer(
        "📊 <b>Статистика</b>\n\nВыберите период:",
        reply_markup=statistics_period_keyboard(),
    )


def _format_location(city: str | None) -> str:
    """Форматировать локацию: для Москвы/СПб - город, для остальных - область."""
    if not city:
        return "—"
    
    city_lower = city.lower()
    
    # Москва и Санкт-Петербург показываем как город
    if "москва" in city_lower or "moscow" in city_lower:
        return "Москва"
    if "санкт-петербург" in city_lower or "петербург" in city_lower or "спб" in city_lower:
        return "Санкт-Петербург"
    
    # Для остальных пытаемся определить область/регион
    # Если город содержит "область" или "край" - оставляем как есть
    if "область" in city_lower or "край" in city_lower or "респ" in city_lower:
        return city
    
    # Иначе просто возвращаем город
    return city


def _format_rank_change(current_rank: int, previous_rank: int | None) -> str:
    """Форматировать изменение позиции."""
    if previous_rank is None or previous_rank == 0:
        return "🆕"
    
    change = previous_rank - current_rank
    if change > 0:
        return f"↑{change}"
    elif change < 0:
        return f"↓{abs(change)}"
    else:
        return "—"


async def _show_rating(message: types.Message, state: FSMContext, is_current_month: bool) -> None:
    """Показать рейтинг сети."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from database import (
        get_partner_companies, 
        get_all_network_ratings, 
        get_rating_history,
        get_previous_month_ranks,
    )
    
    loading_msg = await message.answer("⏳ Загружаю рейтинг...")
    
    tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(tz)
    
    async with AsyncSessionLocal() as db:
        # Получаем салоны партнёра
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        if not partner:
            await loading_msg.edit_text("❌ Партнёр не найден")
            return
        
        partner_companies = await get_partner_companies(db, partner.id)
        partner_yclients_ids = {c.yclients_id for c in partner_companies}
        
        if is_current_month:
            # Текущий месяц
            all_ratings = await get_all_network_ratings(db)
            period_title = f"🏆 <b>Рейтинг сети — {now.strftime('%B %Y')}</b>\n"
            
            # Получаем предыдущие ранги для сравнения
            if now.month == 1:
                prev_year, prev_month = now.year - 1, 12
            else:
                prev_year, prev_month = now.year, now.month - 1
            prev_ranks = await get_previous_month_ranks(db, prev_year, prev_month)
        else:
            # Прошлый месяц
            if now.month == 1:
                target_year, target_month = now.year - 1, 12
            else:
                target_year, target_month = now.year, now.month - 1
            
            all_ratings = await get_rating_history(db, target_year, target_month)
            
            month_names = {
                1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
                5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
                9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
            }
            period_title = f"🏆 <b>Рейтинг сети — {month_names[target_month]} {target_year}</b>\n"
            
            # Получаем ранги за позапрошлый месяц для сравнения
            if target_month == 1:
                prev_year, prev_month = target_year - 1, 12
            else:
                prev_year, prev_month = target_year, target_month - 1
            prev_ranks = await get_previous_month_ranks(db, prev_year, prev_month)
    
    if not all_ratings:
        await loading_msg.edit_text(
            f"{period_title}\n"
            "❌ Данные рейтинга недоступны.\n"
            "Попробуйте позже.",
        )
        return
    
    # Сортируем по рангу
    sorted_ratings = sorted(all_ratings, key=lambda x: x.rank if x.rank else 999)
    total_companies = len(sorted_ratings)
    
    # Находим позиции салонов партнёра
    partner_positions = []
    for r in sorted_ratings:
        yclients_id = r.yclients_company_id
        if yclients_id in partner_yclients_ids:
            partner_positions.append(r)
    
    # Формируем текст рейтинга
    lines = [period_title, f"📊 Всего салонов: {total_companies}\n"]
    
    # Определяем какие позиции показывать
    positions_to_show = set()
    
    # Всегда показываем топ-3
    positions_to_show.update([1, 2, 3])
    
    # Добавляем позиции партнёра ± 2
    for pr in partner_positions:
        rank = pr.rank or 0
        if rank > 3:  # Если партнёр не в топ-3
            for r in range(max(1, rank - 2), min(total_companies + 1, rank + 3)):
                positions_to_show.add(r)
    
    # Формируем список для отображения
    shown_ranks = sorted(positions_to_show)
    
    # Проверяем нужен ли разделитель между топ-3 и позициями партнёра
    need_separator = False
    for pr in partner_positions:
        if pr.rank and pr.rank > 5:  # Если есть разрыв
            need_separator = True
            break
    
    prev_rank_shown = 0
    for r in sorted_ratings:
        rank = r.rank or 0
        if rank not in shown_ranks:
            continue
        
        # Добавляем разделитель если есть разрыв
        if prev_rank_shown > 0 and rank - prev_rank_shown > 1:
            lines.append("   ···")
        prev_rank_shown = rank
        
        yclients_id = r.yclients_company_id
        is_partner = yclients_id in partner_yclients_ids
        
        # Получаем изменение позиции
        prev_rank = prev_ranks.get(yclients_id)
        change_str = _format_rank_change(rank, prev_rank)
        
        # Форматируем локацию
        location = _format_location(r.city)
        
        # Форматируем выручку
        revenue = r.revenue or 0
        revenue_str = f"{revenue:,.0f}".replace(",", " ")
        
        # Медаль для топ-3
        if rank == 1:
            medal = "🥇"
        elif rank == 2:
            medal = "🥈"
        elif rank == 3:
            medal = "🥉"
        else:
            medal = f"{rank}."
        
        # Выделяем салон партнёра
        if is_partner:
            lines.append(f"\n<b>👉 {medal} {location}</b>")
            lines.append(f"    💰 {revenue_str} ₽  {change_str}")
        else:
            lines.append(f"\n{medal} {location}")
            lines.append(f"    💰 {revenue_str} ₽  {change_str}")
    
    # Добавляем информацию о салонах партнёра если не в списке
    if not partner_positions:
        lines.append("\n\n⚠️ <i>Ваши салоны пока не в рейтинге</i>")
    
    # Удаляем сообщение загрузки и отправляем результат
    await loading_msg.delete()
    await message.answer(
        "\n".join(lines),
        reply_markup=rating_period_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Полезное
# ═══════════════════════════════════════════════════════════════════

class UsefulStates(StatesGroup):
    """Состояния для раздела Полезное."""
    selecting_department = State()
    in_department = State()


# Маппинг кнопок на типы отделов
USEFUL_DEPT_MAP = {
    BTN_USEFUL_DEVELOPMENT: "development",
    BTN_USEFUL_MARKETING: "marketing",
    BTN_USEFUL_DESIGN: "design",
}

DEPT_NAMES = {
    "development": "🚀 Отдел Развития",
    "marketing": "📢 Отдел Маркетинга",
    "design": "🎨 Отдел Дизайна",
}


@router.message(F.text == BTN_USEFUL)
async def useful_handler(message: types.Message, state: FSMContext) -> None:
    """Раздел Полезное — выбор отдела."""
    if not await _check_verified(message):
        return
    
    await state.clear()
    await state.set_state(UsefulStates.selecting_department)
    
    await message.answer(
        "📚 <b>Полезное</b>\n\n"
        "Выберите отдел:",
        reply_markup=useful_departments_keyboard(),
    )


@router.message(UsefulStates.selecting_department, F.text.in_(USEFUL_DEPT_MAP.keys()))
async def useful_department_selected(message: types.Message, state: FSMContext) -> None:
    """Выбран отдел — показываем действия."""
    dept_key = USEFUL_DEPT_MAP[message.text]
    
    # Получаем кастомные кнопки из БД
    from database import get_department_buttons, DepartmentType
    
    async with AsyncSessionLocal() as db:
        custom_buttons = await get_department_buttons(db, DepartmentType(dept_key))
    
    # Сохраняем тексты кнопок в состоянии для обработки кликов
    button_texts = [btn.button_text for btn in custom_buttons]
    
    await state.update_data(
        selected_department=dept_key,
        custom_button_texts=button_texts,
    )
    await state.set_state(UsefulStates.in_department)
    
    dept_name = DEPT_NAMES.get(dept_key, message.text)
    
    await message.answer(
        f"{dept_name}\n\n"
        "Выберите действие:",
        reply_markup=useful_actions_keyboard(custom_buttons),
    )


def _is_not_standard_button(message: types.Message) -> bool:
    """Фильтр: пропускаем только кнопку Назад и Главное меню."""
    standard_buttons = {BTN_BACK, BTN_MAIN_MENU}
    return message.text not in standard_buttons


@router.message(UsefulStates.in_department, _is_not_standard_button)
async def useful_custom_button_handler(message: types.Message, state: FSMContext) -> None:
    """Обработчик кастомных кнопок из БД."""
    data = await state.get_data()
    dept_key = data.get("selected_department")
    custom_button_texts = data.get("custom_button_texts", [])
    
    if not dept_key:
        await state.clear()
        await message.answer("Ошибка. Вернитесь в главное меню.", reply_markup=main_menu_keyboard())
        return
    
    # Проверяем, является ли это кастомной кнопкой
    if message.text not in custom_button_texts:
        # Не кастомная кнопка - игнорируем
        return
    
    # Получаем кнопку из БД
    from database import get_department_button_by_text, get_department_buttons, DepartmentType
    
    async with AsyncSessionLocal() as db:
        button = await get_department_button_by_text(
            db,
            DepartmentType(dept_key),
            message.text,
        )
        custom_buttons = await get_department_buttons(db, DepartmentType(dept_key))
    
    if button and button.message_text:
        text = clean_html_for_telegram(button.message_text)
    else:
        text = "Информация временно недоступна."
    
    await message.answer(
        text,
        reply_markup=useful_actions_keyboard(custom_buttons),
        disable_web_page_preview=True,
    )


@router.message(UsefulStates.selecting_department, F.text == BTN_MAIN_MENU)
@router.message(UsefulStates.in_department, F.text == BTN_MAIN_MENU)
async def useful_back_to_main(message: types.Message, state: FSMContext) -> None:
    """Возврат в главное меню из Полезное."""
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=main_menu_keyboard())


@router.message(UsefulStates.in_department, F.text == BTN_BACK)
async def useful_back_to_departments(message: types.Message, state: FSMContext) -> None:
    """Возврат к выбору отдела."""
    await state.set_state(UsefulStates.selecting_department)
    await message.answer(
        "📚 <b>Полезное</b>\n\n"
        "Выберите отдел:",
        reply_markup=useful_departments_keyboard(),
    )


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
        "• 💈 Управлять своими барбершопами\n\n"
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
    """Шаг 1: Получили отдел → показываем барбершопы пользователя."""
    dept_key = DEPT_BUTTON_TO_KEY[message.text]
    dept_info = DEPARTMENTS[dept_key]
    
    if not dept_info["group_id"] or not dept_info["responsible_id"]:
        await message.answer(
            f"❌ Отдел «{dept_info['name']}» пока не настроен.\n"
            "Обратитесь к администратору.",
            reply_markup=department_keyboard(),
        )
        return
    
    # Получаем барбершопы пользователя
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
        if partner:
            from database import get_partner_companies
            companies = await get_partner_companies(db, partner.id)
        else:
            companies = []
    
    await state.update_data(
        department_key=dept_key,
        department_name=dept_info["name"],
        group_id=dept_info["group_id"],
        responsible_id=dept_info["responsible_id"],
        files=[],  # Список для файлов
    )
    await state.set_state(NewTaskStates.waiting_for_barbershop)
    
    if companies:
        # Показываем кнопки с барбершопами
        from bot.keyboards import barbershop_select_keyboard
        await message.answer(
            f"✅ Отдел: <b>{dept_info['name']}</b>\n\n"
            "💈 <b>Выберите барбершоп:</b>",
            reply_markup=barbershop_select_keyboard(companies),
        )
    else:
        # Нет привязанных барбершопов - просим ввести текстом
        await message.answer(
            f"✅ Отдел: <b>{dept_info['name']}</b>\n\n"
            "📍 <b>По какому барбершопу вы хотите поставить задачу?</b>\n\n"
            "У вас нет привязанных барбершопов. Укажите город, ТЦ или адрес:",
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
# Новая задача — Шаг 2: Барбершоп
# ═══════════════════════════════════════════════════════════════════

@router.message(NewTaskStates.waiting_for_barbershop)
async def new_task_barbershop(message: types.Message, state: FSMContext) -> None:
    """Шаг 2: Получили барбершоп → спрашиваем заголовок."""
    if not message.text:
        await message.answer("Пожалуйста, выберите барбершоп из списка.")
        return
    
    text = message.text.strip()
    
    # Проверяем отмену
    if text == BTN_MAIN_MENU:
        await state.clear()
        await message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    # Убираем префикс 💈 если он есть (выбор кнопкой)
    prefix = "💈 "
    if text.startswith(prefix):
        barbershop = text[len(prefix):].strip()
    else:
        barbershop = text
    
    if not barbershop:
        await message.answer(
            "Пожалуйста, выберите или укажите барбершоп:",
            reply_markup=cancel_keyboard(),
        )
        return
    
    await state.update_data(barbershop=barbershop)
    await state.set_state(NewTaskStates.waiting_for_title)
    
    await message.answer(
        f"💈 Барбершоп: <b>{barbershop}</b>\n\n"
        "✏️ <b>Введите краткое название задачи:</b>\n\n"
        "Например: «Обновить цены» или «Добавить сотрудника в Yclients»",
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
        f"📍 Барбершоп: {data['barbershop']}\n"
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
        f"📍 Барбершоп: {data['barbershop']}\n"
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
    barbershop = data.get("barbershop", "Не указан")
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
            branch=barbershop,  # Передаём barbershop как branch в Bitrix
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
            f"📍 Барбершоп: {barbershop}\n"
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


def _extract_barbershop_from_title(title: str) -> tuple[str, str]:
    """
    Извлечь барбершоп из названия задачи.
    Формат названия: [Барбершоп] Заголовок
    
    Returns:
        (barbershop, clean_title)
    """
    import re
    match = re.match(r'\[(.+?)\]\s*(.+)', title)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "Не указан", title


def _format_tasks_list(tasks: list, title: str) -> str:
    """Форматировать список задач: Барбершоп → Отдел → Статус."""
    if not tasks:
        return "📭 <b>Задач не найдено</b>"
    
    # Группируем: барбершоп → отдел → статус → задачи
    grouped: dict[str, dict[str, dict[str, list]]] = {}
    
    for task in tasks:
        full_title = task.get("title", "Без названия")
        barbershop, clean_title = _extract_barbershop_from_title(full_title)
        dept_name = task.get("department_name", "Без отдела")
        stage_name = task.get("stage_name", "") or "Без этапа"
        
        # Сохраняем чистый заголовок в задаче
        task["clean_title"] = clean_title
        
        if barbershop not in grouped:
            grouped[barbershop] = {}
        if dept_name not in grouped[barbershop]:
            grouped[barbershop][dept_name] = {}
        if stage_name not in grouped[barbershop][dept_name]:
            grouped[barbershop][dept_name][stage_name] = []
        
        grouped[barbershop][dept_name][stage_name].append(task)
    
    lines = [f"📋 <b>{title}</b>"]
    
    for barbershop, departments in grouped.items():
        # Всегда показываем название барбершопа
        lines.append(f"\n💈 <b>{barbershop}</b>")
        
        for dept_name, stages in departments.items():
            lines.append(f"  📁 <i>{dept_name}</i>")
            
            # Сортируем этапы в нужном порядке
            sorted_stages = sorted(stages.keys(), key=_get_stage_sort_key)
            
            for stage_name in sorted_stages:
                stage_tasks = stages[stage_name]
                emoji = _get_stage_emoji(stage_name)
                
                lines.append(f"    <i>{emoji} {stage_name}:</i>")
                
                for task in stage_tasks:
                    task_id = task.get("id", "?")
                    title_text = task.get("clean_title", "Без названия")
                    date_str = _format_task_date(task.get("createdDate", ""))
                    
                    if len(title_text) > 50:
                        title_text = title_text[:47] + "..."
                    
                    date_display = f" • {date_str}" if date_str else ""
                    lines.append(f"      • <b>#{task_id}</b> — {title_text}{date_display}")
    
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


# ═══════════════════════════════════════════════════════════════════
# AI-ассистент — вопросы по базе знаний
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_AI_ASSISTANT)
async def ai_assistant_start(message: types.Message, state: FSMContext) -> None:
    """Открыть раздел AI-ассистента для вопросов по обучению."""
    if not await _check_verified(message):
        return
    
    await state.set_state(AIAssistantStates.waiting_for_question)
    
    await message.answer(
        "🤖 <b>AI-ассистент</b>\n\n"
        "Я помогу найти ответы в базе знаний:\n"
        "• Управление барбершопом\n"
        "• KPI и показатели\n"
        "• Планирование\n"
        "• Мотивация персонала\n"
        "• И многое другое\n\n"
        "💬 <b>Просто напишите ваш вопрос</b>",
        reply_markup=ai_assistant_keyboard(),
    )


@router.message(AIAssistantStates.waiting_for_question, F.text == BTN_MAIN_MENU)
async def ai_assistant_back(message: types.Message, state: FSMContext) -> None:
    """Вернуться в главное меню из AI-ассистента."""
    await state.clear()
    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard(),
    )


@router.message(AIAssistantStates.waiting_for_question, F.text == BTN_AI_MORE_DETAILS)
async def ai_assistant_more_details(message: types.Message, state: FSMContext) -> None:
    """Подробный ответ на предыдущий вопрос с данными партнёра."""
    from bot.ai_assistant import get_smart_answer
    
    data = await state.get_data()
    last_question = data.get("last_question")
    
    if not last_question:
        await message.answer(
            "🤔 Сначала задайте вопрос, чтобы получить подробный ответ.",
            reply_markup=ai_assistant_keyboard(show_more_button=False),
        )
        return
    
    loading_msg = await message.answer("📊 Готовлю подробный анализ с вашими данными...")
    
    try:
        # Получаем подробный ответ с данными партнёра
        detailed_answer = await get_smart_answer(
            user_message=last_question,
            telegram_id=message.from_user.id,
            detailed=True,  # Подробный ответ
        )
        
        await loading_msg.delete()
        
        if detailed_answer:
            await message.answer(
                f"📊 <b>Подробный анализ:</b>\n\n{detailed_answer}\n\n"
                "💬 Можете задать новый вопрос.",
                reply_markup=ai_assistant_keyboard(show_more_button=False),
            )
        else:
            await message.answer(
                "🤔 Не удалось получить подробный ответ.\n"
                "Попробуйте задать вопрос иначе.",
                reply_markup=ai_assistant_keyboard(show_more_button=False),
            )
        
        # Очищаем контекст после подробного ответа
        await state.update_data(last_question=None)
        
    except Exception as e:
        logger.error(f"Smart detailed error: {e}")
        await loading_msg.delete()
        await message.answer(
            "❌ Произошла ошибка.\nПопробуйте позже.",
            reply_markup=ai_assistant_keyboard(show_more_button=False),
        )


@router.message(AIAssistantStates.waiting_for_question, F.text)
async def ai_assistant_question(message: types.Message, state: FSMContext) -> None:
    """Обработка вопроса пользователя — умный ответ с данными партнёра."""
    from bot.ai_assistant import get_smart_answer
    
    user_question = message.text.strip()
    
    if len(user_question) < 3:
        await message.answer(
            "🤔 Пожалуйста, задайте более развёрнутый вопрос.",
            reply_markup=ai_assistant_keyboard(show_more_button=False),
        )
        return
    
    # Показываем индикатор загрузки
    loading_msg = await message.answer("🔍 Анализирую данные и ищу ответ...")
    
    try:
        # Получаем умный ответ с учётом данных партнёра
        answer = await get_smart_answer(
            user_message=user_question,
            telegram_id=message.from_user.id,
            detailed=False,  # Краткий ответ
        )
        
        await loading_msg.delete()
        
        if answer:
            # Сохраняем вопрос для "Подробнее"
            await state.update_data(last_question=user_question)
            
            await message.answer(
                f"🤖 {answer}\n\n"
                "👆 Нажмите «📖 Подробнее» для развёрнутого ответа",
                reply_markup=ai_assistant_keyboard(show_more_button=True),
            )
        else:
            await state.update_data(last_question=None)
            await message.answer(
                "🤔 К сожалению, не удалось найти ответ.\n\n"
                "Попробуйте переформулировать вопрос.",
                reply_markup=ai_assistant_keyboard(show_more_button=False),
            )
    except Exception as e:
        logger.error(f"Smart answer error: {e}")
        await loading_msg.delete()
        await message.answer(
            "❌ Произошла ошибка.\nПопробуйте позже.",
            reply_markup=ai_assistant_keyboard(show_more_button=False),
        )


# ═══════════════════════════════════════════════════════════════════
# Fallback handler — обработка неожиданных сообщений
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text)
async def fallback_handler(message: types.Message, state: FSMContext) -> None:
    """
    Обработка любых текстовых сообщений, которые не попали в другие хэндлеры.
    Использует AI для понимания намерения пользователя.
    """
    # Проверяем, верифицирован ли пользователь
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_telegram_id(db, message.from_user.id)
    
    if not partner or partner.status != PartnerStatus.VERIFIED:
        # Для неверифицированных — просто предлагаем регистрацию
        await message.answer(
            "👋 Для использования бота необходимо пройти регистрацию.\n\n"
            "Нажмите кнопку «📝 Пройти регистрацию».",
            reply_markup=registration_start_keyboard(),
        )
        return
    
    # Для верифицированных — используем AI
    user_text = message.text.strip()
    
    # Игнорируем слишком короткие сообщения
    if len(user_text) < 2:
        await message.answer(
            "🤔 Используйте кнопки меню для навигации.",
            reply_markup=main_menu_keyboard(),
        )
        return
    
    # Импортируем AI-функции для навигации
    from .ai_assistant import (
        get_ai_suggestion, 
        get_fallback_suggestion,
    )
    
    logger.info(f"[Fallback] User {message.from_user.id} sent: '{user_text[:50]}...'")
    
    # Используем AI для подсказки навигации
    suggestion = await get_ai_suggestion(user_text)
    
    if suggestion:
        logger.info(f"[Fallback] Using AI response for user {message.from_user.id}")
        await message.answer(
            f"💡 {suggestion}",
            reply_markup=main_menu_keyboard(),
        )
    else:
        # Если AI недоступен — используем ключевые слова
        logger.info(f"[Fallback] Using keyword fallback for user {message.from_user.id}")
        fallback = get_fallback_suggestion(user_text)
        await message.answer(fallback, reply_markup=main_menu_keyboard())
