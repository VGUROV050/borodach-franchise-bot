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
    Получить выручку за текущий месяц для филиала через записи.
    
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
    
    # Получаем записи через API /records/
    try:
        all_records = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            # Пагинация - получаем все записи
            while True:
                response = await client.get(
                    f"{BASE_URL}/records/{company_id}",
                    headers=api.headers,
                    params={
                        "start_date": date_from,
                        "end_date": date_to,
                        "page": page,
                        "count": 100,  # записей на страницу
                    },
                    timeout=30.0,
                )
                
                logger.info(f"YClients records response for {company_id}, page {page}: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("data", [])
                    
                    if not records:
                        break
                    
                    all_records.extend(records)
                    
                    # Если получили меньше 100, значит это последняя страница
                    if len(records) < 100:
                        break
                    
                    page += 1
                else:
                    logger.error(f"YClients records API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                    }
        
        # Считаем статистику по записям
        total_revenue = 0.0
        completed_count = 0
        
        for record in all_records:
            # Статусы: -1 = отменена, 0 = ожидание, 1 = подтверждена, 2 = пришел/завершена
            attendance = record.get("attendance", 0)
            
            # Считаем только завершённые записи (attendance = 1 или 2, или visit = 1)
            visit = record.get("visit", 0)
            
            if visit == 1 or attendance == 2:
                completed_count += 1
                
                # Суммируем стоимость услуг
                services = record.get("services", [])
                for service in services:
                    cost = float(service.get("cost", 0) or 0)
                    total_revenue += cost
        
        logger.info(f"YClients stats for {company_id}: total_records={len(all_records)}, completed={completed_count}, revenue={total_revenue}")
        
        # Форматируем даты для отображения
        period = f"{start_of_month.strftime('%d.%m.%Y')} — {today.strftime('%d.%m.%Y')}"
        
        return {
            "success": True,
            "revenue": total_revenue,
            "records_count": completed_count,
            "total_records": len(all_records),
            "period": period,
        }
            
    except Exception as e:
        logger.error(f"YClients records exception: {e}")
        return {
            "success": False,
            "error": "Ошибка подключения к YClients",
        }

