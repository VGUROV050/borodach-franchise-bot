# Database CRUD operations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Partner, Branch, PartnerBranch, PartnerStatus

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Partner CRUD
# ═══════════════════════════════════════════════════════════════════

async def get_partner_by_telegram_id(
    db: AsyncSession,
    telegram_id: int,
) -> Optional[Partner]:
    """Получить партнёра по Telegram ID."""
    result = await db.execute(
        select(Partner)
        .options(selectinload(Partner.branches).selectinload(PartnerBranch.branch))
        .where(Partner.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_partner_by_phone(
    db: AsyncSession,
    phone: str,
) -> Optional[Partner]:
    """Получить партнёра по номеру телефона."""
    # Нормализуем номер (убираем всё кроме цифр)
    normalized = "".join(filter(str.isdigit, phone))
    
    result = await db.execute(
        select(Partner).where(Partner.phone.contains(normalized[-10:]))  # Последние 10 цифр
    )
    return result.scalar_one_or_none()


async def create_partner(
    db: AsyncSession,
    telegram_id: int,
    telegram_username: Optional[str],
    full_name: str,
    phone: Optional[str] = None,
    telegram_first_name: Optional[str] = None,
    telegram_last_name: Optional[str] = None,
    branches_text: Optional[str] = None,
) -> Partner:
    """Создать нового партнёра."""
    partner = Partner(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        telegram_first_name=telegram_first_name,
        telegram_last_name=telegram_last_name,
        full_name=full_name,
        phone=phone,
        branches_text=branches_text,
        status=PartnerStatus.PENDING,
    )
    
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    
    logger.info(f"Created partner: {partner}")
    return partner


async def update_partner_status(
    db: AsyncSession,
    partner_id: int,
    status: PartnerStatus,
    verified_by: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> Optional[Partner]:
    """Обновить статус партнёра."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    
    if not partner:
        return None
    
    partner.status = status
    
    if status == PartnerStatus.VERIFIED:
        partner.verified_at = datetime.now(ZoneInfo("Europe/Moscow"))
        partner.verified_by = verified_by
        partner.rejection_reason = None
    elif status == PartnerStatus.REJECTED:
        partner.rejection_reason = rejection_reason
        partner.verified_at = None
        partner.verified_by = None
    
    await db.commit()
    await db.refresh(partner)
    
    logger.info(f"Updated partner {partner_id} status to {status.value}")
    return partner


async def get_all_partners(
    db: AsyncSession,
    status: Optional[PartnerStatus] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Partner]:
    """Получить список партнёров с фильтрацией по статусу."""
    query = select(Partner).options(
        selectinload(Partner.branches).selectinload(PartnerBranch.branch)
    )
    
    if status:
        query = query.where(Partner.status == status)
    
    query = query.order_by(Partner.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_pending_partners(db: AsyncSession) -> list[Partner]:
    """Получить партнёров, ожидающих верификации."""
    return await get_all_partners(db, status=PartnerStatus.PENDING)


# ═══════════════════════════════════════════════════════════════════
# Branch CRUD
# ═══════════════════════════════════════════════════════════════════

async def get_all_branches(
    db: AsyncSession,
    only_active: bool = True,
) -> list[Branch]:
    """Получить все филиалы."""
    query = select(Branch)
    
    if only_active:
        query = query.where(Branch.is_active == True)
    
    query = query.order_by(Branch.city, Branch.address)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_branch(
    db: AsyncSession,
    city: str,
    address: str,
    name: Optional[str] = None,
) -> Branch:
    """Создать новый филиал."""
    branch = Branch(
        city=city,
        address=address,
        name=name,
    )
    
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    
    logger.info(f"Created branch: {branch}")
    return branch


async def get_or_create_branch(
    db: AsyncSession,
    city: str,
    address: str,
    name: Optional[str] = None,
) -> Branch:
    """Получить или создать филиал."""
    result = await db.execute(
        select(Branch).where(
            Branch.city == city,
            Branch.address == address,
        )
    )
    branch = result.scalar_one_or_none()
    
    if branch:
        return branch
    
    return await create_branch(db, city, address, name)


# ═══════════════════════════════════════════════════════════════════
# Partner-Branch CRUD
# ═══════════════════════════════════════════════════════════════════

async def link_partner_to_branch(
    db: AsyncSession,
    partner_id: int,
    branch_id: int,
    is_owner: bool = False,
) -> PartnerBranch:
    """Связать партнёра с филиалом."""
    # Проверяем, нет ли уже такой связи
    result = await db.execute(
        select(PartnerBranch).where(
            PartnerBranch.partner_id == partner_id,
            PartnerBranch.branch_id == branch_id,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing
    
    link = PartnerBranch(
        partner_id=partner_id,
        branch_id=branch_id,
        is_owner=is_owner,
    )
    
    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    logger.info(f"Linked partner {partner_id} to branch {branch_id}")
    return link


async def get_partner_branches(
    db: AsyncSession,
    partner_id: int,
) -> list[PartnerBranch]:
    """Получить филиалы партнёра (с данными филиала)."""
    result = await db.execute(
        select(PartnerBranch)
        .options(selectinload(PartnerBranch.branch))
        .where(PartnerBranch.partner_id == partner_id)
    )
    return list(result.scalars().all())


async def update_partner_for_branch_request(
    db: AsyncSession,
    partner_id: int,
    branch_text: str,
) -> Optional[Partner]:
    """Обновить партнёра: добавить заявку на новый филиал."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    
    if not partner:
        return None
    
    # Добавляем текст филиала к существующим (если есть)
    if partner.branches_text:
        partner.branches_text = f"{partner.branches_text}\n---\n{branch_text}"
    else:
        partner.branches_text = branch_text
    
    # Если партнёр уже верифицирован, помечаем что есть запрос на новый филиал
    partner.has_pending_branch = True
    
    await db.commit()
    await db.refresh(partner)
    
    logger.info(f"Partner {partner_id} requested new branch: {branch_text}")
    return partner


async def get_partner_by_id(
    db: AsyncSession,
    partner_id: int,
) -> Optional[Partner]:
    """Получить партнёра по ID."""
    result = await db.execute(
        select(Partner)
        .options(selectinload(Partner.branches).selectinload(PartnerBranch.branch))
        .where(Partner.id == partner_id)
    )
    return result.scalar_one_or_none()


async def delete_partner(
    db: AsyncSession,
    partner_id: int,
) -> bool:
    """Удалить партнёра."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    
    if not partner:
        return False
    
    await db.delete(partner)
    await db.commit()
    
    logger.info(f"Deleted partner {partner_id}")
    return True


async def clear_partner_pending_branch(
    db: AsyncSession,
    partner_id: int,
) -> Optional[Partner]:
    """Очистить флаг ожидающего филиала."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    
    if not partner:
        return None
    
    partner.has_pending_branch = False
    
    await db.commit()
    await db.refresh(partner)
    
    return partner


async def get_partners_with_pending_branches(
    db: AsyncSession,
) -> list[Partner]:
    """Получить верифицированных партнёров с запросами на добавление филиала."""
    result = await db.execute(
        select(Partner)
        .options(selectinload(Partner.branches).selectinload(PartnerBranch.branch))
        .where(
            Partner.status == PartnerStatus.VERIFIED,
            Partner.has_pending_branch == True,
        )
        .order_by(Partner.created_at.desc())
    )
    return list(result.scalars().all())

