# Partner profile service — shared business logic

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    AsyncSessionLocal,
    get_partner_by_id,
    get_partner_companies,
    PartnerStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    id: int
    yclients_id: str
    name: str
    city: Optional[str] = None
    region: Optional[str] = None
    is_active: bool = True


@dataclass
class PartnerProfile:
    id: int
    full_name: str
    phone: Optional[str]
    phone_masked: str
    status: str
    is_owner: bool
    position: Optional[str]
    companies: list[CompanyInfo] = field(default_factory=list)
    has_pending_branch: bool = False
    pending_branch_text: Optional[str] = None
    created_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None


async def get_partner_profile(partner_id: int) -> Optional[PartnerProfile]:
    """Load partner profile with linked companies."""
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_id(db, partner_id)
        if not partner:
            return None

        companies_raw = await get_partner_companies(db, partner.id)

        phone_masked = ""
        if partner.phone and len(partner.phone) >= 4:
            phone_masked = f"****{partner.phone[-4:]}"

        companies = [
            CompanyInfo(
                id=c.id,
                yclients_id=c.yclients_id,
                name=c.name,
                city=getattr(c, "city", None),
                region=getattr(c, "region", None),
                is_active=getattr(c, "is_active", True),
            )
            for c in companies_raw
        ]

        return PartnerProfile(
            id=partner.id,
            full_name=partner.full_name,
            phone=partner.phone,
            phone_masked=phone_masked,
            status=partner.status.value,
            is_owner=partner.is_owner,
            position=partner.position,
            companies=companies,
            has_pending_branch=partner.has_pending_branch,
            pending_branch_text=partner.branches_text,
            created_at=partner.created_at,
            verified_at=partner.verified_at,
        )
