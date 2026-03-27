# Mobile API — account / profile routes

from fastapi import APIRouter, Depends, HTTPException

from mobile_api.deps import get_current_partner_id
from mobile_api.schemas import (
    PartnerProfileOut,
    CompanyOut,
    ContactOfficeOut,
    BarbershopRequestIn,
    BarbershopRequestOut,
)
from services.partner_service import (
    get_partner_profile,
    get_contact_office_text,
    request_add_barbershop,
)

router = APIRouter()


@router.get("/me", response_model=PartnerProfileOut)
async def get_profile(partner_id: int = Depends(get_current_partner_id)):
    profile = await get_partner_profile(partner_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Partner not found")
    return PartnerProfileOut(
        id=profile.id,
        full_name=profile.full_name,
        phone_masked=profile.phone_masked,
        status=profile.status,
        is_owner=profile.is_owner,
        position=profile.position,
        companies=[
            CompanyOut(
                id=c.id,
                yclients_id=c.yclients_id,
                name=c.name,
                city=c.city,
                region=c.region,
                is_active=c.is_active,
            )
            for c in profile.companies
        ],
        has_pending_branch=profile.has_pending_branch,
        pending_branch_text=profile.pending_branch_text,
        created_at=profile.created_at,
        verified_at=profile.verified_at,
    )


@router.get("/companies", response_model=list[CompanyOut])
async def get_companies(partner_id: int = Depends(get_current_partner_id)):
    profile = await get_partner_profile(partner_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Partner not found")
    return [
        CompanyOut(
            id=c.id,
            yclients_id=c.yclients_id,
            name=c.name,
            city=c.city,
            region=c.region,
            is_active=c.is_active,
        )
        for c in profile.companies
    ]


@router.get("/contact-office", response_model=ContactOfficeOut)
async def contact_office():
    text = await get_contact_office_text()
    return ContactOfficeOut(text=text)


@router.post("/barbershop-request", response_model=BarbershopRequestOut)
async def barbershop_request(
    body: BarbershopRequestIn,
    partner_id: int = Depends(get_current_partner_id),
):
    success = await request_add_barbershop(partner_id, body.branch_text)
    if not success:
        raise HTTPException(status_code=404, detail="Partner not found")
    return BarbershopRequestOut(success=True)
