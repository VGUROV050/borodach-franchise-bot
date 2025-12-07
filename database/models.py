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
    
    # Роль в барбершопе
    is_owner: Mapped[bool] = mapped_column(Boolean, default=True)  # Владелец или сотрудник
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Должность (если не владелец)
    
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
    
    # Город (для сравнения с похожими)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Миллионник (для группировки)
    is_million_city: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # === Основные метрики ===
    
    # Выручка за текущий месяц (общая)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Выручка по услугам
    services_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Выручка по товарам
    products_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Средний чек
    avg_check: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Количество завершённых записей
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Процент повторных визитов (0-100)
    repeat_visitors_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # === Клиентская статистика ===
    
    # Количество новых клиентов за период
    new_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Количество вернувшихся клиентов за период
    return_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Всего клиентов в базе
    total_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Процент возврата клиентской базы (return_clients / total_clients * 100)
    client_base_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # === Рейтинг ===
    
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
    """История рейтингов за прошлые месяцы (хранится 12 месяцев)."""
    
    __tablename__ = "network_rating_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # YClients ID салона
    yclients_company_id: Mapped[str] = mapped_column(String(50), index=True)
    
    # Название салона
    company_name: Mapped[str] = mapped_column(String(255))
    
    # Город
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # === Метрики за месяц ===
    
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    services_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    products_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    avg_check: Mapped[float] = mapped_column(Float, default=0.0)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    repeat_visitors_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # === Клиентская статистика ===
    
    new_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    return_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    total_clients_count: Mapped[int] = mapped_column(Integer, default=0)
    client_base_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    
    # === Рейтинг ===
    
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


class RequestType(str, enum.Enum):
    """Тип заявки."""
    VERIFICATION = "verification"     # Верификация партнёра
    ADD_BARBERSHOP = "add_barbershop" # Добавление барбершопа


class RequestStatus(str, enum.Enum):
    """Статус заявки."""
    APPROVED = "approved"   # Одобрено
    REJECTED = "rejected"   # Отклонено


class RequestLog(Base):
    """Лог всех заявок (верификация, добавление барбершопов)."""
    
    __tablename__ = "request_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Связь с партнёром
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"), index=True)
    partner: Mapped["Partner"] = relationship("Partner", foreign_keys=[partner_id])
    
    # Тип и статус заявки
    request_type: Mapped[RequestType] = mapped_column(Enum(RequestType), index=True)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), index=True)
    
    # Детали заявки (текст от партнёра)
    request_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Результат (что одобрено/причина отказа)
    result_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Кто обработал
    processed_by: Mapped[str] = mapped_column(String(100), default="admin")
    
    # Когда создано
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    
    def __repr__(self) -> str:
        return f"<RequestLog {self.request_type.value}: {self.status.value}>"


class PollStatus(str, enum.Enum):
    """Статус голосования."""
    DRAFT = "draft"       # Черновик
    SENT = "sent"         # Отправлено
    CLOSED = "closed"     # Закрыто


