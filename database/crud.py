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
    is_owner: bool = True,
    position: Optional[str] = None,
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
        is_owner=is_owner,
        position=position,
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
    # Новые метрики
    city: str = None,
    is_million_city: bool = False,
    services_revenue: float = 0.0,
    products_revenue: float = 0.0,
    completed_count: int = 0,
    repeat_visitors_pct: float = 0.0,
    # Клиентская статистика
    new_clients_count: int = 0,
    return_clients_count: int = 0,
    total_clients_count: int = 0,
    client_base_return_pct: float = 0.0,
) -> NetworkRating:
    """Обновить или создать запись рейтинга салона с расширенными метриками."""
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
        # Новые поля
        if city:
            rating.city = city
        rating.is_million_city = is_million_city
        rating.services_revenue = services_revenue
        rating.products_revenue = products_revenue
        rating.completed_count = completed_count
        rating.repeat_visitors_pct = repeat_visitors_pct
        # Клиентская статистика
        rating.new_clients_count = new_clients_count
        rating.return_clients_count = return_clients_count
        rating.total_clients_count = total_clients_count
        rating.client_base_return_pct = client_base_return_pct
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
            # Новые поля
            city=city,
            is_million_city=is_million_city,
            services_revenue=services_revenue,
            products_revenue=products_revenue,
            completed_count=completed_count,
            repeat_visitors_pct=repeat_visitors_pct,
            # Клиентская статистика
            new_clients_count=new_clients_count,
            return_clients_count=return_clients_count,
            total_clients_count=total_clients_count,
            client_base_return_pct=client_base_return_pct,
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


