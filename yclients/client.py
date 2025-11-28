# YClients API Client

import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

from config.settings import YCLIENTS_PARTNER_TOKEN, YCLIENTS_USER_TOKEN

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

