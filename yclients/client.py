# YClients API Client

import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from config.settings import YCLIENTS_PARTNER_TOKEN, YCLIENTS_USER_TOKEN, YCLIENTS_CHAIN_ID
from utils.retry import api_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.yclients.com/api/v1"


class YClientsAPI:
    """Клиент для работы с YClients API."""
    
    def __init__(self, partner_token: str = None, user_token: str = None):
        self.partner_token = partner_token or YCLIENTS_PARTNER_TOKEN
        self.user_token = user_token or YCLIENTS_USER_TOKEN
        
        # Формируем заголовок авторизации
        # YClients требует: Bearer PARTNER_TOKEN, User USER_TOKEN
        if self.user_token:
            auth_header = f"Bearer {self.partner_token}, User {self.user_token}"
        else:
            auth_header = f"Bearer {self.partner_token}"
        
        self.headers = {
            "Authorization": auth_header,
            "Accept": "application/vnd.api.v2+json",
            "Content-Type": "application/json",
        }
    
    
    @api_retry(max_attempts=3, min_wait=1, max_wait=10)
    async def get_company_info(self, company_id: str) -> Optional[dict]:
        """Получить информацию о компании/филиале."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/company/{company_id}",
                headers=self.headers,
                timeout=30.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data")
            else:
                logger.error(f"YClients API error: {response.status_code} - {response.text}")
                return None
    
    @api_retry(max_attempts=3, min_wait=1, max_wait=10)
    async def get_finance_transactions(
        self, 
        company_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[list]:
        """Получить финансовые транзакции за период."""
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/company/{company_id}/finance/transactions",
                headers=self.headers,
                params=params,
                timeout=30.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                logger.error(f"YClients finance API error: {response.status_code} - {response.text}")
                return None
    
    @api_retry(max_attempts=3, min_wait=1, max_wait=10)
    async def get_records(
        self,
        company_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[list]:
        """Получить записи (визиты) за период."""
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/records/{company_id}",
                headers=self.headers,
                params=params,
                timeout=30.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                logger.error(f"YClients records API error: {response.status_code} - {response.text}")
                return None


@api_retry(max_attempts=3, min_wait=1, max_wait=10)
async def get_monthly_revenue(company_id: str, year: int = None, month: int = None) -> dict:
    """
    Получить выручку за указанный месяц для филиала.
    Если год/месяц не указаны - берётся текущий месяц.
    Использует эндпоинт /company/{id}/analytics/overall/
    
    Args:
        company_id: ID компании в YClients
        year: Год (опционально, по умолчанию - текущий)
        month: Месяц (опционально, по умолчанию - текущий)
    
    Returns:
        {
            "success": True/False,
            "revenue": float,
            "completed_count": int,
            "period": str,
            "error": str (если ошибка)
        }
    """
    api = YClientsAPI()
    
    # Определяем даты
    today = datetime.now()
    
    if year is None or month is None:
        # Текущий месяц (неполный)
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today
    else:
        # Указанный месяц (полный)
        start_of_month = datetime(year, month, 1)
        # Конец месяца - последний день
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    date_from = start_of_month.strftime("%Y-%m-%d")
    date_to = end_date.strftime("%Y-%m-%d")
    period = f"{start_of_month.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}"
    
    try:
        async with httpx.AsyncClient() as client:
            # Эндпоинт аналитики: /company/{company_id}/analytics/overall/
            url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
            
            # Параметры периода
            params = {
                "date_from": date_from,
                "date_to": date_to,
            }
            
            response = await client.get(
                url,
                headers=api.headers,
                params=params,
                timeout=30.0,
            )
            
            logger.info(f"YClients analytics for {company_id}: status={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    analytics = data.get("data", {})
                    
                    # Получаем общую выручку из income_total_stats
                    income_stats = analytics.get("income_total_stats", {})
                    revenue_str = income_stats.get("current_sum", "0")
                    revenue = float(revenue_str.replace(",", ".").replace(" ", "") if revenue_str else 0)
                    
                    # Получаем статистику записей
                    record_stats = analytics.get("record_stats", {})
                    completed_count = record_stats.get("current_completed_count", 0)
                    total_count = record_stats.get("current_total_count", 0)
                    
                    return {
                        "success": True,
                        "revenue": revenue,
                        "completed_count": completed_count,
                        "total_count": total_count,
                        "period": period,
                    }
                else:
                    logger.error(f"YClients analytics success=false: {data}")
                    return {
                        "success": False,
                        "error": "API вернул success=false",
                    }
            else:
                logger.error(f"YClients analytics error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Ошибка API: {response.status_code}",
                }
            
    except Exception as e:
        logger.error(f"YClients exception: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@api_retry(max_attempts=3, min_wait=2, max_wait=15)
async def get_chain_companies(chain_id: str = None) -> list[dict]:
    """
    Получить список всех салонов в сети.
    
    Returns:
        Список словарей с информацией о салонах:
        [{"id": "123", "title": "Салон 1"}, ...]
    """
    chain_id = chain_id or YCLIENTS_CHAIN_ID
    api = YClientsAPI()
    
    try:
        async with httpx.AsyncClient() as client:
            # Эндпоинт для получения доступных сетей (с салонами внутри)
            url = f"{BASE_URL}/groups"
            
            response = await client.get(
                url,
                headers=api.headers,
                timeout=60.0,
            )
            
            logger.info(f"YClients groups: status={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    groups = data.get("data", [])
                    
                    # Ищем нужную сеть по ID
                    for group in groups:
                        if str(group.get("id")) == str(chain_id):
                            companies = group.get("companies", [])
                            logger.info(f"Found {len(companies)} companies in group {chain_id}")
                            return companies
                    
                    # Если не нашли по ID, берём первую сеть
                    if groups:
                        companies = groups[0].get("companies", [])
                        logger.info(f"Using first group, found {len(companies)} companies")
                        return companies
                    
                    logger.error(f"No groups found")
                    return []
                else:
                    logger.error(f"YClients groups error: {data}")
                    return []
            else:
                logger.error(f"YClients groups error: {response.status_code} - {response.text}")
                return []
                
    except Exception as e:
        logger.error(f"YClients groups exception: {e}")
        return []


async def get_all_companies_revenue(year: int = None, month: int = None) -> list[dict]:
    """
    Получить выручку всех салонов сети за указанный месяц.
    Если год/месяц не указаны - берётся текущий месяц (неполный).
    
    Args:
        year: Год (опционально)
        month: Месяц (опционально)
    
    Returns:
        Список словарей с данными:
        [{"company_id": "123", "company_name": "Салон 1", "revenue": 123456.0, "avg_check": 1500.0}, ...]
    """
    # Получаем список салонов сети
    companies = await get_chain_companies()
    
    if not companies:
        logger.error("No companies found in chain")
        return []
    
    results = []
    api = YClientsAPI()
    
    # Определяем даты
    today = datetime.now()
    
    if year is None or month is None:
        # Текущий месяц (неполный)
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today
        period_name = "текущий месяц"
    else:
        # Указанный месяц (полный)
        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        period_name = f"{year}-{month:02d}"
    
    date_from = start_of_month.strftime("%Y-%m-%d")
    date_to = end_date.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching revenue for {len(companies)} companies for {period_name}...")
    
    async with httpx.AsyncClient() as client:
        for i, company in enumerate(companies):
            company_id = str(company.get("id"))
            company_name = company.get("title", f"Салон {company_id}")
            
            try:
                url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
                params = {"date_from": date_from, "date_to": date_to}
                
                response = await client.get(
                    url,
                    headers=api.headers,
                    params=params,
                    timeout=30.0,
                )
                
                revenue = 0.0
                avg_check = 0.0
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        analytics = data.get("data", {})
                        
                        # Общая выручка
                        income_stats = analytics.get("income_total_stats", {})
                        revenue_str = income_stats.get("current_sum", "0")
                        revenue = float(revenue_str.replace(",", ".").replace(" ", "") if revenue_str else 0)
                        
                        # Средний чек
                        avg_stats = analytics.get("income_average_stats", {})
                        avg_str = avg_stats.get("current_sum", "0")
                        avg_check = float(avg_str.replace(",", ".").replace(" ", "") if avg_str else 0)
                
                results.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "revenue": revenue,
                    "avg_check": avg_check,
                })
                
                # Логируем прогресс каждые 20 салонов
                if (i + 1) % 20 == 0:
                    logger.info(f"Processed {i + 1}/{len(companies)} companies")
                    
            except Exception as e:
                logger.error(f"Error fetching revenue for {company_id}: {e}")
                results.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "revenue": 0.0,
                    "avg_check": 0.0,
                })
    
    logger.info(f"Finished fetching revenue for {len(results)} companies")
    return results


async def calculate_network_ranking(year: int = None, month: int = None) -> list[dict]:
    """
    Рассчитать рейтинг всех салонов сети по выручке за указанный месяц.
    Учитываются только салоны с выручкой > 0.
    
    Args:
        year: Год (опционально, по умолчанию - текущий месяц)
        month: Месяц (опционально)
    
    Returns:
        Список словарей с рейтингом (отсортирован по выручке DESC):
        [{"company_id": "123", "company_name": "Салон 1", "revenue": 123456.0, "avg_check": 1500.0, "rank": 1}, ...]
    """
    # Получаем выручку всех салонов за указанный месяц
    all_revenue = await get_all_companies_revenue(year, month)
    
    if not all_revenue:
        return []
    
    # Фильтруем салоны с выручкой > 0
    active_companies = [c for c in all_revenue if c["revenue"] > 0]
    
    # Сортируем по выручке (от большей к меньшей)
    sorted_companies = sorted(active_companies, key=lambda x: x["revenue"], reverse=True)
    
    # Присваиваем места (только среди активных салонов)
    total = len(sorted_companies)
    for i, company in enumerate(sorted_companies):
        company["rank"] = i + 1
        company["total_companies"] = total
    
    logger.info(f"Calculated ranking for {total} active companies (filtered from {len(all_revenue)} total). Top 3: {sorted_companies[:3]}")
    
    return sorted_companies


async def sync_companies_to_db() -> tuple[int, int]:
    """
    Синхронизировать список салонов из YClients в локальную БД.
    Парсит город и регион из названия салона.
    
    Returns:
        Tuple (добавлено, обновлено)
    """
    from admin.analytics import extract_city_from_name, MILLIONNIKI, get_region
    from database import AsyncSessionLocal, sync_yclients_companies
    
    # Получаем список салонов из YClients
    companies = await get_chain_companies()
    
    if not companies:
        logger.error("No companies found to sync")
        return 0, 0
    
    logger.info(f"Syncing {len(companies)} companies to database...")
    
    # Подготавливаем данные с парсингом города
    companies_data = []
    for company in companies:
        name = company.get("title", "")
        yclients_id = str(company.get("id"))
        
        # Парсим город из названия
        city = extract_city_from_name(name)
        
        # Определяем регион
        region = get_region(city) if city else None
        
        # Является ли город-миллионник
        is_million_city = city.lower().strip() in MILLIONNIKI if city else False
        
        companies_data.append({
            "id": yclients_id,
            "title": name,
            "city": city,
            "region": region,
            "is_million_city": is_million_city,
        })
    
    # Сохраняем в БД
    async with AsyncSessionLocal() as db:
        added, updated = await sync_yclients_companies(db, companies_data)
    
    logger.info(f"Sync complete: {added} added, {updated} updated")
    return added, updated

