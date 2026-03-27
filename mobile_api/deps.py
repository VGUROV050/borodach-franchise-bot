# Mobile API — dependencies (auth, partner resolution)
#
# For the TestFlight MVP the partner is identified by a simple
# ``X-Partner-ID`` header.  This will be replaced with JWT auth
# once the auth flow is implemented.

from fastapi import Header, HTTPException


async def get_current_partner_id(
    x_partner_id: int = Header(..., alias="X-Partner-ID"),
) -> int:
    """Resolve the authenticated partner's database ID.

    MVP: read from ``X-Partner-ID`` header.
    Production: decode from JWT access token.
    """
    if x_partner_id <= 0:
        raise HTTPException(status_code=401, detail="Invalid partner ID")
    return x_partner_id
