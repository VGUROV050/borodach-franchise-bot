# Admin panel routes

import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from config.settings import BASE_DIR, ADMIN_USERNAME, ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN
from database import (
    AsyncSessionLocal,
    get_all_partners,
    get_pending_partners,
    update_partner_status,
    PartnerStatus,
    Partner,
    get_partners_with_pending_branches,
    clear_partner_pending_branch,
)
from .auth import (
    verify_session, 
    create_session, 
    check_brute_force,
    set_secure_cookie,
    delete_session,
    get_csrf_token,
    _get_client_ip,
    _record_failed_attempt,
    _clear_failed_attempts,
)

logger = logging.getLogger(__name__)


async def send_telegram_notification(
    chat_id: int, 
    text: str, 
    show_main_menu: bool = False,
    show_registration: bool = False,
) -> bool:
    """Отправить уведомление пользователю через Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping notification")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    
    # Добавляем клавиатуру главного меню
    if show_main_menu:
        payload["reply_markup"] = {
            "keyboard": [
                [{"text": "📋 Задачи"}, {"text": "📚 Полезное"}],
                [{"text": "📊 Статистика"}, {"text": "👤 Аккаунт"}],
                [{"text": "🤖 AI-ассистент"}],
            ],
            "resize_keyboard": True,
            "input_field_placeholder": "Выберите раздел",
        }
    # Добавляем клавиатуру регистрации
    elif show_registration:
        payload["reply_markup"] = {
            "keyboard": [
                [{"text": "📝 Пройти регистрацию"}]
            ],
            "resize_keyboard": True,
            "input_field_placeholder": "Нажмите для регистрации",
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Notification sent to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send notification: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

router = APIRouter()
templates = Jinja2Templates(directory=f"{BASE_DIR}/admin/templates")


# ═══════════════════════════════════════════════════════════════════
# Health Check (публичный эндпоинт для мониторинга)
# ═══════════════════════════════════════════════════════════════════

# Время запуска сервиса
_start_time = datetime.now()


@router.get("/health", response_class=JSONResponse)
async def health_check():
    """
    Health check эндпоинт для мониторинга состояния сервиса.
    Не требует авторизации.
    """
    # Проверяем подключение к БД
    db_status = "ok"
    db_error = None
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = str(e)
    
    # Вычисляем uptime
    uptime = datetime.now() - _start_time
    uptime_str = str(uptime).split('.')[0]  # Убираем микросекунды
    
    status = "healthy" if db_status == "ok" else "unhealthy"
    
    response = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "uptime": uptime_str,
        "components": {
            "database": {
                "status": db_status,
                "error": db_error,
            }
        }
    }
    
    status_code = 200 if status == "healthy" else 503
    return JSONResponse(content=response, status_code=status_code)


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics эндпоинт.
    Не требует авторизации для scraping.
    """
    from fastapi.responses import Response
    from utils.metrics import get_metrics, get_metrics_content_type
    
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


# ═══════════════════════════════════════════════════════════════════
# Авторизация
# ═══════════════════════════════════════════════════════════════════

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа."""
    # Если уже авторизован — редирект на главную
    if verify_session(request):
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Обработка входа с защитой от brute-force."""
    # Проверяем блокировку по IP
    try:
        check_brute_force(request)
    except HTTPException as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": e.detail,
        })
    
    ip = _get_client_ip(request)
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Успешный вход — очищаем счётчик неудачных попыток
        _clear_failed_attempts(ip)
        
        session_token, csrf_token = create_session(username)
        response = RedirectResponse(url="/", status_code=302)
        
        # Используем secure cookie
        set_secure_cookie(response, "session_token", session_token)
        
        logger.info(f"Admin login successful from {ip}")
        return response
    
    # Неудачная попытка — записываем
    _record_failed_attempt(ip)
    logger.warning(f"Failed admin login attempt from {ip}")
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Неверный логин или пароль",
    })


@router.get("/logout")
async def logout(request: Request):
    """Выход."""
    # Удаляем сессию из хранилища
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response


# ═══════════════════════════════════════════════════════════════════
# Главная страница (Dashboard)
# ═══════════════════════════════════════════════════════════════════

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная страница — список заявок."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    async with AsyncSessionLocal() as db:
        pending = await get_all_partners(db, status=PartnerStatus.PENDING)
        verified = await get_all_partners(db, status=PartnerStatus.VERIFIED, limit=10)
        rejected = await get_all_partners(db, status=PartnerStatus.REJECTED, limit=10)
        pending_branches = await get_partners_with_pending_branches(db)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "pending_partners": pending,
        "verified_partners": verified,
        "rejected_partners": rejected,
        "pending_count": len(pending),
        "pending_branches": pending_branches,
        "pending_branches_count": len(pending_branches),
    })


# ═══════════════════════════════════════════════════════════════════
# Партнёры
# ═══════════════════════════════════════════════════════════════════

@router.get("/partners", response_class=HTMLResponse)
async def partners_list(
    request: Request,
    status: Optional[str] = None,
):
    """Список всех партнёров."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    partner_status = None
    if status:
        try:
            partner_status = PartnerStatus(status)
        except ValueError:
            pass
    
    async with AsyncSessionLocal() as db:
        partners = await get_all_partners(db, status=partner_status, limit=100)
    
    return templates.TemplateResponse("partners.html", {
        "request": request,
        "partners": partners,
        "current_status": status,
    })


@router.get("/partners/{partner_id}/verify", response_class=HTMLResponse)
async def verify_partner_page(
    request: Request,
    partner_id: int,
):
    """Страница верификации партнёра с выбором барбершопов YClients."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import Partner
    from database import get_all_yclients_companies
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        
        # Получаем барбершопы из YClients
        companies = await get_all_yclients_companies(db, only_active=True)
    
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    
    return templates.TemplateResponse("verify_partner.html", {
        "request": request,
        "partner": partner,
        "companies": companies,
    })


