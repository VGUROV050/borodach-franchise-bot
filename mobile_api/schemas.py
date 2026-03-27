# Mobile API — Pydantic response schemas

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Account ──────────────────────────────────────────────────────

class CompanyOut(BaseModel):
    id: int
    yclients_id: str
    name: str
    city: Optional[str] = None
    region: Optional[str] = None
    is_active: bool = True


class PartnerProfileOut(BaseModel):
    id: int
    full_name: str
    phone_masked: str
    status: str
    is_owner: bool
    position: Optional[str] = None
    companies: list[CompanyOut] = []
    has_pending_branch: bool = False
    pending_branch_text: Optional[str] = None
    created_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None


# ── Statistics ───────────────────────────────────────────────────

class CompanyStatsOut(BaseModel):
    name: str
    yclients_id: Optional[str] = None
    revenue: float = 0
    completed_count: int = 0
    total_count: int = 0
    rank: int = 0
    total_companies: int = 0
    rank_change: int = 0
    avg_check: float = 0
    error: Optional[str] = None


class PeriodStatsOut(BaseModel):
    period_type: str
    period_label: str
    date_from: str
    date_to: str
    companies: list[CompanyStatsOut] = []
    total_revenue: float = 0
    total_completed: int = 0


# ── Rating ───────────────────────────────────────────────────────

class RatingEntryOut(BaseModel):
    rank: int
    yclients_company_id: str
    company_name: str
    location: str
    region: Optional[str] = None
    revenue: float = 0
    avg_check: float = 0
    rank_change: int = 0
    is_partner: bool = False


class RatingOut(BaseModel):
    period_label: str
    total_companies: int
    entries: list[RatingEntryOut] = []
    partner_ranks: list[int] = []


# ── Health ───────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str
    version: str


# ── Useful Info (Полезное) ────────────────────────────────────────

class DepartmentOut(BaseModel):
    key: str
    name: str


class DepartmentButtonOut(BaseModel):
    id: int
    button_text: str
    message_text: str


# ── Tasks (Задачи) ──────────────────────────────────────────────

class TaskDepartmentOut(BaseModel):
    key: str
    name: str
    group_id: str
    responsible_id: str


class TaskOut(BaseModel):
    id: int
    title: str
    barbershop: Optional[str] = None
    created_at: str
    stage: str
    stage_emoji: str
    group_id: str
    department_name: str


class TaskCreateIn(BaseModel):
    department_key: str
    barbershop: str
    title: str
    description: str


class TaskCreateOut(BaseModel):
    task_id: int


class TaskCancelOut(BaseModel):
    success: bool


# ── AI Assistant ─────────────────────────────────────────────────

class AiAskIn(BaseModel):
    question: str
    detailed: bool = False


class AiAskOut(BaseModel):
    answer: str


# ── Contact Office ───────────────────────────────────────────────

class ContactOfficeOut(BaseModel):
    text: str


# ── Polls (Опросы) ──────────────────────────────────────────────

class PollOptionOut(BaseModel):
    id: int
    text: str
    position: int


class PollOut(BaseModel):
    id: int
    question: str
    is_anonymous: bool = True
    allows_multiple: bool = False
    status: str
    options: list[PollOptionOut] = []
    created_at: Optional[datetime] = None


class PollVoteIn(BaseModel):
    option_ids: list[int]


class PollVoteOut(BaseModel):
    success: bool


# ── Barbershop Request ──────────────────────────────────────────

class BarbershopRequestIn(BaseModel):
    branch_text: str


class BarbershopRequestOut(BaseModel):
    success: bool
