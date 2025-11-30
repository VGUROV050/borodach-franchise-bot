"""
Тестовый скрипт для проверки данных из YClients API.
Запуск: python scripts/test_yclients_data.py
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
from datetime import datetime
from pprint import pprint

import httpx

from config.settings import YCLIENTS_PARTNER_TOKEN, YCLIENTS_USER_TOKEN, YCLIENTS_CHAIN_ID
from yclients.client import (
    YClientsAPI, 
    get_chain_companies, 
    get_all_companies_metrics,
    BASE_URL,
)


async def test_raw_analytics():
    """Получить сырые данные аналитики для одного салона."""
    print("\n" + "="*60)
    print("📊 ТЕСТ: Сырые данные аналитики YClients")
    print("="*60)
    
    # Получаем список салонов
    companies = await get_chain_companies()
    if not companies:
        print("❌ Не удалось получить список салонов")
        return
    
    print(f"✅ Найдено {len(companies)} салонов в сети")
    
    # Берём первый активный салон
    company = companies[0]
    company_id = str(company.get("id"))
    company_name = company.get("title", "Unknown")
    
    print(f"\n📍 Тестируем салон: {company_name} (ID: {company_id})")
    
    api = YClientsAPI()
    
    # Текущий месяц
    today = datetime.now()
    date_from = today.replace(day=1).strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    
    print(f"📅 Период: {date_from} — {date_to}")
    
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
        params = {"date_from": date_from, "date_to": date_to}
        
        response = await client.get(url, headers=api.headers, params=params, timeout=30.0)
        
        print(f"\n📥 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                analytics = data.get("data", {})
                
                print("\n📋 Доступные ключи в analytics:")
                for key in sorted(analytics.keys()):
                    print(f"  • {key}")
                
                print("\n📊 Детальные данные:")
                
                # Общая выручка
                income_total = analytics.get("income_total_stats", {})
                print(f"\n💰 income_total_stats:")
                pprint(income_total)
                
                # Выручка по услугам
                income_services = analytics.get("income_services_stats", {})
                print(f"\n💇 income_services_stats:")
                pprint(income_services)
                
                # Выручка по товарам
                income_goods = analytics.get("income_goods_stats", {})
                print(f"\n🛍️ income_goods_stats:")
                pprint(income_goods)
                
                # Средний чек
                income_avg = analytics.get("income_average_stats", {})
                print(f"\n📊 income_average_stats:")
                pprint(income_avg)
                
                # Статистика записей
                record_stats = analytics.get("record_stats", {})
                print(f"\n📋 record_stats:")
                pprint(record_stats)
                
                # Возврат клиентов
                client_return = analytics.get("client_return_stats", {})
                print(f"\n🔄 client_return_stats:")
                pprint(client_return)
                
                # Общая статистика клиентов (ВАЖНО!)
                client_stats = analytics.get("client_stats", {})
                print(f"\n👥 client_stats:")
                pprint(client_stats)
                
                # Заполненность расписания
                fullness = analytics.get("fullness_stats", {})
                print(f"\n📅 fullness_stats:")
                pprint(fullness)
                
                # Сохраним полный ответ в файл для анализа
                with open("scripts/yclients_response_sample.json", "w", encoding="utf-8") as f:
                    json.dump(analytics, f, ensure_ascii=False, indent=2)
                print("\n💾 Полный ответ сохранён в scripts/yclients_response_sample.json")
                
            else:
                print(f"❌ API вернул success=false")
                pprint(data)
        else:
            print(f"❌ Ошибка API: {response.text[:500]}")


async def test_metrics_parsing():
    """Проверить парсинг метрик для нескольких салонов."""
    print("\n" + "="*60)
    print("📊 ТЕСТ: Парсинг метрик (3 салона)")
    print("="*60)
    
    # Получаем метрики (ограничим 3 салонами для теста)
    companies = await get_chain_companies()
    if not companies:
        print("❌ Нет салонов")
        return
    
    api = YClientsAPI()
    today = datetime.now()
    date_from = today.replace(day=1).strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    
    print(f"📅 Период: {date_from} — {date_to}\n")
    
    async with httpx.AsyncClient() as client:
        for company in companies[:3]:
            company_id = str(company.get("id"))
            company_name = company.get("title", "Unknown")
            
            url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
            params = {"date_from": date_from, "date_to": date_to}
            
            response = await client.get(url, headers=api.headers, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    analytics = data.get("data", {})
                    
                    # Парсим метрики
                    def parse_sum(value):
                        if not value:
                            return 0.0
                        return float(str(value).replace(",", ".").replace(" ", "").replace("\xa0", ""))
                    
                    revenue = parse_sum(analytics.get("income_total_stats", {}).get("current_sum", "0"))
                    services = parse_sum(analytics.get("income_services_stats", {}).get("current_sum", "0"))
                    products = parse_sum(analytics.get("income_goods_stats", {}).get("current_sum", "0"))
                    avg_check = parse_sum(analytics.get("income_average_stats", {}).get("current_sum", "0"))
                    completed = analytics.get("record_stats", {}).get("current_completed_count", 0) or 0
                    repeat_pct = analytics.get("client_return_stats", {}).get("current_percent", 0) or 0
                    
                    print(f"📍 {company_name}")
                    print(f"   💰 Выручка: {revenue:,.0f} ₽")
                    print(f"   💇 Услуги: {services:,.0f} ₽")
                    print(f"   🛍️ Товары: {products:,.0f} ₽")
                    print(f"   📊 Ср.чек: {avg_check:,.0f} ₽")
                    print(f"   📋 Записей: {completed}")
                    print(f"   🔄 Повторные: {repeat_pct}%")
                    print()


async def test_history_availability():
    """Проверить доступность данных за 12 месяцев."""
    print("\n" + "="*60)
    print("📊 ТЕСТ: Доступность данных за 12 месяцев")
    print("="*60)
    
    companies = await get_chain_companies()
    if not companies:
        print("❌ Нет салонов")
        return
    
    company = companies[0]
    company_id = str(company.get("id"))
    company_name = company.get("title", "Unknown")
    
    print(f"📍 Тестируем салон: {company_name}")
    
    api = YClientsAPI()
    
    # Проверяем последние 12 месяцев
    from datetime import timedelta
    
    today = datetime.now()
    results = []
    
    async with httpx.AsyncClient() as client:
        for months_ago in range(12):
            # Вычисляем месяц
            target_date = today.replace(day=1) - timedelta(days=months_ago * 30)
            year = target_date.year
            month = target_date.month
            
            # Первый и последний день месяца
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
            
            date_from = f"{year}-{month:02d}-01"
            date_to = last_day.strftime("%Y-%m-%d")
            
            url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
            params = {"date_from": date_from, "date_to": date_to}
            
            response = await client.get(url, headers=api.headers, params=params, timeout=30.0)
            
            revenue = 0.0
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    analytics = data.get("data", {})
                    income_total = analytics.get("income_total_stats", {})
                    revenue_str = income_total.get("current_sum", "0")
                    if revenue_str:
                        revenue = float(str(revenue_str).replace(",", ".").replace(" ", "").replace("\xa0", ""))
            
            results.append({
                "month": f"{year}-{month:02d}",
                "revenue": revenue,
                "available": revenue > 0,
            })
            
            status = "✅" if revenue > 0 else "❌"
            print(f"  {status} {year}-{month:02d}: {revenue:,.0f} ₽")
    
    available_count = sum(1 for r in results if r["available"])
    print(f"\n📊 Доступно {available_count} из 12 месяцев")


async def test_repeat_visitors_field():
    """Детально проверить поле повторных визитов."""
    print("\n" + "="*60)
    print("📊 ТЕСТ: Поиск поля повторных визитов")
    print("="*60)
    
    companies = await get_chain_companies()
    if not companies:
        print("❌ Нет салонов")
        return
    
    company = companies[0]
    company_id = str(company.get("id"))
    company_name = company.get("title", "Unknown")
    
    print(f"📍 Тестируем салон: {company_name}")
    
    api = YClientsAPI()
    today = datetime.now()
    date_from = today.replace(day=1).strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}/company/{company_id}/analytics/overall/"
        params = {"date_from": date_from, "date_to": date_to}
        
        response = await client.get(url, headers=api.headers, params=params, timeout=30.0)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                analytics = data.get("data", {})
                
                print("\n🔍 ВСЕ ключи и их значения:")
                for key, value in analytics.items():
                    print(f"\n  📦 {key}:")
                    if isinstance(value, dict) and value:
                        pprint(value)
                    elif value:
                        print(f"      {value}")
                    else:
                        print("      (пусто)")


async def main():
    """Запуск всех тестов."""
    print("\n🔧 ТЕСТИРОВАНИЕ ДАННЫХ YCLIENTS")
    print("=" * 60)
    
    await test_raw_analytics()
    await test_repeat_visitors_field()
    await test_metrics_parsing()
    await test_history_availability()
    
    print("\n" + "="*60)
    print("✅ Тестирование завершено")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

