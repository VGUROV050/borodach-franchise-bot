# Database models

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
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
    
    # Персональные данные
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # Статус верификации
    status: Mapped[PartnerStatus] = mapped_column(
        Enum(PartnerStatus),
        default=PartnerStatus.PENDING,
        index=True,
    )
    
    # Причина отклонения (если rejected)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
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
    
    # Связь с филиалами
    branches: Mapped[list["PartnerBranch"]] = relationship(
        back_populates="partner",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Partner {self.id}: {self.full_name} ({self.status.value})>"


class Branch(Base):
    """Модель филиала."""
    
    __tablename__ = "branches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Информация о филиале
    city: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Название ТЦ и т.д.
    
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
        return f"<Branch {self.id}: {self.city}, {self.address}>"


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