@router.post("/partners/{partner_id}/verify")
async def verify_partner(
    request: Request,
    partner_id: int,
    company_ids: list[int] = Form(default=[]),
):
    """Верифицировать партнёра с привязкой к барбершопам YClients."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database.crud import link_partner_to_company
    from sqlalchemy import select
    from database.models import Partner
    
    async with AsyncSessionLocal() as db:
        # Получаем партнёра для telegram_id
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner_data = result.scalar_one_or_none()
        telegram_id = partner_data.telegram_id if partner_data else None
        partner_name = partner_data.full_name if partner_data else ""
        
        # Обновляем статус
        partner = await update_partner_status(
            db=db,
            partner_id=partner_id,
            status=PartnerStatus.VERIFIED,
            verified_by="admin",
        )
        
        if not partner:
            raise HTTPException(status_code=404, detail="Партнёр не найден")
        
        # Привязываем к барбершопам YClients
        for company_id in company_ids:
            await link_partner_to_company(
                db=db,
                partner_id=partner_id,
                company_id=company_id,
                is_owner=True,
            )
    
    # Отправляем уведомление пользователю с главным меню
    if telegram_id:
        await send_telegram_notification(
            telegram_id,
            f"🎉 <b>Поздравляем, {partner_name}!</b>\n\n"
            f"Ваша заявка на регистрацию одобрена!\n\n"
            f"Теперь вы можете:\n"
            f"• 🆕 Создавать задачи\n"
            f"• 📋 Просматривать свои задачи\n\n"
            f"Выберите действие в меню ниже 👇",
            show_main_menu=True,
        )
    
    # Записываем в лог
    async with AsyncSessionLocal() as db:
        from database import create_request_log, RequestType, RequestStatus
        companies_names = ", ".join([str(cid) for cid in company_ids]) if company_ids else "Без барбершопов"
        await create_request_log(
            db=db,
            partner_id=partner_id,
            request_type=RequestType.VERIFICATION,
            status=RequestStatus.APPROVED,
            request_text=f"Верификация партнёра {partner_name}",
            result_text=f"Привязаны барбершопы: {companies_names}",
        )
    
    logger.info(f"Partner {partner_id} verified with companies: {company_ids}")
    return RedirectResponse(url="/", status_code=302)


@router.post("/partners/{partner_id}/reject")
async def reject_partner(
    request: Request,
    partner_id: int,
    reason: str = Form(""),
):
    """Отклонить заявку партнёра."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionLocal() as db:
        # Получаем имя партнёра для лога
        from sqlalchemy import select
        from database.models import Partner
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner_data = result.scalar_one_or_none()
        partner_name = partner_data.full_name if partner_data else ""
        
        partner = await update_partner_status(
            db=db,
            partner_id=partner_id,
            status=PartnerStatus.REJECTED,
            rejection_reason=reason or "Заявка отклонена администратором",
        )
        
        # Записываем в лог
        from database import create_request_log, RequestType, RequestStatus
        await create_request_log(
            db=db,
            partner_id=partner_id,
            request_type=RequestType.VERIFICATION,
            status=RequestStatus.REJECTED,
            request_text=f"Верификация партнёра {partner_name}",
            result_text=reason or "Причина не указана",
        )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    
    logger.info(f"Partner {partner_id} rejected: {reason}")
    return RedirectResponse(url="/", status_code=302)


@router.get("/partners/{partner_id}/add-barbershop", response_class=HTMLResponse)
async def add_barbershop_to_partner_page(
    request: Request,
    partner_id: int,
):
    """Страница добавления барбершопа к партнёру."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import Partner
    from database import get_all_yclients_companies
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        companies = await get_all_yclients_companies(db, only_active=True)
    
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    
    return templates.TemplateResponse("add_barbershop_to_partner.html", {
        "request": request,
        "partner": partner,
        "companies": companies,
    })


@router.post("/partners/{partner_id}/add-barbershop")
async def add_barbershop_to_partner(
    request: Request,
    partner_id: int,
    company_ids: list[int] = Form(default=[]),
):
    """Добавить барбершоп(ы) к партнёру."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database.crud import link_partner_to_company
    from sqlalchemy import select
    from database.models import Partner
    
    async with AsyncSessionLocal() as db:
        # Получаем партнёра
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner_data = result.scalar_one_or_none()
        
        if not partner_data:
            raise HTTPException(status_code=404, detail="Партнёр не найден")
        
        telegram_id = partner_data.telegram_id
        partner_name = partner_data.full_name
        request_text = partner_data.branches_text or ""
        
        # Привязываем к барбершопам YClients
        for company_id in company_ids:
            await link_partner_to_company(
                db=db,
                partner_id=partner_id,
                company_id=company_id,
                is_owner=True,
            )
        
        # Очищаем флаг и branches_text
        await clear_partner_pending_branch(db, partner_id)
        
        # Записываем в лог
        from database import create_request_log, RequestType, RequestStatus
        companies_str = ", ".join([str(cid) for cid in company_ids])
        await create_request_log(
            db=db,
            partner_id=partner_id,
            request_type=RequestType.ADD_BARBERSHOP,
            status=RequestStatus.APPROVED,
            request_text=request_text,
            result_text=f"Добавлены барбершопы: {companies_str}",
        )
    
    # Отправляем уведомление
    if telegram_id and company_ids:
        await send_telegram_notification(
            telegram_id,
            f"✅ <b>Барбершоп добавлен!</b>\n\n"
            f"Ваш запрос на добавление барбершопа одобрен.\n\n"
            f"Перейдите в раздел «💈 Мои барбершопы» чтобы увидеть обновлённый список.",
            show_main_menu=True,
        )
    
    logger.info(f"Added barbershops {company_ids} to partner {partner_id}")
    return RedirectResponse(url="/", status_code=302)


@router.post("/partners/{partner_id}/reject-barbershop")
async def reject_barbershop_request(
    request: Request,
    partner_id: int,
):
    """Отклонить запрос на добавление барбершопа."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select
    from database.models import Partner
    
    async with AsyncSessionLocal() as db:
        # Получаем партнёра
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner_data = result.scalar_one_or_none()
        
        if not partner_data:
            raise HTTPException(status_code=404, detail="Партнёр не найден")
        
        telegram_id = partner_data.telegram_id
        request_text = partner_data.branches_text or ""
        
        # Записываем в лог
        from database import create_request_log, RequestType, RequestStatus
        await create_request_log(
            db=db,
            partner_id=partner_id,
            request_type=RequestType.ADD_BARBERSHOP,
            status=RequestStatus.REJECTED,
            request_text=request_text,
            result_text="Запрос отклонён",
        )
        
        # Очищаем флаг и branches_text
        await clear_partner_pending_branch(db, partner_id)
    
    # Отправляем уведомление
    if telegram_id:
        await send_telegram_notification(
            telegram_id,
            f"❌ <b>Запрос отклонён</b>\n\n"
            f"Ваш запрос на добавление барбершопа отклонён.\n\n"
            f"Если это ошибка, свяжитесь с вашим менеджером.",
            show_main_menu=True,
        )
    
    logger.info(f"Rejected barbershop request for partner {partner_id}")
    return RedirectResponse(url="/", status_code=302)


@router.get("/partners/{partner_id}/edit", response_class=HTMLResponse)
async def edit_partner_page(request: Request, partner_id: int):
    """Страница редактирования партнёра."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import Partner, YClientsCompany, PartnerCompany
    from sqlalchemy.orm import selectinload
    
    async with AsyncSessionLocal() as db:
        # Получаем партнёра
        result = await db.execute(
            select(Partner)
            .options(selectinload(Partner.companies).selectinload(PartnerCompany.company))
            .where(Partner.id == partner_id)
        )
        partner = result.scalar_one_or_none()
        
        if not partner:
            raise HTTPException(status_code=404, detail="Партнёр не найден")
        
        # Получаем привязанные салоны
        linked_companies = [pc.company for pc in partner.companies if pc.company]
        linked_company_ids = {c.id for c in linked_companies}
        
        # Получаем все активные салоны YClients
        companies_result = await db.execute(
            select(YClientsCompany)
            .where(YClientsCompany.is_active == True)
            .order_by(YClientsCompany.name)
        )
        companies = list(companies_result.scalars().all())
    
    return templates.TemplateResponse("edit_partner.html", {
        "request": request,
        "partner": partner,
        "companies": companies,
        "linked_companies": linked_companies,
        "linked_company_ids": linked_company_ids,
    })


