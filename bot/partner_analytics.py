"""
Аналитика данных партнёра для AI-ассистента.
Получение метрик, сравнение с сетью, формирование контекста.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from database import AsyncSessionLocal
from database.crud import (
    get_partner_by_telegram_id,
    get_partner_companies,
    get_network_rating_by_company,
    get_city_average,
    get_similar_cities_average,
    get_company_history_12m,
)
from database.models import NetworkRating, NetworkRatingHistory, YClientsCompany

logger = logging.getLogger(__name__)


@dataclass
class TrendData:
    """Данные о тренде метрики."""
    current: float
    previous: float  # Прошлый месяц
    months_ago_3: float  # 3 месяца назад
    months_ago_6: float  # 6 месяцев назад
    
    @property
    def change_1m_pct(self) -> float:
        """Изменение за 1 месяц в %."""
        if self.previous > 0:
            return round((self.current / self.previous - 1) * 100, 1)
        return 0.0
    
    @property
    def change_3m_pct(self) -> float:
        """Изменение за 3 месяца в %."""
        if self.months_ago_3 > 0:
            return round((self.current / self.months_ago_3 - 1) * 100, 1)
        return 0.0
    
    @property
    def change_6m_pct(self) -> float:
        """Изменение за 6 месяцев в %."""
        if self.months_ago_6 > 0:
            return round((self.current / self.months_ago_6 - 1) * 100, 1)
        return 0.0
    
    @property
    def trend_emoji(self) -> str:
        """Эмодзи тренда за 3 месяца."""
        if self.change_3m_pct > 10:
            return "📈"
        elif self.change_3m_pct < -10:
            return "📉"
        else:
            return "➡️"


@dataclass
class CompanyTrends:
    """Тренды метрик салона."""
    company_id: str
    company_name: str
    
    revenue: Optional[TrendData] = None
    avg_check: Optional[TrendData] = None
    completed_count: Optional[TrendData] = None
    repeat_visitors_pct: Optional[TrendData] = None
    client_base_return_pct: Optional[TrendData] = None
    
    # История рангов
    rank_history: list[tuple[str, int]] = None  # [(период, ранг), ...]
    
    def __post_init__(self):
        if self.rank_history is None:
            self.rank_history = []


@dataclass
class CompanyMetrics:
    """Метрики одного салона с сравнением."""
    company_id: str
    company_name: str
    city: str
    is_million_city: bool
    
    # Текущие метрики
    revenue: float
    services_revenue: float
    products_revenue: float
    avg_check: float
    completed_count: int
    repeat_visitors_pct: float
    new_clients_count: int
    return_clients_count: int
    total_clients_count: int
    client_base_return_pct: float
    rank: int
    total_companies: int
    
    # Сравнение с городом
    city_avg_revenue: float = 0.0
    city_avg_check: float = 0.0
    city_avg_repeat_pct: float = 0.0
    city_company_count: int = 0
    
    # Сравнение с похожими городами (миллионники/регионы)
    similar_avg_revenue: float = 0.0
    similar_avg_check: float = 0.0
    similar_avg_repeat_pct: float = 0.0
    
    @property
    def revenue_vs_city_pct(self) -> float:
        """Отклонение выручки от среднего по городу в %."""
        if self.city_avg_revenue > 0:
            return round((self.revenue / self.city_avg_revenue - 1) * 100, 1)
        return 0.0
    
    @property
    def check_vs_city_pct(self) -> float:
        """Отклонение среднего чека от города в %."""
        if self.city_avg_check > 0:
            return round((self.avg_check / self.city_avg_check - 1) * 100, 1)
        return 0.0
    
    @property
    def repeat_vs_city_diff(self) -> float:
        """Разница % повторных от города."""
        return round(self.repeat_visitors_pct - self.city_avg_repeat_pct, 1)


@dataclass
class PartnerAnalytics:
    """Полная аналитика партнёра."""
    partner_id: int
    partner_name: str
    companies: list[CompanyMetrics]
    
    @property
    def total_revenue(self) -> float:
        return sum(c.revenue for c in self.companies)
    
    @property
    def avg_rank(self) -> float:
        if not self.companies:
            return 0
        return sum(c.rank for c in self.companies) / len(self.companies)
    
    @property
    def best_company(self) -> Optional[CompanyMetrics]:
        if not self.companies:
            return None
        return min(self.companies, key=lambda c: c.rank)
    
    @property
    def worst_company(self) -> Optional[CompanyMetrics]:
        if not self.companies:
            return None
        return max(self.companies, key=lambda c: c.rank)


async def get_partner_analytics(telegram_id: int) -> Optional[PartnerAnalytics]:
    """
    Получить полную аналитику партнёра с сравнением по сети.
    
    Args:
        telegram_id: Telegram ID партнёра
    
    Returns:
        PartnerAnalytics или None если партнёр не найден
    """
    async with AsyncSessionLocal() as db:
        # Получаем партнёра
        partner = await get_partner_by_telegram_id(db, telegram_id)
        if not partner:
            logger.warning(f"Partner not found for telegram_id={telegram_id}")
            return None
        
        # Получаем салоны партнёра
        companies = await get_partner_companies(db, partner.id)
        if not companies:
            logger.info(f"Partner {partner.id} has no companies linked")
            return PartnerAnalytics(
                partner_id=partner.id,
                partner_name=partner.full_name,
                companies=[],
            )
        
        # Собираем метрики по каждому салону
        company_metrics = []
        
        for company in companies:
            # Получаем рейтинг салона
            rating = await get_network_rating_by_company(db, company.yclients_id)
            
            if not rating:
                logger.warning(f"No rating found for company {company.yclients_id}")
                continue
            
            # Получаем средние по городу
            city_avg = {"company_count": 0, "avg_revenue": 0, "avg_check": 0, "avg_repeat_visitors_pct": 0}
            if rating.city:
                city_avg = await get_city_average(db, rating.city)
            
            # Получаем средние по похожим городам
            similar_avg = await get_similar_cities_average(db, rating.is_million_city)
            
            metrics = CompanyMetrics(
                company_id=company.yclients_id,
                company_name=company.name,
                city=rating.city or "Неизвестно",
                is_million_city=rating.is_million_city,
                
                revenue=rating.revenue,
                services_revenue=rating.services_revenue,
                products_revenue=rating.products_revenue,
                avg_check=rating.avg_check,
                completed_count=rating.completed_count,
                repeat_visitors_pct=rating.repeat_visitors_pct,
                new_clients_count=rating.new_clients_count,
                return_clients_count=rating.return_clients_count,
                total_clients_count=rating.total_clients_count,
                client_base_return_pct=rating.client_base_return_pct,
                rank=rating.rank,
                total_companies=rating.total_companies,
                
                city_avg_revenue=city_avg.get("avg_revenue", 0),
                city_avg_check=city_avg.get("avg_check", 0),
                city_avg_repeat_pct=city_avg.get("avg_repeat_visitors_pct", 0),
                city_company_count=city_avg.get("company_count", 0),
                
                similar_avg_revenue=similar_avg.get("avg_revenue", 0),
                similar_avg_check=similar_avg.get("avg_check", 0),
                similar_avg_repeat_pct=similar_avg.get("avg_repeat_visitors_pct", 0),
            )
            
            company_metrics.append(metrics)
        
        return PartnerAnalytics(
            partner_id=partner.id,
            partner_name=partner.full_name,
            companies=company_metrics,
        )


def format_analytics_for_ai(analytics: PartnerAnalytics) -> str:
    """
    Форматировать аналитику партнёра для передачи в AI.
    
    Returns:
        Текст с данными партнёра для контекста AI
    """
    if not analytics.companies:
        return "У партнёра пока нет привязанных салонов."
    
    lines = [
        f"📊 ДАННЫЕ ПАРТНЁРА: {analytics.partner_name}",
        f"Салонов: {len(analytics.companies)}",
        f"Общая выручка: {analytics.total_revenue:,.0f} ₽",
        "",
    ]
    
    for c in analytics.companies:
        # Определяем статус относительно города
        revenue_status = "🟢" if c.revenue_vs_city_pct >= 0 else "🔴"
        check_status = "🟢" if c.check_vs_city_pct >= 0 else "🔴"
        repeat_status = "🟢" if c.repeat_vs_city_diff >= 0 else "🔴"
        
        lines.extend([
            f"━━━ {c.company_name} ━━━",
            f"📍 Город: {c.city} ({'миллионник' if c.is_million_city else 'регион'})",
            f"🏆 Место в сети: {c.rank} из {c.total_companies}",
            "",
            f"💰 Выручка: {c.revenue:,.0f} ₽",
            f"   {revenue_status} vs город: {c.revenue_vs_city_pct:+.1f}% (среднее {c.city_avg_revenue:,.0f} ₽)",
            "",
            f"📊 Средний чек: {c.avg_check:,.0f} ₽",
            f"   {check_status} vs город: {c.check_vs_city_pct:+.1f}% (среднее {c.city_avg_check:,.0f} ₽)",
            "",
            f"🔄 Повторные визиты: {c.repeat_visitors_pct:.1f}%",
            f"   {repeat_status} vs город: {c.repeat_vs_city_diff:+.1f}% (среднее {c.city_avg_repeat_pct:.1f}%)",
            "",
            f"👥 Клиенты: {c.new_clients_count} новых, {c.return_clients_count} вернулись",
            f"📋 Записей: {c.completed_count}",
            f"💇 Услуги: {c.services_revenue:,.0f} ₽ | 🛍️ Товары: {c.products_revenue:,.0f} ₽",
            "",
        ])
    
    return "\n".join(lines)


def get_partner_issues(analytics: PartnerAnalytics) -> list[str]:
    """
    Определить проблемные зоны партнёра.
    
    Returns:
        Список проблем для анализа AI
    """
    issues = []
    
    for c in analytics.companies:
        prefix = f"{c.company_name}: "
        
        # Выручка ниже среднего
        if c.revenue_vs_city_pct < -20:
            issues.append(f"{prefix}Выручка на {abs(c.revenue_vs_city_pct):.0f}% ниже среднего по городу")
        
        # Низкий средний чек
        if c.check_vs_city_pct < -15:
            issues.append(f"{prefix}Средний чек на {abs(c.check_vs_city_pct):.0f}% ниже среднего")
        
        # Мало повторных визитов
        if c.repeat_visitors_pct < 50:
            issues.append(f"{prefix}Низкий % повторных визитов ({c.repeat_visitors_pct:.0f}%)")
        
        # Низкий возврат базы
        if c.client_base_return_pct < 10:
            issues.append(f"{prefix}Низкий возврат клиентской базы ({c.client_base_return_pct:.1f}%)")
        
        # Низкий ранг
        if c.rank > c.total_companies * 0.7:
            issues.append(f"{prefix}Салон в нижней трети рейтинга ({c.rank} из {c.total_companies})")
        
        # Мало продаж товаров
        if c.revenue > 0 and c.products_revenue / c.revenue < 0.05:
            issues.append(f"{prefix}Низкая доля товаров в выручке ({c.products_revenue / c.revenue * 100:.1f}%)")
    
    return issues


def get_partner_strengths(analytics: PartnerAnalytics) -> list[str]:
    """
    Определить сильные стороны партнёра.
    
    Returns:
        Список сильных сторон
    """
    strengths = []
    
    for c in analytics.companies:
        prefix = f"{c.company_name}: "
        
        # Высокая выручка
        if c.revenue_vs_city_pct > 20:
            strengths.append(f"{prefix}Выручка на {c.revenue_vs_city_pct:.0f}% выше среднего по городу")
        
        # Высокий чек
        if c.check_vs_city_pct > 15:
            strengths.append(f"{prefix}Средний чек на {c.check_vs_city_pct:.0f}% выше среднего")
        
        # Хороший возврат
        if c.repeat_visitors_pct >= 65:
            strengths.append(f"{prefix}Отличный % повторных визитов ({c.repeat_visitors_pct:.0f}%)")
        
        # Топ рейтинга
        if c.rank <= 10:
            strengths.append(f"{prefix}В топ-10 сети!")
        elif c.rank <= c.total_companies * 0.2:
            strengths.append(f"{prefix}В топ-20% сети ({c.rank} место)")
    
    return strengths


async def get_company_trends(yclients_id: str, current_metrics: CompanyMetrics) -> Optional[CompanyTrends]:
    """
    Получить тренды метрик салона за последние месяцы.
    
    Args:
        yclients_id: ID салона в YClients
        current_metrics: Текущие метрики салона
    
    Returns:
        CompanyTrends или None
    """
    from datetime import datetime
    
    async with AsyncSessionLocal() as db:
        history = await get_company_history_12m(db, yclients_id)
    
    if not history:
        return None
    
    # Сортируем по дате (от новых к старым)
    sorted_history = sorted(history, key=lambda h: (h.year, h.month), reverse=True)
    
    # Получаем данные за разные периоды
    now = datetime.now()
    
    def get_history_for_months_ago(months: int) -> Optional[NetworkRatingHistory]:
        """Найти запись за N месяцев назад."""
        target_total = now.year * 12 + now.month - months
        target_year = target_total // 12
        target_month = target_total % 12 or 12
        if target_month == 0:
            target_month = 12
            target_year -= 1
        
        for h in sorted_history:
            if h.year == target_year and h.month == target_month:
                return h
        return None
    
    # Если в начале месяца (первые 7 дней) — используем прошлый месяц как "текущий"
    # чтобы не сравнивать неполный месяц с полным
    use_previous_as_current = now.day <= 7
    
    if use_previous_as_current:
        # Сдвигаем все периоды на 1 месяц назад
        prev_month = get_history_for_months_ago(1)  # Это будет "текущий"
        months_2 = get_history_for_months_ago(2)    # Это будет "прошлый"
        months_4 = get_history_for_months_ago(4)    # 3 месяца назад от "текущего"
        months_7 = get_history_for_months_ago(7)    # 6 месяцев назад от "текущего"
        
        # Используем данные из истории
        current_revenue = prev_month.revenue if prev_month else 0
        current_avg_check = prev_month.avg_check if prev_month else 0
        current_completed = float(prev_month.completed_count) if prev_month else 0
        current_repeat_pct = prev_month.repeat_visitors_pct if prev_month else 0
        
        prev_revenue = months_2.revenue if months_2 else 0
        prev_avg_check = months_2.avg_check if months_2 else 0
        prev_completed = float(months_2.completed_count) if months_2 else 0
        prev_repeat_pct = months_2.repeat_visitors_pct if months_2 else 0
        
        m3_revenue = months_4.revenue if months_4 else 0
        m3_avg_check = months_4.avg_check if months_4 else 0
        m3_completed = float(months_4.completed_count) if months_4 else 0
        m3_repeat_pct = months_4.repeat_visitors_pct if months_4 else 0
        
        m6_revenue = months_7.revenue if months_7 else 0
        m6_avg_check = months_7.avg_check if months_7 else 0
        m6_completed = float(months_7.completed_count) if months_7 else 0
        m6_repeat_pct = months_7.repeat_visitors_pct if months_7 else 0
    else:
        # Обычная логика — используем текущие метрики
        prev_month = get_history_for_months_ago(1)
        months_3 = get_history_for_months_ago(3)
        months_6 = get_history_for_months_ago(6)
        
        current_revenue = current_metrics.revenue
        current_avg_check = current_metrics.avg_check
        current_completed = float(current_metrics.completed_count)
        current_repeat_pct = current_metrics.repeat_visitors_pct
        
        prev_revenue = prev_month.revenue if prev_month else 0
        prev_avg_check = prev_month.avg_check if prev_month else 0
        prev_completed = float(prev_month.completed_count) if prev_month else 0
        prev_repeat_pct = prev_month.repeat_visitors_pct if prev_month else 0
        
        m3_revenue = months_3.revenue if months_3 else 0
        m3_avg_check = months_3.avg_check if months_3 else 0
        m3_completed = float(months_3.completed_count) if months_3 else 0
        m3_repeat_pct = months_3.repeat_visitors_pct if months_3 else 0
        
        m6_revenue = months_6.revenue if months_6 else 0
        m6_avg_check = months_6.avg_check if months_6 else 0
        m6_completed = float(months_6.completed_count) if months_6 else 0
        m6_repeat_pct = months_6.repeat_visitors_pct if months_6 else 0
    
    # Формируем тренды
    trends = CompanyTrends(
        company_id=yclients_id,
        company_name=current_metrics.company_name,
    )
    
    # Выручка
    trends.revenue = TrendData(
        current=current_revenue,
        previous=prev_revenue,
        months_ago_3=m3_revenue,
        months_ago_6=m6_revenue,
    )
    
    # Средний чек
    trends.avg_check = TrendData(
        current=current_avg_check,
        previous=prev_avg_check,
        months_ago_3=m3_avg_check,
        months_ago_6=m6_avg_check,
    )
    
    # Записи
    trends.completed_count = TrendData(
        current=current_completed,
        previous=prev_completed,
        months_ago_3=m3_completed,
        months_ago_6=m6_completed,
    )
    
    # Повторные визиты
    trends.repeat_visitors_pct = TrendData(
        current=current_repeat_pct,
        previous=prev_repeat_pct,
        months_ago_3=m3_repeat_pct,
        months_ago_6=m6_repeat_pct,
    )
    
    # Возврат базы
    trends.client_base_return_pct = TrendData(
        current=current_metrics.client_base_return_pct,
        previous=prev_month.client_base_return_pct if prev_month else 0,
        months_ago_3=months_3.client_base_return_pct if months_3 else 0,
        months_ago_6=months_6.client_base_return_pct if months_6 else 0,
    )
    
    # История рангов
    trends.rank_history = [
        (f"{h.year}-{h.month:02d}", h.rank) 
        for h in sorted_history[:6]  # Последние 6 месяцев
    ]
    
    return trends


def format_trends_for_ai(trends: CompanyTrends) -> str:
    """
    Форматировать тренды для AI-контекста.
    """
    from datetime import datetime
    now = datetime.now()
    
    # Если в начале месяца — указываем что данные за прошлый месяц
    if now.day <= 7:
        period_note = "(данные за прошлый месяц, т.к. текущий только начался)"
    else:
        period_note = ""
    
    lines = [
        f"📈 ДИНАМИКА: {trends.company_name} {period_note}",
        "",
    ]
    
    if trends.revenue:
        lines.extend([
            f"💰 Выручка:",
            f"   {trends.revenue.trend_emoji} За месяц: {trends.revenue.change_1m_pct:+.1f}%",
            f"   За 3 мес: {trends.revenue.change_3m_pct:+.1f}%",
            f"   За 6 мес: {trends.revenue.change_6m_pct:+.1f}%",
            "",
        ])
    
    if trends.avg_check:
        lines.extend([
            f"📊 Средний чек:",
            f"   {trends.avg_check.trend_emoji} За месяц: {trends.avg_check.change_1m_pct:+.1f}%",
            f"   За 3 мес: {trends.avg_check.change_3m_pct:+.1f}%",
            "",
        ])
    
    if trends.repeat_visitors_pct:
        lines.extend([
            f"🔄 Повторные визиты:",
            f"   {trends.repeat_visitors_pct.trend_emoji} За месяц: {trends.repeat_visitors_pct.change_1m_pct:+.1f}%",
            f"   За 3 мес: {trends.repeat_visitors_pct.change_3m_pct:+.1f}%",
            "",
        ])
    
    if trends.rank_history:
        lines.append("🏆 Рейтинг по месяцам:")
        for period, rank in trends.rank_history[:4]:
            lines.append(f"   {period}: {rank} место")
    
    return "\n".join(lines)


async def get_network_average_trends() -> Optional[TrendData]:
    """
    Получить средние тренды по всей сети.
    Сравнивает текущий месяц с предыдущими.
    """
    from datetime import datetime
    from sqlalchemy import select, func
    
    async with AsyncSessionLocal() as db:
        # Получаем средние значения из истории
        now = datetime.now()
        
        def get_month_avg(months_ago: int) -> float:
            """Получить среднюю выручку за N месяцев назад."""
            target_total = now.year * 12 + now.month - months_ago
            target_year = target_total // 12
            target_month = target_total % 12 or 12
            if target_month == 0:
                target_month = 12
                target_year -= 1
            return target_year, target_month
        
        # Текущий месяц - из network_rating
        result = await db.execute(
            select(func.avg(NetworkRating.revenue)).where(NetworkRating.revenue > 0)
        )
        current_avg = result.scalar() or 0
        
        # Прошлые месяцы - из history
        prev_year, prev_month = get_month_avg(1)
        result = await db.execute(
            select(func.avg(NetworkRatingHistory.revenue)).where(
                NetworkRatingHistory.year == prev_year,
                NetworkRatingHistory.month == prev_month,
                NetworkRatingHistory.revenue > 0,
            )
        )
        prev_avg = result.scalar() or 0
        
        m3_year, m3_month = get_month_avg(3)
        result = await db.execute(
            select(func.avg(NetworkRatingHistory.revenue)).where(
                NetworkRatingHistory.year == m3_year,
                NetworkRatingHistory.month == m3_month,
                NetworkRatingHistory.revenue > 0,
            )
        )
        m3_avg = result.scalar() or 0
        
        m6_year, m6_month = get_month_avg(6)
        result = await db.execute(
            select(func.avg(NetworkRatingHistory.revenue)).where(
                NetworkRatingHistory.year == m6_year,
                NetworkRatingHistory.month == m6_month,
                NetworkRatingHistory.revenue > 0,
            )
        )
        m6_avg = result.scalar() or 0
        
        if current_avg == 0:
            return None
        
        return TrendData(
            current=float(current_avg),
            previous=float(prev_avg),
            months_ago_3=float(m3_avg),
            months_ago_6=float(m6_avg),
        )


def compare_with_network_trends(company_trends: TrendData, network_trends: TrendData) -> list[str]:
    """
    Сравнить тренды салона с трендами сети.
    """
    insights = []
    
    # Сравнение за месяц
    company_1m = company_trends.change_1m_pct
    network_1m = network_trends.change_1m_pct
    diff_1m = company_1m - network_1m
    
    if abs(diff_1m) > 5:
        if diff_1m > 0:
            insights.append(f"📈 За месяц: твой салон {company_1m:+.1f}%, сеть в среднем {network_1m:+.1f}% — ты лучше сети на {diff_1m:.1f}%")
        else:
            insights.append(f"📉 За месяц: твой салон {company_1m:+.1f}%, сеть в среднем {network_1m:+.1f}% — отстаёшь от сети на {abs(diff_1m):.1f}%")
    
    # Сравнение за 3 месяца
    company_3m = company_trends.change_3m_pct
    network_3m = network_trends.change_3m_pct
    diff_3m = company_3m - network_3m
    
    if abs(diff_3m) > 5:
        if diff_3m > 0:
            insights.append(f"📈 За 3 месяца: ты {company_3m:+.1f}%, сеть {network_3m:+.1f}% — опережаешь сеть")
        else:
            insights.append(f"📉 За 3 месяца: ты {company_3m:+.1f}%, сеть {network_3m:+.1f}% — отстаёшь от сети")
    
    return insights


def get_trend_insights(trends: CompanyTrends) -> list[str]:
    """
    Получить инсайты на основе трендов.
    """
    insights = []
    name = trends.company_name
    
    # Анализ выручки
    if trends.revenue:
        if trends.revenue.change_3m_pct > 15:
            insights.append(f"📈 {name}: Отличный рост выручки +{trends.revenue.change_3m_pct:.0f}% за 3 месяца!")
        elif trends.revenue.change_3m_pct < -15:
            insights.append(f"📉 {name}: Выручка упала на {abs(trends.revenue.change_3m_pct):.0f}% за 3 месяца — требует внимания")
        
        if trends.revenue.change_1m_pct < -20:
            insights.append(f"⚠️ {name}: Резкое падение выручки за месяц ({trends.revenue.change_1m_pct:.0f}%)")
    
    # Анализ среднего чека
    if trends.avg_check:
        if trends.avg_check.change_3m_pct > 10:
            insights.append(f"📈 {name}: Средний чек растёт (+{trends.avg_check.change_3m_pct:.0f}% за 3 мес)")
        elif trends.avg_check.change_3m_pct < -10:
            insights.append(f"📉 {name}: Средний чек падает ({trends.avg_check.change_3m_pct:.0f}% за 3 мес)")
    
    # Анализ повторных
    if trends.repeat_visitors_pct:
        if trends.repeat_visitors_pct.change_3m_pct < -10:
            insights.append(f"⚠️ {name}: Снижается % повторных визитов ({trends.repeat_visitors_pct.change_3m_pct:.0f}%)")
        elif trends.repeat_visitors_pct.change_3m_pct > 10:
            insights.append(f"✅ {name}: Растёт лояльность клиентов (+{trends.repeat_visitors_pct.change_3m_pct:.0f}%)")
    
    # Анализ рейтинга
    if len(trends.rank_history) >= 3:
        current_rank = trends.rank_history[0][1]
        old_rank = trends.rank_history[2][1]  # 3 месяца назад
        rank_change = old_rank - current_rank
        
        if rank_change > 5:
            insights.append(f"🏆 {name}: Поднялся в рейтинге на {rank_change} позиций за 3 месяца!")
        elif rank_change < -5:
            insights.append(f"⬇️ {name}: Опустился в рейтинге на {abs(rank_change)} позиций")
    
    return insights

