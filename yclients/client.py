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
    Получить выручку за текущий месяц для филиала через аналитику.
    
    Returns:
        {
            "success": True/False,
            "revenue": float,
            "records_count": int,
            "period": str,
            "error": str (если ошибка)
        }
    """
    api = YClientsAPI()
    
    # Получаем даты текущего месяца
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Форматируем даты
    date_from = start_of_month.strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    
    # Получаем аналитику через API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/company/{company_id}/analytics/overall/",
                headers=api.headers,
                params={
                    "date_from": date_from,
                    "date_to": date_to,
                },
                timeout=30.0,
            )
            
            logger.info(f"YClients analytics response for {company_id}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                analytics = data.get("data", {})
                
                # Суммарный доход из аналитики
                total_revenue = float(analytics.get("total_income", 0) or 0)
                # Количество записей
                records_count = int(analytics.get("records_count", 0) or 0)
                # Завершённые записи
                completed_count = int(analytics.get("records_completed", 0) or analytics.get("visits_count", 0) or 0)
                
                logger.info(f"YClients analytics for {company_id}: revenue={total_revenue}, records={records_count}, completed={completed_count}")
                
                # Форматируем даты для отображения
                period = f"{start_of_month.strftime('%d.%m.%Y')} — {today.strftime('%d.%m.%Y')}"
                
                return {
                    "success": True,
                    "revenue": total_revenue,
                    "records_count": completed_count,
                    "total_records": records_count,
                    "period": period,
                }
            else:
                logger.error(f"YClients analytics API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Ошибка API: {response.status_code}",
                }
    except Exception as e:
        logger.error(f"YClients analytics exception: {e}")
        return {
            "success": False,
            "error": "Ошибка подключения к YClients",
        }

