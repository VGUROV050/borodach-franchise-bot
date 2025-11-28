# Database CRUD operations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Partner,
    Branch,
    PartnerBranch,
    PartnerStatus,
    NetworkRating,
    NetworkRatingHistory,
    YClientsCompany,
    PartnerCompany,
    RequestLog,
    RequestType,
    RequestStatus,
)

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
        selectinload(Partner.branches).selectinload(PartnerBranch.branch),
        selectinload(Partner.companies).selectinload(PartnerCompany.company),
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
    """Обновить партнёра: добавить заявку на новый барбершоп."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    
    if not partner:
        return None
    
    # Заменяем текст заявки (не добавляем к старому)
    partner.branches_text = branch_text
    
    # Помечаем что есть запрос на новый барбершоп
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
    """Очистить флаг и текст заявки на барбершоп."""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    
    if not partner:
        return None
    
    partner.has_pending_branch = False
    partner.branches_text = None  # Очищаем текст заявки
    
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


# ═══════════════════════════════════════════════════════════════════
# Network Rating CRUD
# ═══════════════════════════════════════════════════════════════════

async def get_network_rating_by_company(
    db: AsyncSession,
    yclients_company_id: str,
) -> Optional[NetworkRating]:
    """Получить рейтинг салона по YClients ID."""
    result = await db.execute(
        select(NetworkRating).where(NetworkRating.yclients_company_id == yclients_company_id)
    )
    return result.scalar_one_or_none()


async def update_network_rating(
    db: AsyncSession,
    yclients_company_id: str,
    company_name: str,
    revenue: float,
    rank: int,
    total_companies: int,
    avg_check: float = 0.0,
    previous_rank: int = 0,
) -> NetworkRating:
    """Обновить или создать запись рейтинга салона."""
    result = await db.execute(
        select(NetworkRating).where(NetworkRating.yclients_company_id == yclients_company_id)
    )
    rating = result.scalar_one_or_none()
    
    if rating:
        # Обновляем существующую запись
        rating.company_name = company_name
        rating.revenue = revenue
        rating.rank = rank
        rating.total_companies = total_companies
        rating.avg_check = avg_check
        if previous_rank > 0:
            rating.previous_rank = previous_rank
    else:
        # Создаём новую запись
        rating = NetworkRating(
            yclients_company_id=yclients_company_id,
            company_name=company_name,
            revenue=revenue,
            rank=rank,
            total_companies=total_companies,
            avg_check=avg_check,
            previous_rank=previous_rank,
        )
        db.add(rating)
    
    await db.commit()
    await db.refresh(rating)
    return rating


async def get_all_network_ratings(
    db: AsyncSession,
) -> list[NetworkRating]:
    """Получить весь рейтинг сети."""
    result = await db.execute(
        select(NetworkRating).order_by(NetworkRating.rank)
    )
    return list(result.scalars().all())


async def save_rating_history(
    db: AsyncSession,
    year: int,
    month: int,
) -> int:
    """
    Сохранить текущий рейтинг в историю за указанный месяц.
    Возвращает количество сохранённых записей.
    """
    # Проверяем, нет ли уже записей за этот месяц
    existing = await db.execute(
        select(NetworkRatingHistory).where(
            NetworkRatingHistory.year == year,
            NetworkRatingHistory.month == month,
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Rating history for {year}-{month} already exists, skipping")
        return 0
    
    # Получаем текущий рейтинг
    ratings = await get_all_network_ratings(db)
    
    count = 0
    for r in ratings:
        history = NetworkRatingHistory(
            yclients_company_id=r.yclients_company_id,
            company_name=r.company_name,
            revenue=r.revenue,
            avg_check=r.avg_check,
            rank=r.rank,
            total_companies=r.total_companies,
            year=year,
            month=month,
        )
        db.add(history)
        count += 1
    
    await db.commit()
    logger.info(f"Saved {count} ratings to history for {year}-{month}")
    return count


async def get_rating_history(
    db: AsyncSession,
    year: int,
    month: int,
) -> list[NetworkRatingHistory]:
    """Получить рейтинг за конкретный месяц из истории."""
    result = await db.execute(
        select(NetworkRatingHistory).where(
            NetworkRatingHistory.year == year,
            NetworkRatingHistory.month == month,
        ).order_by(NetworkRatingHistory.rank)
    )
    return list(result.scalars().all())


async def get_previous_month_ranks(
    db: AsyncSession,
    year: int,
    month: int,
) -> dict[str, int]:
    """
    Получить словарь company_id -> rank за указанный месяц.
    Используется для вычисления изменения позиции.
    """
    history = await get_rating_history(db, year, month)
    return {h.yclients_company_id: h.rank for h in history}


# ═══════════════════════════════════════════════════════════════════
# YClients Companies CRUD
# ═══════════════════════════════════════════════════════════════════

async def sync_yclients_companies(
    db: AsyncSession,
    companies: list[dict],
) -> tuple[int, int]:
    """
    Синхронизировать список салонов из YClients.
    Добавляет новые, обновляет существующие.
    
    Args:
        db: Сессия БД
        companies: Список салонов из YClients API
            [{"id": "123", "title": "Название", "city": "Москва", "region": "МО", "is_million_city": True}, ...]
    
    Returns:
        Tuple (добавлено, обновлено)
    """
    added = 0
    updated = 0
    
    for company_data in companies:
        yclients_id = str(company_data.get("id"))
        name = company_data.get("title", f"Салон {yclients_id}")
        city = company_data.get("city")
        region = company_data.get("region")
        is_million_city = company_data.get("is_million_city", False)
        
        # Проверяем, существует ли уже
        result = await db.execute(
            select(YClientsCompany).where(
                YClientsCompany.yclients_id == yclients_id
            )
        )
        existing = result.scalar()
        
        if existing:
            # Обновляем
            existing.name = name
            existing.city = city
            existing.region = region
            existing.is_million_city = is_million_city
            existing.is_active = True
            updated += 1
        else:
            # Создаём новый
            new_company = YClientsCompany(
                yclients_id=yclients_id,
                name=name,
                city=city,
                region=region,
                is_million_city=is_million_city,
                is_active=True,
            )
            db.add(new_company)
            added += 1
    
    await db.commit()
    logger.info(f"Synced YClients companies: {added} added, {updated} updated")
    return added, updated


async def get_all_yclients_companies(
    db: AsyncSession,
    only_active: bool = True,
) -> list[YClientsCompany]:
    """Получить все салоны YClients."""
    query = select(YClientsCompany).order_by(YClientsCompany.name)
    
    if only_active:
        query = query.where(YClientsCompany.is_active == True)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_yclients_company_by_id(
    db: AsyncSession,
    yclients_id: str,
) -> Optional[YClientsCompany]:
    """Получить салон по YClients ID."""
    result = await db.execute(
        select(YClientsCompany).where(
            YClientsCompany.yclients_id == yclients_id
        )
    )
    return result.scalar()


async def get_yclients_company_by_pk(
    db: AsyncSession,
    company_id: int,
) -> Optional[YClientsCompany]:
    """Получить салон по первичному ключу."""
    result = await db.execute(
        select(YClientsCompany).where(
            YClientsCompany.id == company_id
        )
    )
    return result.scalar()


# ═══════════════════════════════════════════════════════════════════
# Partner-Company Links CRUD
# ═══════════════════════════════════════════════════════════════════

async def link_partner_to_company(
    db: AsyncSession,
    partner_id: int,
    company_id: int,
    is_owner: bool = False,
) -> PartnerCompany:
    """Привязать партнёра к салону YClients."""
    # Проверяем, есть ли уже связь
    result = await db.execute(
        select(PartnerCompany).where(
            PartnerCompany.partner_id == partner_id,
            PartnerCompany.company_id == company_id,
        )
    )
    existing = result.scalar()
    
    if existing:
        logger.info(f"Partner {partner_id} already linked to company {company_id}")
        return existing
    
    # Создаём связь
    link = PartnerCompany(
        partner_id=partner_id,
        company_id=company_id,
        is_owner=is_owner,
    )
    db.add(link)
    await db.commit()
    
    logger.info(f"Linked partner {partner_id} to company {company_id}")
    return link


async def unlink_partner_from_company(
    db: AsyncSession,
    partner_id: int,
    company_id: int,
) -> bool:
    """Удалить связь партнёра с салоном."""
    result = await db.execute(
        select(PartnerCompany).where(
            PartnerCompany.partner_id == partner_id,
            PartnerCompany.company_id == company_id,
        )
    )
    link = result.scalar()
    
    if link:
        await db.delete(link)
        await db.commit()
        logger.info(f"Unlinked partner {partner_id} from company {company_id}")
        return True
    
    return False


async def get_partner_companies(
    db: AsyncSession,
    partner_id: int,
) -> list[YClientsCompany]:
    """Получить все салоны партнёра."""
    result = await db.execute(
        select(YClientsCompany)
        .join(PartnerCompany)
        .where(PartnerCompany.partner_id == partner_id)
        .order_by(YClientsCompany.name)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════
# Request Log CRUD
# ═══════════════════════════════════════════════════════════════════

async def create_request_log(
    db: AsyncSession,
    partner_id: int,
    request_type: RequestType,
    status: RequestStatus,
    request_text: str | None = None,
    result_text: str | None = None,
    processed_by: str = "admin",
) -> RequestLog:
    """Создать запись в логе заявок."""
    log = RequestLog(
        partner_id=partner_id,
        request_type=request_type,
        status=status,
        request_text=request_text,
        result_text=result_text,
        processed_by=processed_by,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    
    logger.info(f"Created request log: {request_type.value} - {status.value} for partner {partner_id}")
    return log


async def get_request_logs(
    db: AsyncSession,
    limit: int = 100,
    request_type: RequestType | None = None,
    status: RequestStatus | None = None,
) -> list[RequestLog]:
    """Получить лог заявок с фильтрами."""
    query = (
        select(RequestLog)
        .options(selectinload(RequestLog.partner))
        .order_by(RequestLog.created_at.desc())
    )
    
    if request_type:
        query = query.where(RequestLog.request_type == request_type)
    if status:
        query = query.where(RequestLog.status == status)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())

