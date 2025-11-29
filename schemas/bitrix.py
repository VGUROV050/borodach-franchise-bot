# Pydantic schemas for Bitrix24 API

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BitrixTaskCreate(BaseModel):
    """Данные для создания задачи в Bitrix24."""
    
    title: str = Field(min_length=1, max_length=500, description="Название задачи")
    description: str = Field(default="", description="Описание задачи")
    responsible_id: int = Field(description="ID ответственного сотрудника")
    group_id: Optional[int] = Field(default=None, description="ID группы/проекта")
    deadline: Optional[datetime] = Field(default=None, description="Дедлайн")
    priority: int = Field(default=1, ge=0, le=2, description="Приоритет: 0=низкий, 1=средний, 2=высокий")
    
    # Дополнительные поля для нашей логики
    partner_name: Optional[str] = Field(default=None, description="Имя партнёра")
    partner_phone: Optional[str] = Field(default=None, description="Телефон партнёра")
    barbershop_name: Optional[str] = Field(default=None, description="Название барбершопа")
    department: Optional[str] = Field(default=None, description="Отдел")


class BitrixTask(BaseModel):
    """Задача из Bitrix24."""
    
    id: int = Field(description="ID задачи")
    title: str = Field(description="Название")
    description: Optional[str] = Field(default=None, description="Описание")
    status: int = Field(description="Статус задачи")
    status_name: Optional[str] = Field(default=None, description="Название статуса")
    priority: int = Field(default=1, description="Приоритет")
    responsible_id: Optional[int] = Field(default=None, description="ID ответственного")
    created_by: Optional[int] = Field(default=None, description="ID создателя")
    created_date: Optional[datetime] = Field(default=None, description="Дата создания")
    deadline: Optional[datetime] = Field(default=None, description="Дедлайн")
    closed_date: Optional[datetime] = Field(default=None, description="Дата закрытия")
    group_id: Optional[int] = Field(default=None, description="ID группы")
    
    class Config:
        extra = "ignore"
    
    @property
    def is_completed(self) -> bool:
        """Завершена ли задача."""
        return self.status == 5
    
    @property
    def is_cancelled(self) -> bool:
        """Отменена ли задача."""
        return self.status == 6  # или другой код отмены
    
    @property
    def is_active(self) -> bool:
        """Активна ли задача (не завершена и не отменена)."""
        return self.status not in (5, 6)


class BitrixTaskResult(BaseModel):
    """Результат операции с задачей."""
    
    success: bool = Field(description="Успешность операции")
    task_id: Optional[int] = Field(default=None, description="ID задачи")
    task: Optional[BitrixTask] = Field(default=None, description="Данные задачи")
    error: Optional[str] = Field(default=None, description="Сообщение об ошибке")


class BitrixUser(BaseModel):
    """Пользователь Bitrix24."""
    
    id: int = Field(description="ID пользователя")
    name: Optional[str] = Field(default=None, description="Имя")
    last_name: Optional[str] = Field(default=None, description="Фамилия")
    email: Optional[str] = Field(default=None, description="Email")
    
    @property
    def full_name(self) -> str:
        """Полное имя."""
        parts = [self.name, self.last_name]
        return " ".join(p for p in parts if p) or f"User #{self.id}"
    
    class Config:
        extra = "ignore"

