"""Family member roster endpoint, used by Quick Tag (CLAUDE.md Flow 1.4)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_family
from app.db import get_session
from app.models import Family, FamilyMember
from app.schemas.family_members import FamilyMemberResponse

router = APIRouter(prefix="/f/{access_token}/family-members", tags=["family-members"])


@router.get("", response_model=list[FamilyMemberResponse])
def list_family_members(
    family: Family = Depends(get_family),
    session: Session = Depends(get_session),
) -> list[FamilyMember]:
    """Quick Tag chip list (1.4): every member of the family roster."""
    return session.exec(
        select(FamilyMember).where(FamilyMember.family_id == family.id).order_by(FamilyMember.name_en.asc())
    ).all()
