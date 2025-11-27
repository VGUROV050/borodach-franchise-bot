# Database module

from .connection import get_db, init_db, close_db, AsyncSessionLocal
from .models import Base, Partner, Branch, PartnerBranch, PartnerStatus
from .crud import (
    get_partner_by_telegram_id,
    get_partner_by_phone,
    create_partner,
    update_partner_status,
    get_all_partners,
    get_pending_partners,
    get_all_branches,
    create_branch,
    get_or_create_branch,
    link_partner_to_branch,
    get_partner_branches,
)

__all__ = [
    # Connection
    "get_db",
    "init_db", 
    "close_db",
    "AsyncSessionLocal",
    # Models
    "Base",
    "Partner",
    "Branch",
    "PartnerBranch",
    "PartnerStatus",
    # CRUD
    "get_partner_by_telegram_id",
    "get_partner_by_phone",
    "create_partner",
    "update_partner_status",
    "get_all_partners",
    "get_pending_partners",
    "get_all_branches",
    "create_branch",
    "get_or_create_branch",
    "link_partner_to_branch",
    "get_partner_branches",
]

