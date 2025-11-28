# YClients API Client

import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from config.settings import YCLIENTS_PARTNER_TOKEN, YCLIENTS_USER_TOKEN, YCLIENTS_CHAIN_ID

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
    
    
    async def get_company_info(self, company_id: str) -> Optional[dict]:
        """Получить информацию о компании/филиале."""
        try:
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
        except Exception as e:
            logger.error(f"YClients API exception: {e}")
            return None
    
    async def get_finance_transactions(
        self, 
        company_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[list]:
        """Получить финансовые транзакции за период."""
        try:
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
        except Exception as e:
            logger.error(f"YClients finance API exception: {e}")
            return None
    
    async def get_records(
        self,
        company_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[list]:
        """Получить записи (визиты) за период."""
        try:
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
        except Exception as e:
            logger.error(f"YClients records API exception: {e}")
            return None


async def get_monthly_revenue(company_id: str) -> dict:
    """
    Получить выручку за текущий месяц для филиала.
    Использует эндпоинт /company/{id}/analytics/overall/
    
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
    
    # Получаем даты текущего месяца
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    date_from = start_of_month.strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    period = f"{start_of_month.strftime('%d.%m.%Y')} — {today.strftime('%d.%m.%Y')}"
    
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


async def get_all_companies_revenue() -> list[dict]:
    """
    Получить выручку всех салонов сети за текущий месяц.
    
    Returns:
        Список словарей с данными:
        [{"company_id": "123", "company_name": "Салон 1", "revenue": 123456.0}, ...]
    """
    # Получаем список салонов сети
    companies = await get_chain_companies()
    
    if not companies:
        logger.error("No companies found in chain")
        return []
    
    results = []
    api = YClientsAPI()
    
    # Получаем даты текущего месяца
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    date_from = start_of_month.strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching revenue for {len(companies)} companies...")
    
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
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        analytics = data.get("data", {})
                        income_stats = analytics.get("income_total_stats", {})
                        revenue_str = income_stats.get("current_sum", "0")
                        revenue = float(revenue_str.replace(",", ".").replace(" ", "") if revenue_str else 0)
                
                results.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "revenue": revenue,
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
                })
    
    logger.info(f"Finished fetching revenue for {len(results)} companies")
    return results


async def calculate_network_ranking() -> list[dict]:
    """
    Рассчитать рейтинг всех салонов сети по выручке.
    
    Returns:
        Список словарей с рейтингом (отсортирован по выручке DESC):
        [{"company_id": "123", "company_name": "Салон 1", "revenue": 123456.0, "rank": 1}, ...]
    """
    # Получаем выручку всех салонов
    all_revenue = await get_all_companies_revenue()
    
    if not all_revenue:
        return []
    
    # Сортируем по выручке (от большей к меньшей)
    sorted_companies = sorted(all_revenue, key=lambda x: x["revenue"], reverse=True)
    
    # Присваиваем места
    total = len(sorted_companies)
    for i, company in enumerate(sorted_companies):
        company["rank"] = i + 1
        company["total_companies"] = total
    
    logger.info(f"Calculated ranking for {total} companies. Top 3: {sorted_companies[:3]}")
    
    return sorted_companies

