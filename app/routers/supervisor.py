from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_user, get_current_admin
from app.core.security import hash_password
from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.supervisor import Supervisor, SupervisorPreference
from app.schemas.group import GroupDetailResponse, GroupMemberInfo
from app.core.security import create_purpose_token
from app.core.email import send_supervisor_invite_email
from app.schemas.supervisor import (
    SupervisorCreateRequest,
    SupervisorInfo,
    SupervisorUpdateRequest,
    InterestedAreaRequest,
    PreferenceRequest,
    GroupPreferenceInfo,
    AssignSupervisorRequest,
    CapacityOverrideRequest,
    MessageResponse,
)

router = APIRouter(tags=["Supervisor"])


def get_user_group(db: Session, user_id: int) -> GroupMember | None:
    return db.query(GroupMember).filter(GroupMember.student_id == user_id).first()


def supervisor_current_load(db: Session, supervisor_id: int) -> int:
    return db.query(Group).filter(Group.assigned_supervisor_id == supervisor_id).count()


def get_supervisor_profile(db: Session, user_id: int) -> Supervisor | None:
    return db.query(Supervisor).filter(Supervisor.user_id == user_id).first()


def to_supervisor_info(db: Session, sup: Supervisor) -> SupervisorInfo:
    user = db.query(User).filter(User.id == sup.user_id).first()
    return SupervisorInfo(
        id=sup.id,
        name=user.name if user else "",
        email=user.email if user else "",
        department=sup.department,
        research_areas=sup.research_areas,
        capacity=sup.capacity + sup.capacity_override,
        current_load=supervisor_current_load(db, sup.id),
    )


# --- Admin: create a supervisor account ---