@router.post("/partners/{partner_id}/edit")
async def edit_partner(
    request: Request,
    partner_id: int,
    company_ids: list[int] = Form(default=[]),
):
    """Сохранить изменения привязки партнёра к салонам."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select, delete
    from database.models import Partner, PartnerCompany
    
    async with AsyncSessionLocal() as db:
        # Проверяем, существует ли партнёр
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        
        if not partner:
            raise HTTPException(status_code=404, detail="Партнёр не найден")
        
        # Удаляем старые связи
        await db.execute(
            delete(PartnerCompany).where(PartnerCompany.partner_id == partner_id)
        )
        
        # Создаём новые связи
        for company_id in company_ids:
            link = PartnerCompany(
                partner_id=partner_id,
                company_id=company_id,
                is_owner=True,
            )
            db.add(link)
        
        await db.commit()
    
    logger.info(f"Partner {partner_id} updated with companies: {company_ids}")
    return RedirectResponse(url="/partners?updated=1", status_code=302)


@router.post("/partners/{partner_id}/update-position")
async def update_partner_position(
    request: Request,
    partner_id: int,
    is_owner: str = Form(default=None),
    position: str = Form(default=""),
):
    """Обновить должность партнёра."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select
    from database.models import Partner
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        
        if not partner:
            raise HTTPException(status_code=404, detail="Партнёр не найден")
        
        # Определяем, владелец ли (чекбокс отправляет "1" если выбран)
        partner.is_owner = is_owner == "1"
        
        if partner.is_owner:
            partner.position = "Владелец"
        else:
            partner.position = position.strip() if position.strip() else "Сотрудник"
        
        await db.commit()
    
    logger.info(f"Partner {partner_id} position updated: is_owner={partner.is_owner}, position={partner.position}")
    return RedirectResponse(url=f"/partners/{partner_id}/edit", status_code=302)


@router.post("/partners/{partner_id}/delete")
async def delete_partner(
    request: Request,
    partner_id: int,
):
    """Удалить партнёра."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select, delete
    from database.models import Partner, PartnerBranch, PartnerCompany
    
    async with AsyncSessionLocal() as db:
        # Получаем данные партнёра для уведомления
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        telegram_id = partner.telegram_id if partner else None
        partner_name = partner.full_name if partner else ""
        
        # Удаляем связи с филиалами (старая схема)
        await db.execute(
            delete(PartnerBranch).where(PartnerBranch.partner_id == partner_id)
        )
        
        # Удаляем связи с салонами YClients (новая схема)
        await db.execute(
            delete(PartnerCompany).where(PartnerCompany.partner_id == partner_id)
        )
        
        # Удаляем партнёра
        await db.execute(
            delete(Partner).where(Partner.id == partner_id)
        )
        await db.commit()
    
    # Отправляем уведомление с кнопкой регистрации
    if telegram_id:
        await send_telegram_notification(
            telegram_id,
            f"❌ <b>Ваш аккаунт удалён из системы</b>\n\n"
            f"Если это произошло по ошибке — свяжитесь с вашим менеджером.\n\n"
            f"Для повторной регистрации нажмите кнопку ниже.",
            show_registration=True,
        )
    
    logger.info(f"Partner {partner_id} ({partner_name}) deleted")
    return RedirectResponse(url="/partners", status_code=302)


# ═══════════════════════════════════════════════════════════════════
# Барбершопы YClients (автосинхронизация)
# ═══════════════════════════════════════════════════════════════════

@router.get("/yclients-companies", response_class=HTMLResponse)
async def yclients_companies_page(request: Request, status: str = None, show_closed: str = None):
    """Страница списка салонов YClients с фильтрацией по статусу."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_all_yclients_companies
    from sqlalchemy import select
    from database.models import YClientsCompany
    
    async with AsyncSessionLocal() as db:
        # Получаем все компании для статистики
        all_result = await db.execute(select(YClientsCompany).order_by(YClientsCompany.name))
        all_companies = list(all_result.scalars().all())
        
        # Фильтруем закрытые (содержат "закрыт" в названии)
        # Показываем их только если явно запрошено
        if show_closed != "1":
            all_companies = [c for c in all_companies if "закрыт" not in c.name.lower()]
        
        closed_count = sum(1 for c in all_companies if "закрыт" in c.name.lower()) if show_closed == "1" else 0
        
        # Считаем статистику
        active_count = sum(1 for c in all_companies if c.is_active)
        inactive_count = len(all_companies) - active_count
        
        # Фильтруем по статусу
        if status == "active":
            companies = [c for c in all_companies if c.is_active]
            current_filter = "active"
        elif status == "inactive":
            companies = [c for c in all_companies if not c.is_active]
            current_filter = "inactive"
        else:
            companies = all_companies
            current_filter = "all"
    
    # Группируем по городам для статистики (только активные)
    cities = {}
    for c in all_companies:
        if c.is_active:
            city = c.city or "Неизвестно"
            if city not in cities:
                cities[city] = 0
            cities[city] += 1
    
    return templates.TemplateResponse("yclients_companies.html", {
        "request": request,
        "companies": companies,
        "total_count": len(all_companies),
        "active_count": active_count,
        "inactive_count": inactive_count,
        "closed_count": closed_count,
        "cities_count": len(cities),
        "cities": sorted(cities.items(), key=lambda x: x[1], reverse=True),
        "current_filter": current_filter,
        "show_closed": show_closed == "1",
    })


@router.post("/yclients-companies/sync")
async def sync_yclients_companies_route(request: Request):
    """Синхронизировать список салонов из YClients API."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from yclients import sync_companies_to_db
    
    # Запускаем синхронизацию
    added, updated = await sync_companies_to_db()
    
    logger.info(f"YClients companies sync: {added} added, {updated} updated")
    
    return RedirectResponse(url="/yclients-companies?synced=1", status_code=302)


@router.get("/yclients-companies/{company_id}/edit", response_class=HTMLResponse)
async def edit_yclients_company_page(request: Request, company_id: int):
    """Страница редактирования салона YClients."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import YClientsCompany
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(YClientsCompany).where(YClientsCompany.id == company_id)
        )
        company = result.scalar()
    
    if not company:
        raise HTTPException(status_code=404, detail="Салон не найден")
    
    return templates.TemplateResponse("edit_yclients_company.html", {
        "request": request,
        "company": company,
    })


