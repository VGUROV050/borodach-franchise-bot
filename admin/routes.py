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
)
from .auth import verify_session, create_session

logger = logging.getLogger(__name__)


async def send_telegram_notification(chat_id: int, text: str) -> bool:
    """Отправить уведомление пользователю через Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping notification")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            })
            
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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "pending_partners": pending,
        "verified_partners": verified,
        "rejected_partners": rejected,
        "pending_count": len(pending),
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
    """Страница верификации партнёра с выбором филиалов."""
    if not verify_session(request):
        return RedirectResponse(url="/login", status_code=302)
    
    from sqlalchemy import select
    from database.models import Partner
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        branches = await get_all_branches(db, only_active=True)
    
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    
    return templates.TemplateResponse("verify_partner.html", {
        "request": request,
        "partner": partner,
        "branches": branches,
    })


@router.post("/partners/{partner_id}/verify")
async def verify_partner(
    request: Request,
    partner_id: int,
    branch_ids: list[int] = Form(default=[]),
):
    """Верифицировать партнёра с привязкой к филиалам."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from database.crud import link_partner_to_branch
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
        
        # Привязываем к филиалам
        for branch_id in branch_ids:
            await link_partner_to_branch(
                db=db,
                partner_id=partner_id,
                branch_id=branch_id,
                is_owner=True,
            )
    
    # Отправляем уведомление пользователю
    if telegram_id:
        await send_telegram_notification(
            telegram_id,
            f"🎉 <b>Поздравляем, {partner_name}!</b>\n\n"
            f"Ваша заявка на регистрацию одобрена!\n\n"
            f"Теперь вы можете:\n"
            f"• 🆕 Создавать задачи\n"
            f"• 📋 Просматривать свои задачи\n\n"
            f"Нажмите /start чтобы начать работу.",
        )
    
    logger.info(f"Partner {partner_id} verified with branches: {branch_ids}")
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
        partner = await update_partner_status(
            db=db,
            partner_id=partner_id,
            status=PartnerStatus.REJECTED,
            rejection_reason=reason or "Заявка отклонена администратором",
        )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    
    logger.info(f"Partner {partner_id} rejected: {reason}")
    return RedirectResponse(url="/", status_code=302)


@router.post("/partners/{partner_id}/delete")
async def delete_partner(
    request: Request,
    partner_id: int,
):
    """Удалить партнёра."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from sqlalchemy import delete
    from database.models import Partner, PartnerBranch
    
    async with AsyncSessionLocal() as db:
        # Сначала удаляем связи с филиалами
        await db.execute(
            delete(PartnerBranch).where(PartnerBranch.partner_id == partner_id)
        )
        
        # Затем удаляем партнёра
        await db.execute(
            delete(Partner).where(Partner.id == partner_id)
        )
        await db.commit()
    
    logger.info(f"Partner {partner_id} deleted")
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

