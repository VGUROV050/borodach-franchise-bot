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
    
    Returns:
        {
            "success": True/False,
            "revenue": float,
            "records_count": int,
            "period": "Ноябрь 2025",
            "error": str (если ошибка)
        }
    """
    api = YClientsAPI()
    
    # Получаем даты текущего месяца
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Пробуем получить через записи (records) — они содержат стоимость услуг
    records = await api.get_records(company_id, start_of_month, today)
    
    if records is None:
        return {
            "success": False,
            "error": "Не удалось получить данные из YClients",
        }
    
    # Считаем выручку из записей
    total_revenue = 0
    completed_records = 0
    total_records = len(records)
    
    for record in records:
        # attendance: 2 = подтверждён, 1 = пришёл (завершён), 0 = не пришёл, -1 = ожидает
        attendance = record.get("attendance", 0)
        
        # Считаем только завершённые записи (attendance = 1 или 2)
        if attendance >= 1:
            completed_records += 1
            
            # Способ 1: Сумма из услуг
            services = record.get("services", [])
            for service in services:
                # cost — итоговая стоимость, cost_per_unit * amount
                cost = service.get("cost", 0) or service.get("cost_per_unit", 0)
                total_revenue += float(cost)
            
            # Способ 2: Если услуг нет, берём из самой записи
            if not services:
                # Пробуем взять стоимость из записи
                record_cost = record.get("cost", 0) or record.get("price_min", 0)
                total_revenue += float(record_cost)
    
    logger.info(f"YClients stats for {company_id}: total={total_records}, completed={completed_records}, revenue={total_revenue}")
    
    # Название месяца на русском
    months_ru = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    period = f"{months_ru[today.month - 1]} {today.year}"
    
    return {
        "success": True,
        "revenue": total_revenue,
        "records_count": completed_records,
        "total_records": total_records,
        "period": period,
    }