@router.post("/yclients-companies/{company_id}/edit")
async def edit_yclients_company(
    request: Request,
    company_id: int,
    is_active: int = Form(...),
):
    """Сохранить изменения салона YClients."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select
    from database.models import YClientsCompany
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(YClientsCompany).where(YClientsCompany.id == company_id)
        )
        company = result.scalar()
        
        if not company:
            raise HTTPException(status_code=404, detail="Салон не найден")
        
        # Обновляем статус
        company.is_active = bool(is_active)
        await db.commit()
        
        logger.info(f"Company {company_id} ({company.name}) updated: is_active={company.is_active}")
    
    return RedirectResponse(url="/yclients-companies?updated=1", status_code=302)


# ═══════════════════════════════════════════════════════════════════
# Рассылка сообщений
# ═══════════════════════════════════════════════════════════════════

@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    """Страница рассылки сообщений."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import BroadcastHistory
    
    async with AsyncSessionLocal() as db:
        verified_partners = await get_all_partners(db, status=PartnerStatus.VERIFIED)
        all_partners = await get_all_partners(db)
        
        # История рассылок (последние 20)
        result = await db.execute(
            select(BroadcastHistory)
            .order_by(BroadcastHistory.sent_at.desc())
            .limit(20)
        )
        history = list(result.scalars().all())
    
    return templates.TemplateResponse("broadcast.html", {
        "request": request,
        "verified_partners": verified_partners,
        "all_partners": all_partners,
        "verified_count": len(verified_partners),
        "all_count": len(all_partners),
        "history": history,
    })


@router.post("/broadcast/send")
async def send_broadcast(
    request: Request,
    message: str = Form(...),
    recipient_type: str = Form("all_verified"),  # all_verified, selected
    partner_ids: list[int] = Form(default=[]),
):
    """Отправить рассылку."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not message.strip():
        return RedirectResponse(url="/broadcast?error=empty", status_code=302)
    
    from sqlalchemy import select
    from database.models import BroadcastHistory
    
    # Получаем партнёров
    async with AsyncSessionLocal() as db:
        if recipient_type == "selected" and partner_ids:
            # Выбранные партнёры
            all_partners = await get_all_partners(db)
            partners = [p for p in all_partners if p.id in partner_ids]
            recipients_text = ", ".join([p.full_name for p in partners])
        else:
            # Все верифицированные
            partners = await get_all_partners(db, status=PartnerStatus.VERIFIED)
            recipients_text = "Все верифицированные партнёры"
        
        if not partners:
            return RedirectResponse(url="/broadcast?error=no_recipients", status_code=302)
        
        # Отправляем сообщения
        success_count = 0
        fail_count = 0
        
        for partner in partners:
            if partner.telegram_id:
                result = await send_telegram_notification(
                    partner.telegram_id,
                    message,
                    show_main_menu=True if partner.status == PartnerStatus.VERIFIED else False,
                )
                if result:
                    success_count += 1
                else:
                    fail_count += 1
        
        # Сохраняем в историю
        broadcast = BroadcastHistory(
            message=message[:500],  # Ограничиваем длину для БД
            recipients=recipients_text[:500],
            recipients_count=len(partners),
            success_count=success_count,
            fail_count=fail_count,
            sent_by="admin",
        )
        db.add(broadcast)
        await db.commit()
    
    logger.info(f"Broadcast sent: {success_count} success, {fail_count} failed")
    
    return RedirectResponse(
        url=f"/broadcast?success={success_count}&failed={fail_count}", 
        status_code=302
    )


# ═══════════════════════════════════════════════════════════════════
# Network Rating
# ═══════════════════════════════════════════════════════════════════

@router.get("/network-rating", response_class=HTMLResponse)
async def network_rating_page(request: Request, period: str = "current"):
    """Страница рейтинга сети с переключателем периода."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_all_network_ratings, get_rating_history
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    today = datetime.now(ZoneInfo("Europe/Moscow"))
    
    # Определяем названия месяцев
    month_names = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель",
        5: "май", 6: "июнь", 7: "июль", 8: "август",
        9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
    }
    
    # Вспомогательная функция для получения предыдущего месяца
    def get_prev_month(year, month):
        if month == 1:
            return year - 1, 12
        return year, month - 1
    
    if period == "previous":
        # Прошлый полный месяц (октябрь)
        prev_year, prev_month = get_prev_month(today.year, today.month)
        
        # Позапрошлый месяц для сравнения (сентябрь)
        prev_prev_year, prev_prev_month = get_prev_month(prev_year, prev_month)
        
        async with AsyncSessionLocal() as db:
            # Данные за прошлый месяц (октябрь)
            history_ratings = await get_rating_history(db, prev_year, prev_month)
            
            # Данные за позапрошлый месяц (сентябрь) для сравнения
            prev_prev_ratings = await get_rating_history(db, prev_prev_year, prev_prev_month)
        
        # Создаём словарь рангов за позапрошлый месяц
        prev_ranks = {r.yclients_company_id: r.rank for r in prev_prev_ratings}
        
        # Добавляем previous_rank к каждому рейтингу
        ratings_with_change = []
        for r in history_ratings:
            # Пропускаем закрытые и с нулевой выручкой
            if r.revenue > 0 and "закрыт" not in r.company_name.lower():
                # Создаём объект с дополнительным полем
                r.previous_rank = prev_ranks.get(r.yclients_company_id, 0)
                ratings_with_change.append(r)
        
        ratings = ratings_with_change
        period_name = f"{month_names[prev_month]} {prev_year}"
        compare_period = f"vs {month_names[prev_prev_month]}"
        last_update = ratings[0].created_at if ratings else None
    else:
        # Текущий месяц (ноябрь - неполный)
        # Прошлый месяц для сравнения (октябрь)
        prev_year, prev_month = get_prev_month(today.year, today.month)
        
        async with AsyncSessionLocal() as db:
            # Текущие данные
            all_ratings = await get_all_network_ratings(db)
            
            # Данные за прошлый месяц для сравнения
            prev_ratings = await get_rating_history(db, prev_year, prev_month)
        
        # Создаём словарь рангов за прошлый месяц
        prev_ranks = {r.yclients_company_id: r.rank for r in prev_ratings}
        
        # Добавляем previous_rank к каждому рейтингу
        ratings_with_change = []
        for r in all_ratings:
            # Пропускаем закрытые и с нулевой выручкой
            if r.revenue > 0 and "закрыт" not in r.company_name.lower():
                r.previous_rank = prev_ranks.get(r.yclients_company_id, 0)
                ratings_with_change.append(r)
        
        ratings = ratings_with_change
        period_name = f"{month_names[today.month]} {today.year}"
        compare_period = f"vs {month_names[prev_month]}"
        last_update = ratings[0].updated_at if ratings else None
    
    # Статистика
    total_companies = len(ratings)
    total_revenue = sum(r.revenue for r in ratings) if ratings else 0
    avg_revenue = total_revenue / total_companies if total_companies > 0 else 0
    
    return templates.TemplateResponse(
        "network_rating.html",
        {
            "request": request,
            "ratings": ratings,
            "total_companies": total_companies,
            "total_revenue": total_revenue,
            "avg_revenue": avg_revenue,
            "last_update": last_update,
            "period": period,
            "period_name": period_name,
            "compare_period": compare_period,
        },
    )


