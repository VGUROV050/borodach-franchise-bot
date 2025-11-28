# Database models

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class PartnerStatus(str, enum.Enum):
    """Статусы партнёра."""
    PENDING = "pending"      # Ожидает верификации
    VERIFIED = "verified"    # Верифицирован
    REJECTED = "rejected"    # Отклонён


class Partner(Base):
    """Модель партнёра (франчайзи)."""
    
    __tablename__ = "partners"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Telegram данные
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Персональные данные
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # Филиалы — текст от пользователя (для сопоставления админом)
    branches_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Статус верификации
    status: Mapped[PartnerStatus] = mapped_column(
        Enum(PartnerStatus),
        default=PartnerStatus.PENDING,
        index=True,
    )
    
    # Причина отклонения (если rejected)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Флаг: есть ли запрос на добавление филиала
    has_pending_branch: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Связь с филиалами (старая схема, заполняется админом при верификации)
    branches: Mapped[list["PartnerBranch"]] = relationship(
        back_populates="partner",
        cascade="all, delete-orphan",
    )
    
    # Связь с салонами YClients (новая схема, автосинхронизация)
    companies: Mapped[list["PartnerCompany"]] = relationship(
        back_populates="partner",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Partner {self.id}: {self.full_name} ({self.status.value})>"


class Branch(Base):
    """Модель филиала."""
    
    __tablename__ = "branches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # YClients ID — уникальный системный идентификатор
    yclients_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    
    # Информация о филиале
    city: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Название ТЦ и т.д.
    
    # Краткое название для отображения (например "Мега Тёплый Стан")
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Активность
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Связь с партнёрами
    partners: Mapped[list["PartnerBranch"]] = relationship(
        back_populates="branch",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Branch {self.id}: {self.display_name or self.city}>"


class PartnerBranch(Base):
    """Связь партнёра с филиалом (многие-ко-многим)."""
    
    __tablename__ = "partner_branches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"))
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"))
    
    # Роль партнёра в филиале
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)  # Владелец или сотрудник
    
    # Временные метки
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Связи
    partner: Mapped["Partner"] = relationship(back_populates="branches")
    branch: Mapped["Branch"] = relationship(back_populates="partners")
    
    def __repr__(self) -> str:
        return f"<PartnerBranch partner={self.partner_id} branch={self.branch_id}>"


class BroadcastHistory(Base):
    """История рассылок."""
    
    __tablename__ = "broadcast_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Текст сообщения
    message: Mapped[str] = mapped_column(Text)
    
    # Получатели (JSON список имён или "Все верифицированные")
    recipients: Mapped[str] = mapped_column(Text)
    recipients_count: Mapped[int] = mapped_column(default=0)
    
    # Результаты отправки
    success_count: Mapped[int] = mapped_column(default=0)
    fail_count: Mapped[int] = mapped_column(default=0)
    
    # Кто отправил
    sent_by: Mapped[str] = mapped_column(String(100), default="admin")
    
    # Временные метки
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    def __repr__(self) -> str:
        return f"<BroadcastHistory {self.id}: {self.sent_at}>"


class YClientsCompany(Base):
    """
    Салон из сети YClients.
    Синхронизируется автоматически из API YClients.
    Является единым источником правды для всех салонов сети.
    """
    
    __tablename__ = "yclients_companies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # YClients ID — уникальный идентификатор в YClients
    yclients_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # Название салона (из YClients)
    name: Mapped[str] = mapped_column(String(255))
    
    # Город (парсится из названия)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Регион/область
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Является ли город-миллионник
    is_million_city: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Активность
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Когда синхронизировано
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Связь с партнёрами
    partner_links: Mapped[list["PartnerCompany"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<YClientsCompany {self.yclients_id}: {self.name}>"


class PartnerCompany(Base):
    """
    Связь партнёра с салоном YClients (многие-ко-многим).
    Заменяет PartnerBranch для автоматически синхронизированных салонов.
    """
    
    __tablename__ = "partner_companies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"))
    company_id: Mapped[int] = mapped_column(ForeignKey("yclients_companies.id", ondelete="CASCADE"))
    
    # Роль партнёра
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Временные метки
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Связи
    partner: Mapped["Partner"] = relationship(back_populates="companies")
    company: Mapped["YClientsCompany"] = relationship(back_populates="partner_links")
    
    def __repr__(self) -> str:
        return f"<PartnerCompany partner={self.partner_id} company={self.company_id}>"


class NetworkRating(Base):
    """Рейтинг салонов в сети (кэш, обновляется ночью)."""
    
    __tablename__ = "network_rating"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # YClients ID салона
    yclients_company_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # Название салона (из YClients)
    company_name: Mapped[str] = mapped_column(String(255))
    
    # Выручка за текущий месяц
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Средний чек
    avg_check: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Место в рейтинге (1 = лидер)
    rank: Mapped[int] = mapped_column(Integer, default=0, index=True)
    
    # Место в рейтинге в прошлом месяце (для показа изменения)
    previous_rank: Mapped[int] = mapped_column(Integer, default=0)
    
    # Всего салонов в сети (с выручкой > 0)
    total_companies: Mapped[int] = mapped_column(Integer, default=0)
    
    # Когда обновлено
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    @property
    def rank_change(self) -> int:
        """Изменение позиции (положительное = улучшение)."""
        if self.previous_rank == 0:
            return 0
        return self.previous_rank - self.rank
    
    def __repr__(self) -> str:
        return f"<NetworkRating {self.company_name}: #{self.rank}>"


class NetworkRatingHistory(Base):
    """История рейтингов за прошлые месяцы."""
    
    __tablename__ = "network_rating_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # YClients ID салона
    yclients_company_id: Mapped[str] = mapped_column(String(50), index=True)
    
    # Название салона
    company_name: Mapped[str] = mapped_column(String(255))
    
    # Данные за месяц
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    avg_check: Mapped[float] = mapped_column(Float, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    total_companies: Mapped[int] = mapped_column(Integer, default=0)
    
    # Период (год и месяц)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    
    # Когда сохранено
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    def __repr__(self) -> str:
        return f"<NetworkRatingHistory {self.company_name}: {self.year}-{self.month} #{self.rank}>"

