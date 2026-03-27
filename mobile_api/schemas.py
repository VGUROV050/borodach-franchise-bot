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