@router.get("/network-rating/refresh")
async def network_rating_refresh(request: Request):
    """Принудительное обновление рейтинга."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from scheduler import update_network_rating_now
    import asyncio
    
    # Запускаем обновление в фоне
    asyncio.create_task(update_network_rating_now())
    
    logger.info("Manual network rating refresh triggered from admin panel")
    
    # Редиректим обратно с сообщением
    return RedirectResponse(url="/network-rating?refresh=started", status_code=302)


# ═══════════════════════════════════════════════════════════════════
# Geography Analytics
# ═══════════════════════════════════════════════════════════════════

@router.get("/geography", response_class=HTMLResponse)
async def geography_page(request: Request):
    """Страница географической аналитики сети с использованием yclients_companies."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import NetworkRating, YClientsCompany
    from collections import defaultdict
    
    async with AsyncSessionLocal() as db:
        # Получаем все рейтинги
        ratings_result = await db.execute(
            select(NetworkRating).where(NetworkRating.revenue > 0)
        )
        ratings = list(ratings_result.scalars().all())
        
        # Получаем данные о компаниях из yclients_companies (где город уже распарсен)
        companies_result = await db.execute(select(YClientsCompany))
        companies = {c.yclients_id: c for c in companies_result.scalars().all()}
    
    # Собираем географию, используя данные из yclients_companies
    geo = {
        "total_salons": len(ratings),
        "millionniki_count": 0,
        "millionniki_revenue": 0,
        "other_count": 0,
        "other_revenue": 0,
        "millionniki_percent": 0,
        "other_percent": 0,
        "millionniki": [],
        "regions": [],
        "unknown_cities": [],
    }
    
    by_city = defaultdict(lambda: {"count": 0, "revenue": 0, "avg_check": 0, "salons": []})
    by_region = defaultdict(lambda: {"count": 0, "revenue": 0, "salons": []})
    
    for r in ratings:
        # Пропускаем закрытые барбершопы
        if "закрыт" in r.company_name.lower():
            geo["total_salons"] -= 1
            continue
            
        company = companies.get(r.yclients_company_id)
        
        salon_info = {
            "name": r.company_name,
            "revenue": r.revenue or 0,
            "avg_check": r.avg_check or 0,
            "rank": r.rank,
        }
        
        if company and company.city:
            city = company.city
            region = company.region or "Не определено"
            is_million = company.is_million_city
            
            # По городам
            by_city[city]["count"] += 1
            by_city[city]["revenue"] += r.revenue or 0
            by_city[city]["salons"].append(salon_info)
            if r.avg_check:
                current_count = by_city[city]["count"]
                current_avg = by_city[city]["avg_check"]
                by_city[city]["avg_check"] = (current_avg * (current_count - 1) + r.avg_check) / current_count
            
            # Миллионники vs остальные
            if is_million:
                geo["millionniki_count"] += 1
                geo["millionniki_revenue"] += r.revenue or 0
            else:
                geo["other_count"] += 1
                geo["other_revenue"] += r.revenue or 0
                # Только НЕ-миллионники идут в регионы
                by_region[region]["count"] += 1
                by_region[region]["revenue"] += r.revenue or 0
                by_region[region]["salons"].append(salon_info)
        else:
            # Город не определён - используем старый метод парсинга
            from .analytics import extract_city_from_name, is_millionnik, get_region
            city = extract_city_from_name(r.company_name)
            
            if city:
                by_city[city]["count"] += 1
                by_city[city]["revenue"] += r.revenue or 0
                by_city[city]["salons"].append(salon_info)
                
                if is_millionnik(city):
                    geo["millionniki_count"] += 1
                    geo["millionniki_revenue"] += r.revenue or 0
                else:
                    geo["other_count"] += 1
                    geo["other_revenue"] += r.revenue or 0
                    region = get_region(city)
                    by_region[region]["count"] += 1
                    by_region[region]["revenue"] += r.revenue or 0
                    by_region[region]["salons"].append(salon_info)
            else:
                geo["unknown_cities"].append(r.company_name)
                geo["other_count"] += 1
                geo["other_revenue"] += r.revenue or 0
    
    # Проценты
    total = geo["total_salons"]
    if total > 0:
        geo["millionniki_percent"] = round(geo["millionniki_count"] / total * 100, 1)
        geo["other_percent"] = round(geo["other_count"] / total * 100, 1)
    
    # Формируем список миллионников
    millionnik_cities = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", 
                        "Казань", "Нижний Новгород", "Красноярск", "Челябинск",
                        "Самара", "Уфа", "Ростов-на-Дону", "Омск", "Краснодар",
                        "Воронеж", "Пермь", "Волгоград"]
    
    for city in millionnik_cities:
        if city in by_city:
            data = by_city[city]
            geo["millionniki"].append({
                "name": city,
                "count": data["count"],
                "revenue": data["revenue"],
                "avg_check": data["avg_check"],
                "salons": sorted(data["salons"], key=lambda x: x["revenue"], reverse=True),
            })
    
    geo["millionniki"] = sorted(geo["millionniki"], key=lambda x: x["count"], reverse=True)
    
    # Формируем список регионов
    for region, data in by_region.items():
        if region != "Не определено":
            geo["regions"].append({
                "name": region,
                "count": data["count"],
                "revenue": data["revenue"],
                "salons": sorted(data["salons"], key=lambda x: x["revenue"], reverse=True),
            })
    
    geo["regions"] = sorted(geo["regions"], key=lambda x: x["count"], reverse=True)
    
    # Добавляем "Не определено" отдельно
    if "Не определено" in by_region:
        geo["undefined_region"] = {
            "count": by_region["Не определено"]["count"],
            "revenue": by_region["Не определено"]["revenue"],
            "salons": sorted(by_region["Не определено"]["salons"], key=lambda x: x["revenue"], reverse=True),
        }
    
    # Добавляем by_city для подсчёта городов присутствия
    geo["by_city"] = dict(by_city)
    
    return templates.TemplateResponse(
        "geography.html",
        {
            "request": request,
            "geo": geo,
        },
    )


# ═══════════════════════════════════════════════════════════════════
# Лог заявок
# ═══════════════════════════════════════════════════════════════════

