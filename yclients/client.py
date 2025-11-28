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
    
    async def test_endpoint(self, endpoint: str, params: dict = None) -> dict:
        """Тестовый запрос к любому эндпоинту для отладки."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BASE_URL}{endpoint}",
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                logger.info(f"YClients [{endpoint}] status={response.status_code}")
                logger.info(f"YClients [{endpoint}] response: {response.text[:1000]}")
                return {
                    "status": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text if response.status_code != 200 else None,
                }
        except Exception as e:
            logger.error(f"YClients [{endpoint}] exception: {e}")
            return {"status": 0, "error": str(e)}
    
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
    Тестируем несколько эндпоинтов чтобы найти рабочий.
    
    Returns:
        {
            "success": True/False,
            "revenue": float,
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
            # ═══════════════════════════════════════════════════════════════
            # Пробуем эндпоинт: /finance_transactions/{company_id}
            # ═══════════════════════════════════════════════════════════════
            logger.info(f"Testing /finance_transactions/{company_id}")
            resp1 = await client.get(
                f"{BASE_URL}/finance_transactions/{company_id}",
                headers=api.headers,
                params={"start_date": date_from, "end_date": date_to},
                timeout=30.0,
            )
            logger.info(f"finance_transactions: status={resp1.status_code}, body={resp1.text[:500]}")
            
            if resp1.status_code == 200:
                data = resp1.json()
                transactions = data.get("data", [])
                if transactions:
                    # Считаем сумму приходных транзакций
                    total = sum(
                        float(t.get("amount", 0) or 0) 
                        for t in transactions 
                        if t.get("type") in [1, "income", "приход"]  # тип = приход
                    )
                    if total > 0:
                        return {"success": True, "revenue": total, "period": period, "source": "finance_transactions"}
            
            # ═══════════════════════════════════════════════════════════════
            # Пробуем эндпоинт: /company/{company_id}/finance/report
            # ═══════════════════════════════════════════════════════════════
            logger.info(f"Testing /company/{company_id}/finance/report")
            resp2 = await client.get(
                f"{BASE_URL}/company/{company_id}/finance/report",
                headers=api.headers,
                params={"start_date": date_from, "end_date": date_to},
                timeout=30.0,
            )
            logger.info(f"finance/report: status={resp2.status_code}, body={resp2.text[:500]}")
            
            if resp2.status_code == 200:
                data = resp2.json()
                revenue = data.get("data", {}).get("revenue") or data.get("data", {}).get("income") or data.get("data", {}).get("total")
                if revenue:
                    return {"success": True, "revenue": float(revenue), "period": period, "source": "finance/report"}
            
            # ═══════════════════════════════════════════════════════════════
            # Пробуем эндпоинт: /timetable/seances/{company_id} (сеансы с оплатой)
            # ═══════════════════════════════════════════════════════════════
            logger.info(f"Testing /timetable/seances/{company_id}")
            resp3 = await client.get(
                f"{BASE_URL}/timetable/seances/{company_id}",
                headers=api.headers,
                params={"date_from": date_from, "date_to": date_to},
                timeout=30.0,
            )
            logger.info(f"timetable/seances: status={resp3.status_code}, body={resp3.text[:500]}")
            
            # ═══════════════════════════════════════════════════════════════
            # Пробуем эндпоинт: /activity/{company_id}/search (посещения)
            # ═══════════════════════════════════════════════════════════════
            logger.info(f"Testing /activity/{company_id}/search")
            resp4 = await client.post(
                f"{BASE_URL}/activity/{company_id}/search",
                headers=api.headers,
                json={"from": date_from, "to": date_to},
                timeout=30.0,
            )
            logger.info(f"activity/search: status={resp4.status_code}, body={resp4.text[:500]}")
            
            # ═══════════════════════════════════════════════════════════════
            # Пробуем эндпоинт: /records/{company_id} и считаем вручную
            # ═══════════════════════════════════════════════════════════════
            logger.info(f"Testing /records/{company_id} with manual calculation")
            
            all_records = []
            page = 1
            
            while page <= 10:  # максимум 10 страниц для безопасности
                resp5 = await client.get(
                    f"{BASE_URL}/records/{company_id}",
                    headers=api.headers,
                    params={
                        "start_date": date_from,
                        "end_date": date_to,
                        "page": page,
                        "count": 200,
                    },
                    timeout=30.0,
                )
                
                if resp5.status_code != 200:
                    logger.error(f"records error: {resp5.status_code} - {resp5.text}")
                    break
                
                data = resp5.json()
                records = data.get("data", [])
                
                if not records:
                    break
                
                all_records.extend(records)
                
                if len(records) < 200:
                    break
                page += 1
            
            # Логируем структуру первой записи
            if all_records:
                logger.info(f"First record FULL: {all_records[0]}")
            
            # Считаем выручку по завершённым записям
            total_revenue = 0.0
            completed = 0
            
            for rec in all_records:
                # Проверяем статус: клиент пришёл
                # attendance: 2 = пришёл, visit: 1 = пришёл
                attendance = rec.get("attendance", 0)
                visit = rec.get("visit", 0)
                
                if attendance == 2 or visit == 1:
                    completed += 1
                    
                    # Пробуем разные поля для суммы
                    # 1. services[].cost
                    services = rec.get("services", [])
                    for svc in services:
                        cost = float(svc.get("cost", 0) or 0)
                        total_revenue += cost
                    
                    # 2. Если services пусто - пробуем поле самой записи
                    if not services:
                        total_revenue += float(rec.get("cost", 0) or 0)
                        total_revenue += float(rec.get("cost_to_pay", 0) or 0)
                        total_revenue += float(rec.get("paid_full", 0) or 0)
            
            logger.info(f"Records calculation: total={len(all_records)}, completed={completed}, revenue={total_revenue}")
            
            return {
                "success": True,
                "revenue": total_revenue,
                "period": period,
                "source": "records_manual",
                "total_records": len(all_records),
                "completed": completed,
            }
            
    except Exception as e:
        logger.error(f"YClients exception: {e}")
        return {
            "success": False,
            "error": str(e),
        }