@router.post("/admin/supervisors", response_model=SupervisorInfo)
def create_supervisor(
    payload: SupervisorCreateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=payload.name,
        email=payload.email,
        password_hash="",
        role="supervisor",
        is_verified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_supervisor = Supervisor(
        user_id=new_user.id,
        department=payload.department,
        research_areas=payload.research_areas,
    )
    db.add(new_supervisor)
    db.commit()
    db.refresh(new_supervisor)

    token = create_purpose_token(
        new_user.id, purpose="supervisor_invite", expire_minutes=60 * 24
    )
    send_supervisor_invite_email(new_user.email, new_user.name, token)

    return to_supervisor_info(db, new_supervisor)


# --- Student: browse supervisors, filtered by area ---


@router.get("/supervisors", response_model=list[SupervisorInfo])
def list_supervisors(
    area: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Supervisor)
    if area:
        query = query.filter(Supervisor.research_areas.ilike(f"%{area}%"))
    supervisors = query.all()
    return [to_supervisor_info(db, s) for s in supervisors]


# --- Student: set interested area (group leader, before locking) ---


@router.post("/groups/interested-area", response_model=MessageResponse)
def set_interested_area(
    payload: InterestedAreaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = db.query(Group).filter(Group.id == membership.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.leader_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the group leader can set the interested area"
        )

    group.interested_area = payload.area
    db.commit()

    return MessageResponse(message="Interested area set")


# --- Student: submit 3 supervisor preferences (only after group is locked) ---


@router.post("/groups/supervisor-preferences", response_model=MessageResponse)
def submit_preferences(
    payload: PreferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_user_group(db, current_user.id)
    if membership is None:
        raise HTTPException(status_code=404, detail="You are not in a group")

    group = db.query(Group).filter(Group.id == membership.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.leader_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the group leader can submit supervisor preferences",
        )

    if not group.is_locked:
        raise HTTPException(
            status_code=400, detail="Lock the group before selecting supervisors"
        )

    if len(payload.supervisor_ids) != 3:
        raise HTTPException(
            status_code=400, detail="You must select exactly 3 supervisors"
        )

    if len(set(payload.supervisor_ids)) != 3:
        raise HTTPException(
            status_code=400, detail="Supervisor choices must be 3 different supervisors"
        )

    # Clear any previous preferences for this group, then save the new ones
    db.query(SupervisorPreference).filter(
        SupervisorPreference.group_id == group.id
    ).delete()

    for rank, supervisor_id in enumerate(payload.supervisor_ids, start=1):
        supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
        if supervisor is None:
            raise HTTPException(
                status_code=404, detail=f"Supervisor id {supervisor_id} not found"
            )

        db.add(
            SupervisorPreference(
                group_id=group.id, supervisor_id=supervisor_id, preference_rank=rank
            )
        )

    db.commit()

    return MessageResponse(message="Supervisor preferences submitted")


# --- Admin: view all groups' preferences (to decide manual assignment) ---


@router.get("/admin/supervisor-preferences", response_model=list[GroupPreferenceInfo])
def view_all_preferences(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    groups = db.query(Group).filter(Group.is_locked).all()
    result = []
    for group in groups:
        prefs = (
            db.query(SupervisorPreference)
            .filter(SupervisorPreference.group_id == group.id)
            .order_by(SupervisorPreference.preference_rank)
            .all()
        )
        if not prefs:
            continue
        result.append(
            GroupPreferenceInfo(
                group_id=group.id,
                group_name=group.name,
                preferences=[p.supervisor_id for p in prefs],
            )
        )
    return result


# --- Admin: manually assign final supervisor to a group ---


@router.post("/admin/assign-supervisor", response_model=MessageResponse)
def assign_supervisor(
    payload: AssignSupervisorRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == payload.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    supervisor = (
        db.query(Supervisor).filter(Supervisor.id == payload.supervisor_id).first()
    )
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    current_load = supervisor_current_load(db, supervisor.id)
    max_capacity = supervisor.capacity + supervisor.capacity_override

    if current_load >= max_capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Supervisor is at full capacity ({current_load}/{max_capacity}). "
            "Grant a capacity override first if you want to proceed anyway.",
        )

    group.assigned_supervisor_id = supervisor.id
    db.commit()

    return MessageResponse(message="Supervisor assigned to group")


# --- Admin: temporarily raise a supervisor's capacity ---


@router.post("/admin/supervisor-capacity-override", response_model=MessageResponse)
def override_capacity(
    payload: CapacityOverrideRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    supervisor = (
        db.query(Supervisor).filter(Supervisor.id == payload.supervisor_id).first()
    )
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    supervisor.capacity_override = payload.extra_slots
    db.commit()

    return MessageResponse(
        message=f"Supervisor capacity is now {supervisor.capacity + supervisor.capacity_override}"
    )


@router.get("/supervisors/me/groups", response_model=list[GroupDetailResponse])
def my_assigned_groups(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    supervisor = get_supervisor_profile(db, current_user.id)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")

    from app.models.group import Group, GroupMember

    groups = db.query(Group).filter(Group.assigned_supervisor_id == supervisor.id).all()

    result = []
    for group in groups:
        members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
        member_infos = []
        for m in members:
            user = db.query(User).filter(User.id == m.student_id).first()
            if user:
                member_infos.append(
                    GroupMemberInfo(id=user.id, name=user.name, email=user.email)
                )

        result.append(
            GroupDetailResponse(
                id=group.id,
                name=group.name,
                join_code=group.join_code,
                leader_id=group.leader_id,
                is_locked=group.is_locked,
                members=member_infos,
            )
        )

    return result


@router.post(
    "/admin/supervisors/{supervisor_id}/resend-invite", response_model=MessageResponse
)
def resend_supervisor_invite(
    supervisor_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    user = db.query(User).filter(User.id == supervisor.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=404, detail="Supervisor's user account not found"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=400, detail="This supervisor has already set their password"
        )

    token = create_purpose_token(
        user.id, purpose="supervisor_invite", expire_minutes=60 * 24
    )
    send_supervisor_invite_email(user.email, user.name, token)

    return MessageResponse(message="Invite email resent")


@router.patch("/supervisors/me", response_model=SupervisorInfo)
def update_my_profile(
    payload: SupervisorUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")

    supervisor = get_supervisor_profile(db, current_user.id)
    if supervisor is None:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")

    if payload.department is not None:
        supervisor.department = payload.department
    if payload.research_areas is not None:
        supervisor.research_areas = payload.research_areas

    db.commit()
    db.refresh(supervisor)

    return to_supervisor_info(db, supervisor)