@router.get("/request-logs", response_class=HTMLResponse)
async def request_logs_page(request: Request):
    """Страница с логом всех заявок."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_request_logs, RequestType, RequestStatus
    
    async with AsyncSessionLocal() as db:
        logs = await get_request_logs(db, limit=100)
    
    return templates.TemplateResponse(
        "request_logs.html",
        {
            "request": request,
            "logs": logs,
            "RequestType": RequestType,
            "RequestStatus": RequestStatus,
        },
    )


# ═══════════════════════════════════════════════════════════════════
# Голосования
# ═══════════════════════════════════════════════════════════════════

@router.get("/polls", response_class=HTMLResponse)
async def polls_list(request: Request):
    """Список всех голосований."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_all_polls, PollStatus
    
    async with AsyncSessionLocal() as db:
        polls = await get_all_polls(db)
    
    return templates.TemplateResponse(
        "polls.html",
        {
            "request": request,
            "polls": polls,
            "PollStatus": PollStatus,
        },
    )


@router.get("/polls/create", response_class=HTMLResponse)
async def create_poll_page(request: Request):
    """Страница создания голосования."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "poll_create.html",
        {"request": request},
    )


@router.post("/polls/create")
async def create_poll_action(
    request: Request,
    question: str = Form(...),
    options: str = Form(...),  # Варианты через перевод строки
    allows_multiple: str = Form("0"),
):
    """Создать голосование."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import create_poll
    
    # Парсим варианты
    options_list = [opt.strip() for opt in options.split("\n") if opt.strip()]
    
    if len(options_list) < 2:
        raise HTTPException(status_code=400, detail="Минимум 2 варианта ответа")
    
    if len(options_list) > 10:
        raise HTTPException(status_code=400, detail="Максимум 10 вариантов ответа")
    
    async with AsyncSessionLocal() as db:
        poll = await create_poll(
            db,
            question=question,
            options=options_list,
            is_anonymous=False,  # Всегда не анонимное для получения ответов
            allows_multiple=allows_multiple == "1",
        )
    
    logger.info(f"Poll created: {poll.id}")
    return RedirectResponse(url="/polls", status_code=302)


@router.get("/polls/{poll_id}", response_class=HTMLResponse)
async def poll_details(request: Request, poll_id: int):
    """Детали и результаты голосования."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_poll_by_id, get_poll_results, PollStatus
    
    async with AsyncSessionLocal() as db:
        poll = await get_poll_by_id(db, poll_id)
        
        if not poll:
            raise HTTPException(status_code=404, detail="Голосование не найдено")
        
        results = await get_poll_results(db, poll_id)
    
    return templates.TemplateResponse(
        "poll_details.html",
        {
            "request": request,
            "poll": poll,
            "results": results,
            "PollStatus": PollStatus,
        },
    )


@router.post("/polls/{poll_id}/send")
async def send_poll(request: Request, poll_id: int):
    """Отправить голосование всем верифицированным партнёрам."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import (
        get_poll_by_id, 
        update_poll_status, 
        save_poll_message,
        PollStatus,
    )
    
    async with AsyncSessionLocal() as db:
        poll = await get_poll_by_id(db, poll_id)
        
        if not poll:
            raise HTTPException(status_code=404, detail="Голосование не найдено")
        
        if poll.status != PollStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Можно отправить только черновик")
        
        # Получаем верифицированных партнёров
        partners = await get_all_partners(db, status=PartnerStatus.VERIFIED)
        
        if not partners:
            raise HTTPException(status_code=400, detail="Нет верифицированных партнёров")
        
        # Подготавливаем варианты ответов
        options = [opt.text for opt in poll.options]
        
        # Отправляем каждому партнёру
        success_count = 0
        fail_count = 0
        
        async with httpx.AsyncClient() as client:
            for partner in partners:
                try:
                    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
                    
                    payload = {
                        "chat_id": partner.telegram_id,
                        "question": poll.question,
                        "options": options,
                        "is_anonymous": poll.is_anonymous,
                        "allows_multiple_answers": poll.allows_multiple,
                    }
                    
                    response = await client.post(url, json=payload, timeout=10)
                    result = response.json()
                    
                    if result.get("ok"):
                        # Сохраняем информацию о сообщении
                        msg_data = result["result"]
                        await save_poll_message(
                            db,
                            poll_id=poll.id,
                            partner_id=partner.id,
                            telegram_chat_id=msg_data["chat"]["id"],
                            telegram_message_id=msg_data["message_id"],
                            telegram_poll_id=msg_data["poll"]["id"],
                        )
                        success_count += 1
                    else:
                        logger.error(f"Failed to send poll to {partner.telegram_id}: {result}")
                        fail_count += 1
                        
                except Exception as e:
                    logger.error(f"Error sending poll to {partner.telegram_id}: {e}")
                    fail_count += 1
        
        # Обновляем статус голосования
        await update_poll_status(db, poll_id, PollStatus.SENT)
    
    logger.info(f"Poll {poll_id} sent: {success_count} success, {fail_count} failed")
    return RedirectResponse(url=f"/polls/{poll_id}", status_code=302)


@router.post("/polls/{poll_id}/close")
async def close_poll(request: Request, poll_id: int):
    """Закрыть голосование (остановить опросы в Telegram)."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import (
        get_poll_by_id, 
        update_poll_status, 
        get_poll_messages,
        mark_poll_message_stopped,
        PollStatus,
    )
    
    async with AsyncSessionLocal() as db:
        poll = await get_poll_by_id(db, poll_id)
        
        if not poll:
            raise HTTPException(status_code=404, detail="Голосование не найдено")
        
        if poll.status != PollStatus.SENT:
            raise HTTPException(status_code=400, detail="Можно закрыть только отправленное голосование")
        
        # Получаем все сообщения с опросами
        messages = await get_poll_messages(db, poll_id)
        
        stopped_count = 0
        
        async with httpx.AsyncClient() as client:
            for msg in messages:
                try:
                    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/stopPoll"
                    
                    payload = {
                        "chat_id": msg.telegram_chat_id,
                        "message_id": msg.telegram_message_id,
                    }
                    
                    response = await client.post(url, json=payload, timeout=10)
                    result = response.json()
                    
                    if result.get("ok"):
                        await mark_poll_message_stopped(db, msg.id)
                        stopped_count += 1
                    else:
                        logger.warning(f"Failed to stop poll message {msg.id}: {result}")
                        
                except Exception as e:
                    logger.error(f"Error stopping poll message {msg.id}: {e}")
        
        # Обновляем статус голосования
        await update_poll_status(db, poll_id, PollStatus.CLOSED)
    
    logger.info(f"Poll {poll_id} closed: {stopped_count} polls stopped")
    return RedirectResponse(url=f"/polls/{poll_id}", status_code=302)


@router.post("/polls/{poll_id}/delete")
async def delete_poll_action(request: Request, poll_id: int):
    """Удалить голосование (любое)."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import get_poll_by_id
    from database.models import Poll
    from sqlalchemy import delete
    
    async with AsyncSessionLocal() as db:
        poll = await get_poll_by_id(db, poll_id)
        
        if not poll:
            raise HTTPException(status_code=404, detail="Голосование не найдено")
        
        # Удаляем голосование (каскадно удалятся options, responses, messages)
        await db.delete(poll)
        await db.commit()
    
    logger.info(f"Poll {poll_id} deleted")
    return RedirectResponse(url="/polls", status_code=302)


