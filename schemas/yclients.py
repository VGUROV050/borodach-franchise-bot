# Pydantic schemas for YClients API responses

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class YClientsIncomeStats(BaseModel):
    """Статистика дохода из YClients Analytics."""
    
    current_sum: float = Field(default=0.0, description="Текущая сумма дохода")
    previous_sum: float = Field(default=0.0, description="Сумма за предыдущий период")
    change_percent: float = Field(default=0.0, description="Изменение в процентах")
    
    @field_validator("current_sum", "previous_sum", mode="before")
    @classmethod
    def parse_sum(cls, v):
        """Парсинг суммы из строки с разделителями."""
        if isinstance(v, str):
            # Убираем пробелы и заменяем запятую на точку
            v = v.replace(" ", "").replace(",", ".")
            return float(v) if v else 0.0
        return float(v) if v else 0.0


class YClientsRecordStats(BaseModel):
    """Статистика записей из YClients Analytics."""
    
    current_completed_count: int = Field(default=0, description="Завершённых записей")
    current_total_count: int = Field(default=0, description="Всего записей")
    current_cancelled_count: int = Field(default=0, description="Отменённых записей")


class YClientsAnalytics(BaseModel):
    """Аналитика компании из YClients."""
    
    income_total_stats: YClientsIncomeStats = Field(
        default_factory=YClientsIncomeStats,
        description="Общий доход"
    )
    income_average_stats: YClientsIncomeStats = Field(
        default_factory=YClientsIncomeStats,
        description="Средний чек"
    )
    record_stats: YClientsRecordStats = Field(
        default_factory=YClientsRecordStats,
        description="Статистика записей"
    )
    
    @property
    def revenue(self) -> float:
        """Общая выручка."""
        return self.income_total_stats.current_sum
    
    @property
    def avg_check(self) -> float:
        """Средний чек."""
        return self.income_average_stats.current_sum
    
    @property
    def completed_count(self) -> int:
        """Количество завершённых записей."""
        return self.record_stats.current_completed_count


class YClientsCompanyInfo(BaseModel):
    """Информация о компании/салоне из YClients."""
    
    id: int = Field(description="ID компании в YClients")
    title: str = Field(description="Название салона")
    city: Optional[str] = Field(default=None, description="Город")
    address: Optional[str] = Field(default=None, description="Адрес")
    phone: Optional[str] = Field(default=None, description="Телефон")
    is_active: bool = Field(default=True, description="Активен ли салон")
    
    class Config:
        extra = "ignore"  # Игнорируем лишние поля из API


class NetworkRatingItem(BaseModel):
    """Элемент рейтинга сети салонов."""
    
    company_id: str = Field(description="ID компании в YClients")
    company_name: str = Field(description="Название салона")
    revenue: float = Field(default=0.0, description="Выручка за период")
    avg_check: float = Field(default=0.0, description="Средний чек")
    rank: int = Field(default=0, description="Место в рейтинге")
    previous_rank: Optional[int] = Field(default=None, description="Предыдущее место")
    total_companies: int = Field(default=0, description="Всего компаний в рейтинге")
    
    @property
    def rank_change(self) -> Optional[int]:
        """Изменение позиции в рейтинге (положительное = улучшение)."""
        if self.previous_rank is None:
            return None
        return self.previous_rank - self.rank
    
    @property
    def rank_change_emoji(self) -> str:
        """Эмодзи изменения рейтинга."""
        change = self.rank_change
        if change is None:
            return "🆕"
        elif change > 0:
            return f"↑{change} 📈"
        elif change < 0:
            return f"↓{abs(change)} 📉"
        else:
            return "➡️"


class MonthlyRevenueResult(BaseModel):
    """Результат запроса выручки за месяц."""
    
    success: bool = Field(description="Успешность запроса")
    revenue: float = Field(default=0.0, description="Выручка")
    avg_check: float = Field(default=0.0, description="Средний чек")
    completed_count: int = Field(default=0, description="Завершённых записей")
    period: str = Field(default="", description="Период в формате DD.MM.YYYY — DD.MM.YYYY")
    error: Optional[str] = Field(default=None, description="Сообщение об ошибке")