class Poll(Base):
    """Голосование."""
    
    __tablename__ = "polls"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Вопрос
    question: Mapped[str] = mapped_column(Text)
    
    # Настройки
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_multiple: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Статус
    status: Mapped[PollStatus] = mapped_column(
        Enum(PollStatus),
        default=PollStatus.DRAFT,
        index=True,
    )
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Кто создал
    created_by: Mapped[str] = mapped_column(String(100), default="admin")
    
    # Связи
    options: Mapped[list["PollOption"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
        order_by="PollOption.position",
    )
    responses: Mapped[list["PollResponse"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
    )
    sent_messages: Mapped[list["PollMessage"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
    )
    
    @property
    def total_votes(self) -> int:
        """Общее количество проголосовавших."""
        return len(self.responses)
    
    def __repr__(self) -> str:
        return f"<Poll {self.id}: {self.question[:30]}...>"


class PollOption(Base):
    """Вариант ответа в голосовании."""
    
    __tablename__ = "poll_options"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"))
    
    # Текст варианта
    text: Mapped[str] = mapped_column(String(255))
    
    # Порядок отображения
    position: Mapped[int] = mapped_column(Integer, default=0)
    
    # Связи
    poll: Mapped["Poll"] = relationship(back_populates="options")
    
    def __repr__(self) -> str:
        return f"<PollOption {self.id}: {self.text[:20]}...>"


class PollResponse(Base):
    """Ответ пользователя на голосование."""
    
    __tablename__ = "poll_responses"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"), index=True)
    
    # Выбранные варианты (JSON: [1, 3])
    option_ids: Mapped[str] = mapped_column(Text)
    
    # Когда ответил
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Связи
    poll: Mapped["Poll"] = relationship(back_populates="responses")
    partner: Mapped["Partner"] = relationship()
    
    def __repr__(self) -> str:
        return f"<PollResponse poll={self.poll_id} partner={self.partner_id}>"


class DepartmentType(str, enum.Enum):
    """Типы отделов."""
    DEVELOPMENT = "development"
    MARKETING = "marketing"
    DESIGN = "design"


class DepartmentInfoType(str, enum.Enum):
    """Типы информации по отделу."""
    IMPORTANT_INFO = "important_info"   # Важная информация
    CONTACT_INFO = "contact_info"       # Связаться с отделом


class DepartmentInfo(Base):
    """Настраиваемые тексты для раздела 'Полезное' по отделам."""
    
    __tablename__ = "department_info"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Отдел
    department: Mapped[DepartmentType] = mapped_column(
        Enum(DepartmentType),
        index=True,
    )
    
    # Тип информации
    info_type: Mapped[DepartmentInfoType] = mapped_column(
        Enum(DepartmentInfoType),
        index=True,
    )
    
    # Текст сообщения (HTML разрешён)
    text: Mapped[str] = mapped_column(Text)
    
    # Когда обновлено
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Кто обновил
    updated_by: Mapped[str] = mapped_column(String(100), default="admin")
    
    def __repr__(self) -> str:
        return f"<DepartmentInfo {self.department.value}/{self.info_type.value}>"


class DepartmentButton(Base):
    """Кастомные кнопки для раздела 'Полезное' по отделам."""
    
    __tablename__ = "department_buttons"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Отдел
    department: Mapped[DepartmentType] = mapped_column(
        Enum(DepartmentType),
        index=True,
    )
    
    # Текст кнопки (что видит пользователь)
    button_text: Mapped[str] = mapped_column(String(100))
    
    # Сообщение при нажатии (HTML разрешён)
    message_text: Mapped[str] = mapped_column(Text)
    
    # Порядок отображения (меньше = выше)
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Активна ли кнопка
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Когда создано/обновлено
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    def __repr__(self) -> str:
        return f"<DepartmentButton {self.department.value}: {self.button_text}>"


class PollMessage(Base):
    """Связь голосования с сообщением в Telegram (для закрытия)."""
    
    __tablename__ = "poll_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="CASCADE"))
    
    # Telegram данные для закрытия опроса
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger)
    telegram_poll_id: Mapped[str] = mapped_column(String(100))
    
    # Статус
    is_stopped: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Связи
    poll: Mapped["Poll"] = relationship(back_populates="sent_messages")
    
    def __repr__(self) -> str:
        return f"<PollMessage poll={self.poll_id} msg={self.telegram_message_id}>"


# ============================================================
# KNOWLEDGE BASE - База знаний (видео уроки)
# ============================================================

class KnowledgeModule(Base):
    """Модуль (тема) в базе знаний."""
    
    __tablename__ = "knowledge_modules"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Название модуля
    title: Mapped[str] = mapped_column(String(255))
    
    # Описание
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Порядок отображения
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Активен ли модуль
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Связь с уроками
    lessons: Mapped[list["KnowledgeLesson"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="KnowledgeLesson.order",
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeModule {self.id}: {self.title}>"


class KnowledgeLesson(Base):
    """Урок (видео) в модуле."""
    
    __tablename__ = "knowledge_lessons"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Связь с модулем
    module_id: Mapped[int] = mapped_column(ForeignKey("knowledge_modules.id", ondelete="CASCADE"), index=True)
    
    # Название урока
    title: Mapped[str] = mapped_column(String(255))
    
    # Имя видео файла
    video_filename: Mapped[str] = mapped_column(String(255))
    
    # Длительность в секундах
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Порядок в модуле
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Статус обработки
    is_transcribed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Краткое содержание урока (для улучшения RAG)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    transcribed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Связи
    module: Mapped["KnowledgeModule"] = relationship(back_populates="lessons")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeLesson {self.id}: {self.title}>"


class KnowledgeChunk(Base):
    """Фрагмент транскрипта с эмбеддингом для RAG."""
    
    __tablename__ = "knowledge_chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Связь с уроком
    lesson_id: Mapped[int] = mapped_column(ForeignKey("knowledge_lessons.id", ondelete="CASCADE"), index=True)
    
    # Текст фрагмента
    text: Mapped[str] = mapped_column(Text)
    
    # Тайм-коды (секунды)
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Порядковый номер чанка в уроке
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    
    # Эмбеддинг (будет храниться как pgvector)
    # Для pgvector нужно добавить расширение и использовать специальный тип
    # Пока сохраняем как JSON строку, потом мигрируем на pgvector
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Связи
    lesson: Mapped["KnowledgeLesson"] = relationship(back_populates="chunks")
    
    @property
    def timestamp_formatted(self) -> str:
        """Форматированный тайм-код (MM:SS)."""
        minutes = int(self.start_time // 60)
        seconds = int(self.start_time % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def __repr__(self) -> str:
        return f"<KnowledgeChunk lesson={self.lesson_id} @{self.timestamp_formatted}>"


# ============================================================
# BOT SETTINGS - Настройки бота
# ============================================================

class BotSetting(Base):
    """Настройки бота (ключ-значение)."""
    
    __tablename__ = "bot_settings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Уникальный ключ настройки
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # Значение настройки
    value: Mapped[str] = mapped_column(Text)
    
    # Описание (для админки)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Временные метки
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    def __repr__(self) -> str:
        return f"<BotSetting {self.key}={self.value[:50]}>"