# ═══════════════════════════════════════════════════════════════════
# Полезное (тексты для отделов)
# ═══════════════════════════════════════════════════════════════════

@router.get("/useful-info", response_class=HTMLResponse)
async def useful_info_page(request: Request):
    """Редирект на страницу кнопок (основной функционал)."""
    return RedirectResponse(url="/useful-info/buttons", status_code=302)


# Старые роуты /useful-info/{department}/{info_type}/edit удалены
# Теперь всё управляется через /useful-info/buttons


# ═══════════════════════════════════════════════════════════════════
# Кнопки отделов (для раздела "Полезное")
# ═══════════════════════════════════════════════════════════════════

@router.get("/useful-info/buttons", response_class=HTMLResponse)
async def department_buttons_page(request: Request, department: str = None):
    """Страница управления кнопками отделов."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_all_department_buttons, init_default_department_buttons, DepartmentType
    
    async with AsyncSessionLocal() as db:
        # Инициализируем дефолтные кнопки если их нет
        await init_default_department_buttons(db)
        all_buttons = await get_all_department_buttons(db)
    
    # Группируем по отделам
    grouped = {}
    for dept in DepartmentType:
        grouped[dept] = [b for b in all_buttons if b.department == dept]
    
    return templates.TemplateResponse(
        "department_buttons.html",
        {
            "request": request,
            "grouped": grouped,
            "DepartmentType": DepartmentType,
            "current_department": department,
        },
    )


@router.get("/useful-info/buttons/create", response_class=HTMLResponse)
async def create_button_page(request: Request, department: str = None):
    """Страница создания кнопки."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import DepartmentType
    
    return templates.TemplateResponse(
        "edit_department_button.html",
        {
            "request": request,
            "button": None,
            "DepartmentType": DepartmentType,
            "selected_department": department,
            "is_new": True,
        },
    )


@router.post("/useful-info/buttons/create")
async def create_button(
    request: Request,
    department: str = Form(...),
    button_text: str = Form(...),
    message_text: str = Form(...),
    order: int = Form(0),
):
    """Создать новую кнопку."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import create_department_button, DepartmentType
    
    try:
        dept = DepartmentType(department)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный отдел")
    
    async with AsyncSessionLocal() as db:
        await create_department_button(db, dept, button_text, message_text, order)
    
    logger.info(f"Created department button: {department} - {button_text}")
    return RedirectResponse(url="/useful-info/buttons", status_code=302)


@router.get("/useful-info/buttons/{button_id}/edit", response_class=HTMLResponse)
async def edit_button_page(request: Request, button_id: int):
    """Страница редактирования кнопки."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_department_button_by_id, DepartmentType
    
    async with AsyncSessionLocal() as db:
        button = await get_department_button_by_id(db, button_id)
    
    if not button:
        raise HTTPException(status_code=404, detail="Кнопка не найдена")
    
    return templates.TemplateResponse(
        "edit_department_button.html",
        {
            "request": request,
            "button": button,
            "DepartmentType": DepartmentType,
            "selected_department": button.department.value,
            "is_new": False,
        },
    )


@router.post("/useful-info/buttons/{button_id}/edit")
async def save_button(
    request: Request,
    button_id: int,
    department: str = Form(...),
    button_text: str = Form(...),
    message_text: str = Form(...),
    order: int = Form(0),
    is_active: bool = Form(True),
):
    """Сохранить изменения кнопки."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import update_department_button, get_department_button_by_id, DepartmentType
    
    async with AsyncSessionLocal() as db:
        button = await get_department_button_by_id(db, button_id)
        if not button:
            raise HTTPException(status_code=404, detail="Кнопка не найдена")
        
        # Обновляем все поля
        try:
            dept = DepartmentType(department)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный отдел")
        
        button.department = dept
        button.button_text = button_text
        button.message_text = message_text
        button.order = order
        button.is_active = is_active
        
        await db.commit()
    
    logger.info(f"Updated department button {button_id}: {button_text}")
    return RedirectResponse(url="/useful-info/buttons", status_code=302)


@router.post("/useful-info/buttons/{button_id}/delete")
async def delete_button(request: Request, button_id: int):
    """Удалить кнопку."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import delete_department_button
    
    async with AsyncSessionLocal() as db:
        await delete_department_button(db, button_id)
    
    logger.info(f"Deleted department button {button_id}")
    return RedirectResponse(url="/useful-info/buttons", status_code=302)


@router.post("/useful-info/buttons/{button_id}/toggle")
async def toggle_button(request: Request, button_id: int):
    """Включить/выключить кнопку."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import get_department_button_by_id
    
    async with AsyncSessionLocal() as db:
        button = await get_department_button_by_id(db, button_id)
        if button:
            button.is_active = not button.is_active
            await db.commit()
            logger.info(f"Toggled button {button_id}: active={button.is_active}")
    
    return RedirectResponse(url="/useful-info/buttons", status_code=302)


# ═══════════════════════════════════════════════════════════════════
# Диагностика системы
# ═══════════════════════════════════════════════════════════════════

@router.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(request: Request):
    """Страница диагностики системы."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("diagnostics.html", {"request": request})


