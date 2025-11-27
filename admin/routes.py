# Admin panel routes

import logging
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config.settings import BASE_DIR, ADMIN_USERNAME, ADMIN_PASSWORD
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


@router.post("/partners/{partner_id}/verify")
async def verify_partner(
    request: Request,
    partner_id: int,
):
    """Верифицировать партнёра."""
    if not verify_session(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionLocal() as db:
        partner = await update_partner_status(
            db=db,
            partner_id=partner_id,
            status=PartnerStatus.VERIFIED,
            verified_by="admin",
        )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    
    logger.info(f"Partner {partner_id} verified")
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
    
    from database.crud import create_branch
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

