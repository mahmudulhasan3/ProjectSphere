import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.group import Group, GroupMember
from app.services.semester_service import get_active_semester
from app.schemas.group import (
    GroupCreateResponse,
    GroupJoinRequest,
    GroupNameUpdate,
    GroupDetailResponse,
    GroupMemberInfo,
    MessageResponse,
)

from app.models.student_profile import StudentProfile

router = APIRouter(prefix="/groups", tags=["Group"])

MAX_GROUP_MEMBERS = 3


def generate_join_code() -> str:
    """Generates a random 8-character alphanumeric join code, e.g. 'A1B2C3D4'."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def generate_unique_join_code(db: Session) -> str:
    for _ in range(10):
        code = generate_join_code()
        exists = db.query(Group).filter(Group.join_code == code).first()
        if not exists:
            return code
    raise HTTPException(
        status_code=500,
        detail="Could not generate a unique join code, please try again",
    )


def get_user_group(db: Session, user_id: int) -> GroupMember | None:
    return db.query(GroupMember).filter(GroupMember.student_id == user_id).first()


def get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def check_group_formation_open(db: Session):
    semester = get_active_semester(db)
    if semester and datetime.now(
        timezone.utc
    ) > semester.group_formation_deadline.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=400, detail="Group formation deadline has passed"
        )


def build_group_detail(db: Session, group: Group) -> GroupDetailResponse:
    members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    member_infos = []
    for m in members:
        user = db.query(User).filter(User.id == m.student_id).first()
        if user is None:
            continue
        member_infos.append(
            GroupMemberInfo(id=user.id, name=user.name, email=user.email)
        )

    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        join_code=group.join_code,
        leader_id=group.leader_id,
        is_locked=group.is_locked,
        members=member_infos,
    )


@router.post("/create", response_model=GroupCreateResponse)
def create_group(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    check_group_formation_open(db)

    if get_user_group(db, current_user.id):
        raise HTTPException(status_code=400, detail="You are already in a group")

    new_group = Group(
        join_code=generate_unique_join_code(db),
        leader_id=current_user.id,
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    membership = GroupMember(group_id=new_group.id, student_id=current_user.id)
    db.add(membership)
    db.commit()

    return new_group


@router.post("/join", response_model=MessageResponse)
def join_group(
    payload: GroupJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_group_formation_open(db)

    if get_user_group(db, current_user.id):
        raise HTTPException(status_code=400, detail="You are already in a group")

    group = db.query(Group).filter(Group.join_code == payload.join_code).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Invalid join code")

    if group.is_locked:
        raise HTTPException(
            status_code=400, detail="This group is locked and not accepting new members"
        )

    current_member_count = (
        db.query(GroupMember).filter(GroupMember.group_id == group.id).count()
    )
    if current_member_count >= MAX_GROUP_MEMBERS:
        raise HTTPException(status_code=400, detail="This group is already full")

    # Department / level / term must match the existing members
    joining_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )
    if joining_profile is None:
        raise HTTPException(status_code=400, detail="Student profile not found")

    leader_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == group.leader_id)
        .first()
    )
    if leader_profile is not None:
        if joining_profile.department != leader_profile.department:
            raise HTTPException(
                status_code=400,
                detail="You must be in the same department as this group",
            )
        if joining_profile.level != leader_profile.level:
            raise HTTPException(
                status_code=400, detail="You must be in the same level as this group"
            )
        if joining_profile.term != leader_profile.term:
            raise HTTPException(
                status_code=400, detail="You must be in the same term as this group"
            )

    membership = GroupMember(group_id=group.id, student_id=current_user.id)
    db.add(membership)
    db.commit()

    return MessageResponse(message="Joined group successfully")


@router.get("/me", response_model=GroupDetailResponse)
def get_my_group(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group yet")

    group = get_group_or_404(db, membership.group_id)
    return build_group_detail(db, group)


@router.patch("/name", response_model=MessageResponse)
def update_group_name(
    payload: GroupNameUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = get_group_or_404(db, membership.group_id)

    if group.leader_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the group leader can rename the group"
        )

    if group.is_locked:
        raise HTTPException(
            status_code=400, detail="Group is locked, name can no longer be changed"
        )

    existing = (
        db.query(Group).filter(Group.name == payload.name, Group.id != group.id).first()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="This group name is already taken")

    group.name = payload.name
    db.commit()

    return MessageResponse(message="Group name updated")


@router.post("/regenerate-code", response_model=MessageResponse)
def regenerate_join_code(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = get_group_or_404(db, membership.group_id)

    if group.leader_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the group leader can regenerate the join code"
        )

    group.join_code = generate_unique_join_code(db)
    db.commit()

    return MessageResponse(message=f"New join code: {group.join_code}")


@router.post("/lock", response_model=MessageResponse)
def lock_group(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = get_group_or_404(db, membership.group_id)

    if group.leader_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the group leader can lock the group"
        )

    if not group.name:
        raise HTTPException(status_code=400, detail="Set a group name before locking")

    group.is_locked = True
    db.commit()

    return MessageResponse(message="Group locked. You can now select a supervisor.")


@router.post("/leave", response_model=MessageResponse)
def leave_group(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = get_group_or_404(db, membership.group_id)

    if group.is_locked:
        raise HTTPException(
            status_code=400,
            detail="Group is locked. Contact admin to leave (admin approval required).",
        )

    db.delete(membership)
    db.commit()

    remaining_members = (
        db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    )

    if not remaining_members:
        db.delete(group)
        db.commit()
        return MessageResponse(
            message="You left the group. The group had no other members and was removed."
        )

    if group.leader_id == current_user.id:
        group.leader_id = remaining_members[0].student_id
        db.commit()

    if len(remaining_members) == 1:
        group.member_risk = True
        db.commit()

        from app.services.notification_service import notify_admins_group_at_risk

        notify_admins_group_at_risk(db, group, "Only 1 member remaining after a member left")

    return MessageResponse(message="Left group successfully")
