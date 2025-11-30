# YClients API Client

import asyncio
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
async def get_period_revenue(company_id: str, date_from: str, date_to: str) -> dict:
    """
    Получить выручку за произвольный период для филиала.
    
    Args:
        company_id: ID компании в YClients
        date_from: Дата начала в формате YYYY-MM-DD
        date_to: Дата конца в формате YYYY-MM-DD
    
    Returns:
        {
            "success": True/False,
            "revenue": float,
            "completed_count": int,
            "total_count": int,
            "error": str (если ошибка)
        }
    """
    api = YClientsAPI()
    
    try:
        async with httpx.AsyncClient() as client:
            url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
            
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
            
            logger.info(f"YClients period analytics for {company_id} ({date_from} - {date_to}): status={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    analytics = data.get("data", {})
                    
                    # Получаем общую выручку
                    income_stats = analytics.get("income_total_stats", {})
                    revenue_str = income_stats.get("current_sum", "0")
                    revenue = float(revenue_str.replace(",", ".").replace(" ", "") if revenue_str else 0)
                    
                    # Статистика записей
                    record_stats = analytics.get("record_stats", {})
                    completed_count = record_stats.get("current_completed_count", 0)
                    total_count = record_stats.get("current_total_count", 0)
                    
                    return {
                        "success": True,
                        "revenue": revenue,
                        "completed_count": completed_count,
                        "total_count": total_count,
                    }
                else:
                    logger.error(f"YClients period analytics success=false: {data}")
                    return {
                        "success": False,
                        "error": "API вернул success=false",
                    }
            else:
                logger.error(f"YClients period analytics error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Ошибка API: {response.status_code}",
                }
            
    except Exception as e:
        logger.error(f"YClients period exception: {e}")
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


def _parse_yclients_sum(value: str) -> float:
    """Парсит числовое значение из YClients API."""
    if not value:
        return 0.0
    return float(str(value).replace(",", ".").replace(" ", "").replace("\xa0", ""))


async def get_all_companies_metrics(year: int = None, month: int = None) -> list[dict]:
    """
    Получить расширенные метрики всех салонов сети за указанный месяц.
    
    Args:
        year: Год (опционально)
        month: Месяц (опционально)
    
    Returns:
        Список словарей с данными:
        [{
            "company_id": str,
            "company_name": str,
            "revenue": float,           # Общая выручка
            "services_revenue": float,  # Выручка по услугам
            "products_revenue": float,  # Выручка по товарам
            "avg_check": float,         # Средний чек
            "completed_count": int,     # Завершённых записей
            "repeat_visitors_pct": float, # % повторных (пока 0, будет отдельный эндпоинт)
        }, ...]
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
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today
        period_name = "текущий месяц"
    else:
        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        period_name = f"{year}-{month:02d}"
    
    date_from = start_of_month.strftime("%Y-%m-%d")
    date_to = end_date.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching metrics for {len(companies)} companies for {period_name}...")
    
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
                
                metrics = {
                    "company_id": company_id,
                    "company_name": company_name,
                    "revenue": 0.0,
                    "services_revenue": 0.0,
                    "products_revenue": 0.0,
                    "avg_check": 0.0,
                    "completed_count": 0,
                    "repeat_visitors_pct": 0.0,
                    "new_clients_count": 0,
                    "return_clients_count": 0,
                    "total_clients_count": 0,
                    "client_base_return_pct": 0.0,
                }
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        analytics = data.get("data", {})
                        
                        # Общая выручка
                        income_total = analytics.get("income_total_stats", {})
                        metrics["revenue"] = _parse_yclients_sum(income_total.get("current_sum", "0"))
                        
                        # Выручка по услугам (income_services_stats)
                        income_services = analytics.get("income_services_stats", {})
                        metrics["services_revenue"] = _parse_yclients_sum(income_services.get("current_sum", "0"))
                        
                        # Выручка по товарам (income_goods_stats)
                        income_goods = analytics.get("income_goods_stats", {})
                        metrics["products_revenue"] = _parse_yclients_sum(income_goods.get("current_sum", "0"))
                        
                        # Средний чек
                        avg_stats = analytics.get("income_average_stats", {})
                        metrics["avg_check"] = _parse_yclients_sum(avg_stats.get("current_sum", "0"))
                        
                        # Завершённые записи
                        record_stats = analytics.get("record_stats", {})
                        metrics["completed_count"] = record_stats.get("current_completed_count", 0) or 0
                        
                        # Процент повторных визитов из client_stats
                        client_stats = analytics.get("client_stats", {})
                        return_pct = client_stats.get("return_percent", 0)
                        metrics["repeat_visitors_pct"] = float(return_pct) if return_pct else 0.0
                        
                        # Дополнительно: количество новых и вернувшихся клиентов
                        metrics["new_clients_count"] = client_stats.get("new_count", 0) or 0
                        metrics["return_clients_count"] = client_stats.get("return_count", 0) or 0
                        metrics["total_clients_count"] = client_stats.get("total_count", 0) or 0
                        
                        # % возврата клиентской базы = вернувшиеся / всего в базе
                        total_in_base = metrics["total_clients_count"]
                        return_count = metrics["return_clients_count"]
                        if total_in_base > 0:
                            metrics["client_base_return_pct"] = round(return_count / total_in_base * 100, 1)
                        else:
                            metrics["client_base_return_pct"] = 0.0
                
                results.append(metrics)
                
                # Логируем прогресс каждые 20 салонов
                if (i + 1) % 20 == 0:
                    logger.info(f"Processed {i + 1}/{len(companies)} companies")
                
                # Небольшая пауза между запросами (0.3 сек) для защиты API
                await asyncio.sleep(0.3)
                    
            except Exception as e:
                logger.error(f"Error fetching metrics for {company_id}: {e}")
                results.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "revenue": 0.0,
                    "services_revenue": 0.0,
                    "products_revenue": 0.0,
                    "avg_check": 0.0,
                    "completed_count": 0,
                    "repeat_visitors_pct": 0.0,
                    "new_clients_count": 0,
                    "return_clients_count": 0,
                    "total_clients_count": 0,
                    "client_base_return_pct": 0.0,
                })
    
    logger.info(f"Finished fetching metrics for {len(results)} companies")
    return results


# Обратная совместимость
async def get_all_companies_revenue(year: int = None, month: int = None) -> list[dict]:
    """Обёртка для обратной совместимости."""
    metrics = await get_all_companies_metrics(year, month)
    return [
        {
            "company_id": m["company_id"],
            "company_name": m["company_name"],
            "revenue": m["revenue"],
            "avg_check": m["avg_check"],
        }
        for m in metrics
    ]


async def calculate_network_ranking(year: int = None, month: int = None) -> list[dict]:
    """
    Рассчитать рейтинг всех салонов сети по выручке за указанный месяц.
    Учитываются только салоны с выручкой > 0.
    Возвращает расширенные метрики.
    
    Args:
        year: Год (опционально, по умолчанию - текущий месяц)
        month: Месяц (опционально)
    
    Returns:
        Список словарей с рейтингом и метриками (отсортирован по выручке DESC):
        [{
            "company_id": str,
            "company_name": str,
            "revenue": float,
            "services_revenue": float,
            "products_revenue": float,
            "avg_check": float,
            "completed_count": int,
            "repeat_visitors_pct": float,
            "rank": int,
            "total_companies": int,
        }, ...]
    """
    # Получаем метрики всех салонов за указанный месяц
    all_metrics = await get_all_companies_metrics(year, month)
    
    if not all_metrics:
        return []
    
    # Фильтруем салоны с выручкой > 0
    active_companies = [c for c in all_metrics if c["revenue"] > 0]
    
    # Сортируем по выручке (от большей к меньшей)
    sorted_companies = sorted(active_companies, key=lambda x: x["revenue"], reverse=True)
    
    # Присваиваем места (только среди активных салонов)
    total = len(sorted_companies)
    for i, company in enumerate(sorted_companies):
        company["rank"] = i + 1
        company["total_companies"] = total
    
    logger.info(f"Calculated ranking for {total} active companies (filtered from {len(all_metrics)} total)")
    if sorted_companies:
        top = sorted_companies[0]
        logger.info(f"Top company: {top['company_name']} - revenue: {top['revenue']:.0f}, services: {top['services_revenue']:.0f}, products: {top['products_revenue']:.0f}")
    
    return sorted_companies


async def sync_companies_to_db() -> tuple[int, int]:
    """
    Синхронизировать список салонов из YClients в локальную БД.
    Парсит город и регион из названия салона.
    
    Returns:
        Tuple (добавлено, обновлено)
    """
    from admin.analytics import extract_city_from_name, is_millionnik, get_region
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
        
        # Является ли город-миллионник (используем улучшенную функцию)
        is_million_city = is_millionnik(city) if city else False
        
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

