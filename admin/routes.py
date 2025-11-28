# Admin panel routes

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config.settings import BASE_DIR, ADMIN_USERNAME, ADMIN_PASSWORD, TELEGRAM_BOT_TOKEN
from database import (
    AsyncSessionLocal,
    get_all_partners,
    get_pending_partners,
    update_partner_status,
    get_all_branches,
    PartnerStatus,
    Partner,
    get_partners_with_pending_branches,
    clear_partner_pending_branch,
)
from .auth import verify_session, create_session

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
                [{"text": "📋 Задачи"}, {"text": "🏢 Мои филиалы"}]
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
    """Обработка входа."""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = create_session(username)
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            max_age=86400,  # 24 часа
        )
        return response
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Неверный логин или пароль",
    })


@router.get("/logout")
async def logout(request: Request):
    """Выход."""
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
                yclients_company_id=company_id,
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
                yclients_company_id=company_id,
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
# Филиалы
# ═══════════════════════════════════════════════════════════════════

@router.get("/branches", response_class=HTMLResponse)
async def branches_list(request: Request):
    """Список филиалов."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    async with AsyncSessionLocal() as db:
        branches = await get_all_branches(db, only_active=False)
    
    return templates.TemplateResponse("branches.html", {
        "request": request,
        "branches": branches,
    })


@router.post("/branches/add")
async def add_branch(
    request: Request,
    yclients_id: str = Form(...),
    city: str = Form(...),
    address: str = Form(...),
    name: str = Form(""),
    display_name: str = Form(""),
):
    """Добавить филиал."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database.models import Branch
    
    async with AsyncSessionLocal() as db:
        branch = Branch(
            yclients_id=yclients_id,
            city=city,
            address=address,
            name=name or None,
            display_name=display_name or None,
        )
        db.add(branch)
        await db.commit()
    
    logger.info(f"Branch added: {city}, {address}")
    return RedirectResponse(url="/branches", status_code=302)


@router.get("/branches/{branch_id}/edit", response_class=HTMLResponse)
async def edit_branch_page(
    request: Request,
    branch_id: int,
):
    """Страница редактирования филиала."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import Branch
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = result.scalar_one_or_none()
    
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")
    
    return templates.TemplateResponse("edit_branch.html", {
        "request": request,
        "branch": branch,
    })


@router.post("/branches/{branch_id}/edit")
async def edit_branch(
    request: Request,
    branch_id: int,
    yclients_id: str = Form(...),
    city: str = Form(...),
    address: str = Form(...),
    name: str = Form(""),
    display_name: str = Form(""),
    is_active: str = Form("1"),
):
    """Сохранить изменения филиала."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select
    from database.models import Branch
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch = result.scalar_one_or_none()
        
        if not branch:
            raise HTTPException(status_code=404, detail="Филиал не найден")
        
        branch.yclients_id = yclients_id
        branch.city = city
        branch.address = address
        branch.name = name or None
        branch.display_name = display_name or None
        branch.is_active = is_active == "1"
        
        await db.commit()
    
    logger.info(f"Branch {branch_id} updated")
    return RedirectResponse(url="/branches", status_code=302)


@router.post("/branches/{branch_id}/delete")
async def delete_branch(
    request: Request,
    branch_id: int,
):
    """Удалить филиал."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import select, delete
    from database.models import Branch, PartnerBranch
    
    async with AsyncSessionLocal() as db:
        # Сначала удаляем связи с партнёрами
        await db.execute(
            delete(PartnerBranch).where(PartnerBranch.branch_id == branch_id)
        )
        
        # Затем удаляем сам филиал
        await db.execute(
            delete(Branch).where(Branch.id == branch_id)
        )
        await db.commit()
    
    logger.info(f"Branch {branch_id} deleted")
    return RedirectResponse(url="/branches", status_code=302)


# ═══════════════════════════════════════════════════════════════════
# Салоны YClients (автосинхронизация)
# ═══════════════════════════════════════════════════════════════════

@router.get("/yclients-companies", response_class=HTMLResponse)
async def yclients_companies_page(request: Request, status: str = None):
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
        "cities_count": len(cities),
        "cities": sorted(cities.items(), key=lambda x: x[1], reverse=True),
        "current_filter": current_filter,
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
            if r.revenue > 0:
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
            if r.revenue > 0:
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