async def get_last_network_rating_update(db: AsyncSession) -> datetime | None:
    """Получить время последнего обновления рейтинга."""
    result = await db.execute(
        select(NetworkRating.updated_at).order_by(NetworkRating.updated_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def save_rating_history(
    db: AsyncSession,
    year: int,
    month: int,
) -> int:
    """
    Сохранить текущий рейтинг в историю за указанный месяц.
    Включает все расширенные метрики.
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
            city=r.city,
            revenue=r.revenue,
            services_revenue=r.services_revenue,
            products_revenue=r.products_revenue,
            avg_check=r.avg_check,
            completed_count=r.completed_count,
            repeat_visitors_pct=r.repeat_visitors_pct,
            # Клиентская статистика
            new_clients_count=r.new_clients_count,
            return_clients_count=r.return_clients_count,
            total_clients_count=r.total_clients_count,
            client_base_return_pct=r.client_base_return_pct,
            # Рейтинг
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


# ═══════════════════════════════════════════════════════════════════
# Сравнение по городам и регионам
# ═══════════════════════════════════════════════════════════════════

async def get_city_average(
    db: AsyncSession,
    city: str,
) -> dict:
    """
    Получить средние метрики по городу.
    
    Returns:
        {
            "city": str,
            "company_count": int,
            "avg_revenue": float,
            "avg_services_revenue": float,
            "avg_products_revenue": float,
            "avg_check": float,
            "avg_completed_count": float,
            "avg_repeat_visitors_pct": float,
        }
    """
    from sqlalchemy import func as sqlfunc
    
    result = await db.execute(
        select(
            sqlfunc.count(NetworkRating.id).label("count"),
            sqlfunc.avg(NetworkRating.revenue).label("avg_revenue"),
            sqlfunc.avg(NetworkRating.services_revenue).label("avg_services_revenue"),
            sqlfunc.avg(NetworkRating.products_revenue).label("avg_products_revenue"),
            sqlfunc.avg(NetworkRating.avg_check).label("avg_check"),
            sqlfunc.avg(NetworkRating.completed_count).label("avg_completed_count"),
            sqlfunc.avg(NetworkRating.repeat_visitors_pct).label("avg_repeat_pct"),
        ).where(
            NetworkRating.city == city,
            NetworkRating.revenue > 0,  # Только активные
        )
    )
    row = result.one()
    
    return {
        "city": city,
        "company_count": row.count or 0,
        "avg_revenue": float(row.avg_revenue or 0),
        "avg_services_revenue": float(row.avg_services_revenue or 0),
        "avg_products_revenue": float(row.avg_products_revenue or 0),
        "avg_check": float(row.avg_check or 0),
        "avg_completed_count": float(row.avg_completed_count or 0),
        "avg_repeat_visitors_pct": float(row.avg_repeat_pct or 0),
    }


async def get_similar_cities_average(
    db: AsyncSession,
    is_million_city: bool,
) -> dict:
    """
    Получить средние метрики по похожим городам (миллионники vs остальные).
    
    Returns:
        {
            "city_type": "millionnik" | "region",
            "company_count": int,
            "avg_revenue": float,
            "avg_services_revenue": float,
            "avg_products_revenue": float,
            "avg_check": float,
            "avg_completed_count": float,
            "avg_repeat_visitors_pct": float,
        }
    """
    from sqlalchemy import func as sqlfunc
    
    result = await db.execute(
        select(
            sqlfunc.count(NetworkRating.id).label("count"),
            sqlfunc.avg(NetworkRating.revenue).label("avg_revenue"),
            sqlfunc.avg(NetworkRating.services_revenue).label("avg_services_revenue"),
            sqlfunc.avg(NetworkRating.products_revenue).label("avg_products_revenue"),
            sqlfunc.avg(NetworkRating.avg_check).label("avg_check"),
            sqlfunc.avg(NetworkRating.completed_count).label("avg_completed_count"),
            sqlfunc.avg(NetworkRating.repeat_visitors_pct).label("avg_repeat_pct"),
        ).where(
            NetworkRating.is_million_city == is_million_city,
            NetworkRating.revenue > 0,
        )
    )
    row = result.one()
    
    return {
        "city_type": "millionnik" if is_million_city else "region",
        "company_count": row.count or 0,
        "avg_revenue": float(row.avg_revenue or 0),
        "avg_services_revenue": float(row.avg_services_revenue or 0),
        "avg_products_revenue": float(row.avg_products_revenue or 0),
        "avg_check": float(row.avg_check or 0),
        "avg_completed_count": float(row.avg_completed_count or 0),
        "avg_repeat_visitors_pct": float(row.avg_repeat_pct or 0),
    }


async def get_company_history_12m(
    db: AsyncSession,
    yclients_company_id: str,
) -> list[NetworkRatingHistory]:
    """
    Получить историю метрик салона за последние 12 месяцев.
    Отсортировано от старых к новым.
    """
    from datetime import datetime
    
    # Определяем диапазон: последние 12 месяцев
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Вычисляем год и месяц 12 месяцев назад
    if current_month > 12:
        start_year = current_year - 1
        start_month = current_month
    else:
        months_back = 12
        total_months = current_year * 12 + current_month - months_back
        start_year = total_months // 12
        start_month = total_months % 12 or 12
    
    result = await db.execute(
        select(NetworkRatingHistory).where(
            NetworkRatingHistory.yclients_company_id == yclients_company_id,
        ).order_by(
            NetworkRatingHistory.year,
            NetworkRatingHistory.month,
        )
    )
    
    return list(result.scalars().all())


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


# ═══════════════════════════════════════════════════════════════════
# Poll CRUD
# ═══════════════════════════════════════════════════════════════════

from .models import Poll, PollOption, PollResponse, PollMessage, PollStatus
import json


async def create_poll(
    db: AsyncSession,
    question: str,
    options: list[str],
    is_anonymous: bool = True,
    allows_multiple: bool = False,
    created_by: str = "admin",
) -> Poll:
    """Создать новое голосование."""
    poll = Poll(
        question=question,
        is_anonymous=is_anonymous,
        allows_multiple=allows_multiple,
        status=PollStatus.DRAFT,
        created_by=created_by,
    )
    db.add(poll)
    await db.flush()  # Чтобы получить poll.id
    
    # Добавляем варианты ответов
    for i, option_text in enumerate(options):
        option = PollOption(
            poll_id=poll.id,
            text=option_text,
            position=i,
        )
        db.add(option)
    
    await db.commit()
    await db.refresh(poll)
    
    logger.info(f"Created poll {poll.id}: {question[:50]}...")
    return poll


async def get_poll_by_id(
    db: AsyncSession,
    poll_id: int,
) -> Optional[Poll]:
    """Получить голосование по ID с опциями и ответами."""
    result = await db.execute(
        select(Poll)
        .options(
            selectinload(Poll.options),
            selectinload(Poll.responses).selectinload(PollResponse.partner),
            selectinload(Poll.sent_messages),
        )
        .where(Poll.id == poll_id)
    )
    return result.scalar_one_or_none()


async def get_all_polls(
    db: AsyncSession,
    status: PollStatus | None = None,
) -> list[Poll]:
    """Получить все голосования."""
    query = (
        select(Poll)
        .options(
            selectinload(Poll.options),
            selectinload(Poll.responses),
        )
        .order_by(Poll.created_at.desc())
    )
    
    if status:
        query = query.where(Poll.status == status)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_poll_status(
    db: AsyncSession,
    poll_id: int,
    status: PollStatus,
) -> Optional[Poll]:
    """Обновить статус голосования."""
    result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()
    
    if not poll:
        return None
    
    poll.status = status
    
    if status == PollStatus.SENT:
        poll.sent_at = datetime.now(ZoneInfo("Europe/Moscow"))
    elif status == PollStatus.CLOSED:
        poll.closed_at = datetime.now(ZoneInfo("Europe/Moscow"))
    
    await db.commit()
    await db.refresh(poll)
    
    logger.info(f"Updated poll {poll_id} status to {status.value}")
    return poll


async def save_poll_message(
    db: AsyncSession,
    poll_id: int,
    partner_id: int,
    telegram_chat_id: int,
    telegram_message_id: int,
    telegram_poll_id: str,
) -> PollMessage:
    """Сохранить информацию об отправленном опросе."""
    msg = PollMessage(
        poll_id=poll_id,
        partner_id=partner_id,
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
        telegram_poll_id=telegram_poll_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    
    return msg


async def save_poll_response(
    db: AsyncSession,
    poll_id: int,
    partner_id: int,
    option_ids: list[int],
) -> PollResponse:
    """Сохранить ответ пользователя на голосование."""
    # Проверяем, не отвечал ли уже
    result = await db.execute(
        select(PollResponse).where(
            PollResponse.poll_id == poll_id,
            PollResponse.partner_id == partner_id,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Обновляем ответ
        existing.option_ids = json.dumps(option_ids)
        existing.answered_at = datetime.now(ZoneInfo("Europe/Moscow"))
        await db.commit()
        await db.refresh(existing)
        return existing
    
    # Создаём новый ответ
    response = PollResponse(
        poll_id=poll_id,
        partner_id=partner_id,
        option_ids=json.dumps(option_ids),
    )
    db.add(response)
    await db.commit()
    await db.refresh(response)
    
    logger.info(f"Saved poll response: poll={poll_id}, partner={partner_id}, options={option_ids}")
    return response


async def get_poll_messages(
    db: AsyncSession,
    poll_id: int,
) -> list[PollMessage]:
    """Получить все сообщения голосования (для закрытия)."""
    result = await db.execute(
        select(PollMessage).where(
            PollMessage.poll_id == poll_id,
            PollMessage.is_stopped == False,
        )
    )
    return list(result.scalars().all())


async def mark_poll_message_stopped(
    db: AsyncSession,
    message_id: int,
) -> None:
    """Пометить сообщение как закрытое."""
    result = await db.execute(
        select(PollMessage).where(PollMessage.id == message_id)
    )
    msg = result.scalar_one_or_none()
    
    if msg:
        msg.is_stopped = True
        await db.commit()


async def delete_poll(
    db: AsyncSession,
    poll_id: int,
) -> bool:
    """Удалить голосование (только черновик)."""
    result = await db.execute(
        select(Poll).where(
            Poll.id == poll_id,
            Poll.status == PollStatus.DRAFT,
        )
    )
    poll = result.scalar_one_or_none()
    
    if not poll:
        return False
    
    await db.delete(poll)
    await db.commit()
    
    logger.info(f"Deleted poll {poll_id}")
    return True


async def get_poll_results(
    db: AsyncSession,
    poll_id: int,
) -> dict:
    """
    Получить результаты голосования.
    
    Returns:
        {
            "question": "...",
            "total_votes": 45,
            "options": [
                {"id": 1, "text": "Вариант 1", "votes": 20, "percent": 44.4},
                {"id": 2, "text": "Вариант 2", "votes": 25, "percent": 55.6},
            ],
            "responses": [
                {"partner_name": "Иван", "options": ["Вариант 1"], "answered_at": "..."},
            ]
        }
    """
    poll = await get_poll_by_id(db, poll_id)
    
    if not poll:
        return {}
    
    # Подсчитываем голоса
    option_votes: dict[int, int] = {opt.id: 0 for opt in poll.options}
    
    for response in poll.responses:
        selected_ids = json.loads(response.option_ids)
        for opt_id in selected_ids:
            if opt_id in option_votes:
                option_votes[opt_id] += 1
    
    total_votes = len(poll.responses)
    
    # Формируем результаты по опциям
    options_result = []
    for opt in poll.options:
        votes = option_votes[opt.id]
        percent = (votes / total_votes * 100) if total_votes > 0 else 0
        options_result.append({
            "id": opt.id,
            "text": opt.text,
            "votes": votes,
            "percent": round(percent, 1),
        })
    
    # Формируем список ответов (если не анонимное)
    responses_list = []
    if not poll.is_anonymous:
        for response in poll.responses:
            selected_ids = json.loads(response.option_ids)
            selected_texts = [
                opt.text for opt in poll.options 
                if opt.id in selected_ids
            ]
            responses_list.append({
                "partner_name": response.partner.full_name if response.partner else "Неизвестно",
                "options": selected_texts,
                "answered_at": response.answered_at.strftime("%d.%m.%Y %H:%M"),
            })
    
    return {
        "question": poll.question,
        "total_votes": total_votes,
        "is_anonymous": poll.is_anonymous,
        "options": options_result,
        "responses": responses_list,
    }


# ═══════════════════════════════════════════════════════════════════
# Department Info CRUD (Полезное)
# ═══════════════════════════════════════════════════════════════════

from .models import DepartmentInfo, DepartmentType, DepartmentInfoType


async def get_department_info(
    db: AsyncSession,
    department: DepartmentType,
    info_type: DepartmentInfoType,
) -> Optional[DepartmentInfo]:
    """Получить текст для отдела и типа информации."""
    result = await db.execute(
        select(DepartmentInfo).where(
            DepartmentInfo.department == department,
            DepartmentInfo.info_type == info_type,
        )
    )
    return result.scalar_one_or_none()


async def get_all_department_info(
    db: AsyncSession,
) -> list[DepartmentInfo]:
    """Получить все настройки текстов."""
    result = await db.execute(
        select(DepartmentInfo).order_by(
            DepartmentInfo.department,
            DepartmentInfo.info_type,
        )
    )
    return list(result.scalars().all())


async def upsert_department_info(
    db: AsyncSession,
    department: DepartmentType,
    info_type: DepartmentInfoType,
    text: str,
    updated_by: str = "admin",
) -> DepartmentInfo:
    """Создать или обновить текст для отдела."""
    # Проверяем существует ли
    result = await db.execute(
        select(DepartmentInfo).where(
            DepartmentInfo.department == department,
            DepartmentInfo.info_type == info_type,
        )
    )
    info = result.scalar_one_or_none()
    
    if info:
        # Обновляем
        info.text = text
        info.updated_by = updated_by
    else:
        # Создаём
        info = DepartmentInfo(
            department=department,
            info_type=info_type,
            text=text,
            updated_by=updated_by,
        )
        db.add(info)
    
    await db.commit()
    await db.refresh(info)
    
    logger.info(f"Updated department info: {department.value}/{info_type.value}")
    return info


async def init_default_department_info(db: AsyncSession) -> None:
    """Инициализировать тексты по умолчанию (если пустые)."""
    defaults = {
        (DepartmentType.DEVELOPMENT, DepartmentInfoType.IMPORTANT_INFO): 
            "🚀 <b>Отдел Развития</b>\n\n"
            "Здесь будет важная информация от отдела развития.\n\n"
            "<i>Текст можно изменить в админке.</i>",
        
        (DepartmentType.DEVELOPMENT, DepartmentInfoType.CONTACT_INFO): 
            "🚀 <b>Связаться с Отделом Развития</b>\n\n"
            "👉 <a href='https://t.me/borodach_development'>@borodach_development</a>\n\n"
            "Отдел отвечает за:\n"
            "• Открытие новых точек\n"
            "• Вопросы по франшизе\n"
            "• Стратегическое развитие",
        
        (DepartmentType.MARKETING, DepartmentInfoType.IMPORTANT_INFO): 
            "📢 <b>Отдел Маркетинга</b>\n\n"
            "Здесь будет важная информация от отдела маркетинга.\n\n"
            "<i>Текст можно изменить в админке.</i>",
        
        (DepartmentType.MARKETING, DepartmentInfoType.CONTACT_INFO): 
            "📢 <b>Связаться с Отделом Маркетинга</b>\n\n"
            "👉 <a href='https://t.me/borodach_marketing'>@borodach_marketing</a>\n\n"
            "Отдел отвечает за:\n"
            "• Рекламные материалы\n"
            "• Маркетинговые акции\n"
            "• SMM и продвижение",
        
        (DepartmentType.DESIGN, DepartmentInfoType.IMPORTANT_INFO): 
            "🎨 <b>Отдел Дизайна</b>\n\n"
            "Здесь будет важная информация от отдела дизайна.\n\n"
            "<i>Текст можно изменить в админке.</i>",
        
        (DepartmentType.DESIGN, DepartmentInfoType.CONTACT_INFO): 
            "🎨 <b>Связаться с Отделом Дизайна</b>\n\n"
            "Напишите в чат поддержки для связи с дизайнерами.\n\n"
            "Отдел отвечает за:\n"
            "• Дизайн материалов\n"
            "• Оформление точек\n"
            "• Брендинг",
    }
    
    for (dept, info_type), text in defaults.items():
        existing = await get_department_info(db, dept, info_type)
        if not existing:
            await upsert_department_info(db, dept, info_type, text)


# ═══════════════════════════════════════════════════════════════════
# Department Buttons (Кастомные кнопки для "Полезное")
# ═══════════════════════════════════════════════════════════════════

async def get_department_buttons(
    db: AsyncSession,
    department: DepartmentType,
    only_active: bool = True,
) -> list["DepartmentButton"]:
    """Получить все кнопки для отдела."""
    from database.models import DepartmentButton
    
    query = select(DepartmentButton).where(
        DepartmentButton.department == department
    ).order_by(DepartmentButton.order, DepartmentButton.id)
    
    if only_active:
        query = query.where(DepartmentButton.is_active == True)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_department_buttons(
    db: AsyncSession,
) -> list["DepartmentButton"]:
    """Получить все кнопки всех отделов."""
    from database.models import DepartmentButton
    
    result = await db.execute(
        select(DepartmentButton).order_by(
            DepartmentButton.department,
            DepartmentButton.order,
            DepartmentButton.id,
        )
    )
    return list(result.scalars().all())


async def get_department_button_by_id(
    db: AsyncSession,
    button_id: int,
) -> Optional["DepartmentButton"]:
    """Получить кнопку по ID."""
    from database.models import DepartmentButton
    
    result = await db.execute(
        select(DepartmentButton).where(DepartmentButton.id == button_id)
    )
    return result.scalar_one_or_none()


async def get_department_button_by_text(
    db: AsyncSession,
    department: DepartmentType,
    button_text: str,
) -> Optional["DepartmentButton"]:
    """Получить кнопку по тексту (для обработки нажатий)."""
    from database.models import DepartmentButton
    
    result = await db.execute(
        select(DepartmentButton).where(
            DepartmentButton.department == department,
            DepartmentButton.button_text == button_text,
            DepartmentButton.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def create_department_button(
    db: AsyncSession,
    department: DepartmentType,
    button_text: str,
    message_text: str,
    order: int = 0,
) -> "DepartmentButton":
    """Создать новую кнопку."""
    from database.models import DepartmentButton
    
    button = DepartmentButton(
        department=department,
        button_text=button_text,
        message_text=message_text,
        order=order,
        is_active=True,
    )
    db.add(button)
    await db.commit()
    await db.refresh(button)
    
    logger.info(f"Created department button: {department.value} - {button_text}")
    return button


async def update_department_button(
    db: AsyncSession,
    button_id: int,
    button_text: Optional[str] = None,
    message_text: Optional[str] = None,
    order: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> Optional["DepartmentButton"]:
    """Обновить кнопку."""
    button = await get_department_button_by_id(db, button_id)
    if not button:
        return None
    
    if button_text is not None:
        button.button_text = button_text
    if message_text is not None:
        button.message_text = message_text
    if order is not None:
        button.order = order
    if is_active is not None:
        button.is_active = is_active
    
    await db.commit()
    await db.refresh(button)
    
    logger.info(f"Updated department button {button_id}: {button.button_text}")
    return button


async def delete_department_button(
    db: AsyncSession,
    button_id: int,
) -> bool:
    """Удалить кнопку."""
    button = await get_department_button_by_id(db, button_id)
    if not button:
        return False
    
    await db.delete(button)
    await db.commit()
    
    logger.info(f"Deleted department button {button_id}")
    return True


async def init_default_department_buttons(db: AsyncSession) -> int:
    """
    Инициализировать дефолтные кнопки для каждого отдела (если пусто).
    Возвращает количество созданных кнопок.
    """
    from database.models import DepartmentButton
    
    # Проверяем есть ли уже кнопки
    result = await db.execute(select(DepartmentButton))
    if result.scalars().first():
        return 0  # Кнопки уже есть
    
    created = 0
    
    # Дефолтные кнопки для каждого отдела
    defaults = {
        DepartmentType.DEVELOPMENT: [
            ("📋 Важная информация", "🚀 <b>Отдел Развития</b>\n\nЗдесь будет важная информация от отдела развития.\n\n<i>Текст можно изменить в админке.</i>", 1),
            ("📞 Связаться с отделом", "🚀 <b>Связаться с Отделом Развития</b>\n\n👉 <a href='https://t.me/borodach_development'>@borodach_development</a>", 2),
        ],
        DepartmentType.MARKETING: [
            ("📋 Важная информация", "📢 <b>Отдел Маркетинга</b>\n\nЗдесь будет важная информация от отдела маркетинга.\n\n<i>Текст можно изменить в админке.</i>", 1),
            ("📞 Связаться с отделом", "📢 <b>Связаться с Отделом Маркетинга</b>\n\n👉 <a href='https://t.me/borodach_marketing'>@borodach_marketing</a>", 2),
        ],
        DepartmentType.DESIGN: [
            ("📋 Важная информация", "🎨 <b>Отдел Дизайна</b>\n\nЗдесь будет важная информация от отдела дизайна.\n\n<i>Текст можно изменить в админке.</i>", 1),
            ("📞 Связаться с отделом", "🎨 <b>Связаться с Отделом Дизайна</b>\n\nНапишите в чат поддержки для связи с дизайнерами.", 2),
        ],
    }
    
    for dept, buttons in defaults.items():
        for button_text, message_text, order in buttons:
            button = DepartmentButton(
                department=dept,
                button_text=button_text,
                message_text=message_text,
                order=order,
                is_active=True,
            )
            db.add(button)
            created += 1
    
    await db.commit()
    logger.info(f"Initialized {created} default department buttons")
    return created


# ═══════════════════════════════════════════════════════════════════
# Bot Settings CRUD
# ═══════════════════════════════════════════════════════════════════

from .models import BotSetting


async def get_bot_setting(
    db: AsyncSession,
    key: str,
    default: str = "",
) -> str:
    """Получить значение настройки бота по ключу."""
    result = await db.execute(
        select(BotSetting).where(BotSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    
    return setting.value if setting else default


async def set_bot_setting(
    db: AsyncSession,
    key: str,
    value: str,
    description: str = None,
) -> BotSetting:
    """Установить значение настройки бота."""
    result = await db.execute(
        select(BotSetting).where(BotSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = BotSetting(
            key=key,
            value=value,
            description=description,
        )
        db.add(setting)
    
    await db.commit()
    await db.refresh(setting)
    
    logger.info(f"Updated bot setting: {key}")
    return setting


async def get_all_bot_settings(db: AsyncSession) -> list[BotSetting]:
    """Получить все настройки бота."""
    result = await db.execute(
        select(BotSetting).order_by(BotSetting.key)
    )
    return list(result.scalars().all())


async def init_default_bot_settings(db: AsyncSession) -> int:
    """Инициализировать настройки по умолчанию."""
    defaults = {
        "contact_office_text": (
            "📞 <b>Связаться с офисом</b>\n\n"
            "Для связи с управляющей компанией BORODACH:\n\n"
            "📧 Email: franchise@borodach.com\n"
            "📱 Телефон: +7 (XXX) XXX-XX-XX\n"
            "💬 Telegram: @borodach_support\n\n"
            "<i>Режим работы: Пн-Пт 10:00-19:00 (МСК)</i>",
            "Текст кнопки 'Связаться с офисом' в главном меню"
        ),
    }
    
    created = 0
    for key, (value, description) in defaults.items():
        existing = await db.execute(
            select(BotSetting).where(BotSetting.key == key)
        )
        if not existing.scalar_one_or_none():
            setting = BotSetting(key=key, value=value, description=description)
            db.add(setting)
            created += 1
    
    if created > 0:
        await db.commit()
        logger.info(f"Initialized {created} default bot settings")
    
    return created