@router.get("/diagnostics/run", response_class=JSONResponse)
async def run_diagnostics(request: Request):
    """Запуск диагностики всех компонентов."""
    if not verify_session(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    from datetime import datetime
    import httpx
    from config.settings import (
        DATABASE_URL, 
        TELEGRAM_BOT_TOKEN, 
        BITRIX_WEBHOOK_URL,
        YCLIENTS_PARTNER_TOKEN,
        YCLIENTS_USER_TOKEN,
        REDIS_URL,
    )
    
    checks = {}
    
    # 1. PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            checks["database"] = {
                "name": "PostgreSQL",
                "status": "ok",
                "message": "Подключено",
                "details": version.split(",")[0] if version else None,
            }
    except Exception as e:
        checks["database"] = {
            "name": "PostgreSQL",
            "status": "error",
            "message": f"Ошибка: {str(e)[:50]}",
        }
    
    # 2. Redis
    try:
        from cache import init_cache, is_cache_available, close_cache
        if REDIS_URL:
            # Пробуем подключиться
            import redis.asyncio as redis_client
            r = redis_client.from_url(REDIS_URL, socket_connect_timeout=3)
            await r.ping()
            await r.close()
            checks["redis"] = {
                "name": "Redis",
                "status": "ok",
                "message": "Подключено",
                "details": REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL,
            }
        else:
            checks["redis"] = {
                "name": "Redis",
                "status": "warning",
                "message": "Не настроен",
                "details": "REDIS_URL не задан в .env",
            }
    except Exception as e:
        checks["redis"] = {
            "name": "Redis",
            "status": "warning",
            "message": "Недоступен",
            "details": str(e)[:50],
        }
    
    # 3. Telegram Bot
    try:
        if TELEGRAM_BOT_TOKEN:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        checks["telegram"] = {
                            "name": "Telegram Bot",
                            "status": "ok",
                            "message": f"@{bot_info.get('username', 'bot')}",
                            "details": f"ID: {bot_info.get('id')}",
                        }
                    else:
                        checks["telegram"] = {
                            "name": "Telegram Bot",
                            "status": "error",
                            "message": "Неверный токен",
                        }
                else:
                    checks["telegram"] = {
                        "name": "Telegram Bot",
                        "status": "error",
                        "message": f"HTTP {resp.status_code}",
                    }
        else:
            checks["telegram"] = {
                "name": "Telegram Bot",
                "status": "error",
                "message": "Токен не задан",
            }
    except Exception as e:
        checks["telegram"] = {
            "name": "Telegram Bot",
            "status": "error",
            "message": str(e)[:50],
        }
    
    # 4. YClients API
    try:
        if YCLIENTS_PARTNER_TOKEN:
            async with httpx.AsyncClient(timeout=10) as client:
                # YClients требует Bearer + User Token
                if YCLIENTS_USER_TOKEN:
                    auth_header = f"Bearer {YCLIENTS_PARTNER_TOKEN}, User {YCLIENTS_USER_TOKEN}"
                else:
                    auth_header = f"Bearer {YCLIENTS_PARTNER_TOKEN}"
                
                headers = {
                    "Authorization": auth_header,
                    "Accept": "application/vnd.api.v2+json",
                }
                resp = await client.get(
                    "https://api.yclients.com/api/v1/groups",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        groups = data.get("data", [])
                        company_count = sum(len(g.get("companies", [])) for g in groups)
                        checks["yclients"] = {
                            "name": "YClients API",
                            "status": "ok",
                            "message": "Подключено",
                            "details": f"{company_count} салонов в сети",
                        }
                    else:
                        checks["yclients"] = {
                            "name": "YClients API",
                            "status": "error",
                            "message": "API вернул ошибку",
                        }
                else:
                    checks["yclients"] = {
                        "name": "YClients API",
                        "status": "error",
                        "message": f"HTTP {resp.status_code}",
                    }
        else:
            checks["yclients"] = {
                "name": "YClients API",
                "status": "error",
                "message": "Токен не задан",
            }
    except Exception as e:
        checks["yclients"] = {
            "name": "YClients API",
            "status": "error",
            "message": str(e)[:50],
        }
    
    # 5. Bitrix24 API
    try:
        if BITRIX_WEBHOOK_URL:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BITRIX_WEBHOOK_URL.rstrip('/')}/profile"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "result" in data:
                        user = data.get("result", {})
                        checks["bitrix"] = {
                            "name": "Bitrix24 API",
                            "status": "ok",
                            "message": "Подключено",
                            "details": f"{user.get('NAME', '')} {user.get('LAST_NAME', '')}".strip() or "Webhook OK",
                        }
                    else:
                        checks["bitrix"] = {
                            "name": "Bitrix24 API",
                            "status": "error",
                            "message": data.get("error_description", "Ошибка"),
                        }
                else:
                    checks["bitrix"] = {
                        "name": "Bitrix24 API",
                        "status": "error",
                        "message": f"HTTP {resp.status_code}",
                    }
        else:
            checks["bitrix"] = {
                "name": "Bitrix24 API",
                "status": "warning",
                "message": "Не настроен",
                "details": "BITRIX_WEBHOOK_URL не задан",
            }
    except Exception as e:
        checks["bitrix"] = {
            "name": "Bitrix24 API",
            "status": "error",
            "message": str(e)[:50],
        }
    
    # 6. Scheduler
    try:
        from database import get_last_network_rating_update
        async with AsyncSessionLocal() as db:
            last_update = await get_last_network_rating_update(db)
        
        if last_update:
            # Приводим к naive datetime для сравнения
            now = datetime.now()
            if last_update.tzinfo is not None:
                last_update = last_update.replace(tzinfo=None)
            
            age = now - last_update
            hours_ago = age.total_seconds() / 3600
            
            if hours_ago < 25:  # Меньше суток + 1 час запаса
                checks["scheduler"] = {
                    "name": "Планировщик",
                    "status": "ok",
                    "message": "Работает",
                    "details": f"Обновлено {hours_ago:.1f}ч назад",
                }
            else:
                checks["scheduler"] = {
                    "name": "Планировщик",
                    "status": "warning",
                    "message": "Давно не обновлялось",
                    "details": f"Последнее обновление: {last_update.strftime('%d.%m %H:%M')}",
                }
        else:
            checks["scheduler"] = {
                "name": "Планировщик",
                "status": "warning",
                "message": "Нет данных",
                "details": "Рейтинг ещё не загружен",
            }
    except Exception as e:
        checks["scheduler"] = {
            "name": "Планировщик",
            "status": "error",
            "message": str(e)[:50],
        }
    
    return JSONResponse({
        "checks": checks,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    })


# ═══════════════════════════════════════════════════════════════════
# Настройки бота (Bot Settings)
# ═══════════════════════════════════════════════════════════════════

@router.get("/bot-settings", response_class=HTMLResponse)
async def bot_settings_page(request: Request):
    """Страница настроек бота."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_all_bot_settings, init_default_bot_settings
    
    async with AsyncSessionLocal() as db:
        await init_default_bot_settings(db)
        settings = await get_all_bot_settings(db)
    
    return templates.TemplateResponse(
        "bot_settings.html",
        {
            "request": request,
            "settings": settings,
        },
    )


@router.get("/bot-settings/{key}/edit", response_class=HTMLResponse)
async def edit_bot_setting_page(request: Request, key: str):
    """Страница редактирования настройки."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from database import get_bot_setting, init_default_bot_settings, BotSetting
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        await init_default_bot_settings(db)
        result = await db.execute(
            select(BotSetting).where(BotSetting.key == key)
        )
        setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    
    return templates.TemplateResponse(
        "edit_bot_setting.html",
        {
            "request": request,
            "setting": setting,
        },
    )


@router.post("/bot-settings/{key}/edit")
async def save_bot_setting(
    request: Request,
    key: str,
    value: str = Form(...),
):
    """Сохранить настройку."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database import set_bot_setting
    
    async with AsyncSessionLocal() as db:
        await set_bot_setting(db, key, value)
    
    logger.info(f"Updated bot setting: {key}")
    return RedirectResponse(url="/bot-settings", status_code=302)
