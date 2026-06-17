"""Family tree endpoints for the Keeper surface (CLAUDE.md Flow 3).

All routes require Keeper JWT auth and scope to the Keeper's family.
Relationships are always stored as bidirectional pairs so the layout
algorithm can query either direction without OR conditions.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_keeper, verify_keeper_family
from app.db import get_session
from app.models import AIPeopleMention, FamilyMember, FamilyRelationship, Keeper, Story, StoryTag
from app.models.common import utcnow
from app.models.enums import RelationshipType
from app.schemas.family_members import (
    FamilyMemberResponse,
    MemberCreate,
    MemberStoriesResponse,
    MemberUpdate,
    RelationshipCreate,
    RelationshipResponse,
    StoryMentionResponse,
    TreeResponse,
)

router = APIRouter(prefix="/keeper/tree", tags=["keeper-tree"])

_OPPOSITE = {
    RelationshipType.parent: RelationshipType.child,
    RelationshipType.child: RelationshipType.parent,
    RelationshipType.spouse: RelationshipType.spouse,
    RelationshipType.sibling: RelationshipType.sibling,
}


def _get_member(session: Session, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
    m = session.get(FamilyMember, member_id)
    if not m or m.family_id != family_id:
        raise HTTPException(status_code=404, detail="Family member not found")
    return m


def _create_relationship_pair(
    session: Session,
    family_id: uuid.UUID,
    member_id: uuid.UUID,
    related_id: uuid.UUID,
    rel_type: RelationshipType,
    keeper_id: uuid.UUID,
) -> FamilyRelationship:
    rel_a = FamilyRelationship(
        family_id=family_id,
        member_id=member_id,
        related_member_id=related_id,
        relationship_type=rel_type,
        created_by=keeper_id,
    )
    rel_b = FamilyRelationship(
        family_id=family_id,
        member_id=related_id,
        related_member_id=member_id,
        relationship_type=_OPPOSITE[rel_type],
        created_by=keeper_id,
    )
    session.add(rel_a)
    session.add(rel_b)
    return rel_a


@router.get("", response_model=TreeResponse)
def get_tree(
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    members = session.exec(
        select(FamilyMember).where(FamilyMember.family_id == keeper.family_id)
    ).all()

    placed = [m for m in members if m.is_tree_member]
    unplaced = [m for m in members if not m.is_tree_member]

    relationships = session.exec(
        select(FamilyRelationship).where(FamilyRelationship.family_id == keeper.family_id)
    ).all()

    return TreeResponse(
        placed=[FamilyMemberResponse.model_validate(m) for m in placed],
        unplaced=[FamilyMemberResponse.model_validate(m) for m in unplaced],
        relationships=[RelationshipResponse.model_validate(r) for r in relationships],
    )


@router.post("/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
def create_tree_member(
    body: MemberCreate,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    member = FamilyMember(
        family_id=keeper.family_id,
        name_en=body.name_en,
        name_kh=body.name_kh,
        gender=body.gender,
        birth_year=body.birth_year,
        is_deceased=body.is_deceased,
        deceased_date=body.deceased_date,
        deceased_date_precision=body.deceased_date_precision,
        notes=body.notes,
        is_tree_member=True,
    )
    session.add(member)
    session.flush()  # get member.id before creating relationship

    if body.anchor_member_id and body.relationship_type:
        anchor = _get_member(session, body.anchor_member_id, keeper.family_id)
        if not anchor.is_tree_member:
            anchor.is_tree_member = True
            session.add(anchor)
        _create_relationship_pair(
            session,
            keeper.family_id,
            anchor.id,
            member.id,
            body.relationship_type,
            keeper.id,
        )

    session.commit()
    session.refresh(member)
    return FamilyMemberResponse.model_validate(member)


@router.patch("/members/{member_id}", response_model=FamilyMemberResponse)
def update_tree_member(
    member_id: uuid.UUID,
    body: MemberUpdate,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    member = _get_member(session, member_id, keeper.family_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    member.updated_at = utcnow()

    session.add(member)
    session.commit()
    session.refresh(member)
    return FamilyMemberResponse.model_validate(member)


@router.post("/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(
    body: RelationshipCreate,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    member = _get_member(session, body.member_id, keeper.family_id)
    related = _get_member(session, body.related_member_id, keeper.family_id)

    if not member.is_tree_member:
        member.is_tree_member = True
        session.add(member)
    if not related.is_tree_member:
        related.is_tree_member = True
        session.add(related)

    rel = _create_relationship_pair(
        session,
        keeper.family_id,
        member.id,
        related.id,
        body.relationship_type,
        keeper.id,
    )

    session.commit()
    session.refresh(rel)
    return RelationshipResponse.model_validate(rel)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tree_member(
    member_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    member = _get_member(session, member_id, keeper.family_id)

    outgoing = session.exec(
        select(FamilyRelationship).where(
            FamilyRelationship.family_id == keeper.family_id,
            FamilyRelationship.member_id == member_id,
        )
    ).all()
    incoming = session.exec(
        select(FamilyRelationship).where(
            FamilyRelationship.family_id == keeper.family_id,
            FamilyRelationship.related_member_id == member_id,
        )
    ).all()
    for rel in [*outgoing, *incoming]:
        session.delete(rel)

    has_references = (
        session.exec(select(StoryTag).where(StoryTag.family_member_id == member_id)).first()
        or session.exec(select(AIPeopleMention).where(AIPeopleMention.family_member_id == member_id)).first()
    )

    if has_references:
        member.is_tree_member = False
        member.updated_at = utcnow()
        session.add(member)
    else:
        session.delete(member)

    session.commit()


@router.delete("/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(
    rel_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    rel = session.get(FamilyRelationship, rel_id)
    if not rel or rel.family_id != keeper.family_id:
        raise HTTPException(status_code=404, detail="Relationship not found")

    # Delete both directions
    inverse = session.exec(
        select(FamilyRelationship).where(
            FamilyRelationship.family_id == keeper.family_id,
            FamilyRelationship.member_id == rel.related_member_id,
            FamilyRelationship.related_member_id == rel.member_id,
            FamilyRelationship.relationship_type == _OPPOSITE[rel.relationship_type],
        )
    ).first()

    session.delete(rel)
    if inverse:
        session.delete(inverse)
    session.commit()


@router.get("/members/{member_id}/stories", response_model=MemberStoriesResponse)
def get_member_stories(
    member_id: uuid.UUID,
    keeper: Keeper = Depends(get_current_keeper),
    session: Session = Depends(get_session),
):
    member = _get_member(session, member_id, keeper.family_id)

    tags = session.exec(
        select(StoryTag).where(
            StoryTag.family_member_id == member_id,
        )
    ).all()

    story_ids = {t.story_id for t in tags}
    stories = []
    for sid in story_ids:
        s = session.get(Story, sid)
        if s and s.family_id == keeper.family_id:
            stories.append(
                StoryMentionResponse(
                    id=s.id,
                    title_en=s.title_en,
                    title_kh=s.title_kh,
                    narrator_name_raw=s.narrator_name_raw,
                )
            )

    return MemberStoriesResponse(
        member=FamilyMemberResponse.model_validate(member),
        stories=stories,
    )
