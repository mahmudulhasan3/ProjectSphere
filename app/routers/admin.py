import csv
import io
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_admin
from app.core.security import hash_password
from app.models.user import User
from app.models.student_profile import StudentProfile
from app.models.group import Group, GroupMember
from app.models.supervisor import Supervisor
from app.schemas.admin import (
    BulkImportResult,
    ReassignGroupRequest,
    DeadlineExtensionRequest,
    GroupSummary,
    StudentSummary,
    SupervisorSummary,
    MessageResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


def random_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


@router.post("/students/bulk-import", response_model=BulkImportResult)
def bulk_import_students(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    contents = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(contents))

    created = 0
    skipped_emails = []

    for row in reader:
        name = row.get("name", "").strip()
        email = row.get("email", "").strip()
        student_id = row.get("student_id", "").strip()
        department = row.get("department", "").strip()
        level = row.get("level", "").strip()
        term = row.get("term", "").strip()
        section = row.get("section", "").strip()

        if not all([name, email, student_id, department, level, term, section]):
            skipped_emails.append(email or "(missing email)")
            continue

        existing_email = db.query(User).filter(User.email == email).first()
        existing_student_id = (
            db.query(StudentProfile)
            .filter(StudentProfile.student_id == student_id)
            .first()
        )
        if existing_email or existing_student_id:
            skipped_emails.append(email)
            continue

        new_user = User(
            name=name,
            email=email,
            password_hash=hash_password(random_password()),
            role="student",
            is_verified=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        db.add(
            StudentProfile(
                user_id=new_user.id,
                student_id=student_id,
                department=department,
                level=level,
                term=term,
                section=section,
            )
        )
        db.commit()

        created += 1

    return BulkImportResult(
        created=created, skipped=len(skipped_emails), skipped_emails=skipped_emails
    )


@router.post("/groups/{group_id}/lock", response_model=MessageResponse)
def admin_lock_group(
    group_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    group.is_locked = True
    db.commit()
    return MessageResponse(message="Group locked by admin")


@router.post("/groups/{group_id}/unlock", response_model=MessageResponse)
def admin_unlock_group(
    group_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    group.is_locked = False
    db.commit()
    return MessageResponse(message="Group unlocked by admin")


@router.post(
    "/groups/{group_id}/approve-leave/{student_id}", response_model=MessageResponse
)
def approve_leave(
    group_id: int,
    student_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.student_id == student_id)
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(membership)
    db.commit()

    remaining_members = (
        db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    )

    if not remaining_members:
        db.delete(group)
        db.commit()
        return MessageResponse(
            message="Student removed. Group had no other members and was deleted."
        )

    if group.leader_id == student_id:
        group.leader_id = remaining_members[0].student_id

    if len(remaining_members) == 1:
        group.member_risk = True

    db.commit()

    if group.member_risk:
        from app.services.notification_service import notify_admins_group_at_risk

        notify_admins_group_at_risk(db, group, "Only 1 member remaining after admin-approved leave")

    return MessageResponse(message="Leave approved")


@router.post("/groups/reallocate", response_model=MessageResponse)
def reallocate_student(
    payload: ReassignGroupRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(GroupMember)
        .filter(GroupMember.student_id == payload.student_id)
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=404, detail="Student is not currently in any group"
        )

    new_group = db.query(Group).filter(Group.id == payload.new_group_id).first()
    if new_group is None:
        raise HTTPException(status_code=404, detail="Target group not found")

    current_count = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == payload.new_group_id)
        .count()
    )
    if current_count >= 3:
        raise HTTPException(status_code=400, detail="Target group is already full")

    old_group_id = membership.group_id
    membership.group_id = payload.new_group_id
    db.commit()

    old_group = db.query(Group).filter(Group.id == old_group_id).first()
    if old_group:
        remaining = (
            db.query(GroupMember).filter(GroupMember.group_id == old_group_id).all()
        )
        if not remaining:
            db.delete(old_group)
        elif old_group.leader_id == payload.student_id:
            old_group.leader_id = remaining[0].student_id
        db.commit()

    return MessageResponse(message="Student reallocated to new group")


@router.post("/groups/assign-leftover-students", response_model=MessageResponse)
def assign_leftover_students(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    all_students = db.query(User).filter(User.role == "student").all()
    grouped_student_ids = {m.student_id for m in db.query(GroupMember).all()}
    leftover = [s for s in all_students if s.id not in grouped_student_ids]

    if not leftover:
        return MessageResponse(message="No leftover students to assign")

    assigned_count = 0
    unassigned_count = 0

    for student in leftover:
        profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == student.id)
            .first()
        )
        if profile is None:
            unassigned_count += 1
            continue

        candidate_groups = (
            db.query(Group)
            .filter(
                Group.id.in_(
                    db.query(GroupMember.group_id)
                    .group_by(GroupMember.group_id)
                    .having(func.count(GroupMember.id) < 3)
                )
            )
            .all()
        )

        group_with_space = None
        for g in candidate_groups:
            leader_profile = (
                db.query(StudentProfile)
                .filter(StudentProfile.user_id == g.leader_id)
                .first()
            )
            if (
                leader_profile is not None
                and leader_profile.department == profile.department
                and leader_profile.level == profile.level
                and leader_profile.term == profile.term
            ):
                group_with_space = g
                break

        if group_with_space is None:
            new_group = Group(
                join_code=secrets.token_hex(4).upper(),
                leader_id=student.id,
                name=f"Auto-Group-{student.id}",
                is_locked=True,
            )
            db.add(new_group)
            db.commit()
            db.refresh(new_group)
            db.add(GroupMember(group_id=new_group.id, student_id=student.id))
        else:
            db.add(GroupMember(group_id=group_with_space.id, student_id=student.id))

        db.commit()
        assigned_count += 1

    message = f"{assigned_count} leftover students assigned to groups"
    if unassigned_count:
        message += f" ({unassigned_count} skipped - no student profile found)"

    return MessageResponse(message=message)


@router.post("/groups/{group_id}/extend-deadline", response_model=MessageResponse)
def extend_group_deadline(
    group_id: int,
    payload: DeadlineExtensionRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    group.deadline_extension = payload.new_deadline
    db.commit()

    return MessageResponse(message=f"Deadline extended to {payload.new_deadline}")


@router.get("/groups", response_model=list[GroupSummary])
def list_all_groups(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    groups = db.query(Group).all()
    result = []
    for g in groups:
        member_count = (
            db.query(GroupMember).filter(GroupMember.group_id == g.id).count()
        )
        result.append(
            GroupSummary(
                id=g.id,
                name=g.name,
                leader_id=g.leader_id,
                is_locked=g.is_locked,
                member_count=member_count,
                assigned_supervisor_id=g.assigned_supervisor_id,
                member_risk=g.member_risk,
                progress_risk=g.progress_risk,
            )
        )
    return result


@router.get("/students", response_model=list[StudentSummary])
def list_all_students(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    students = db.query(User).filter(User.role == "student").all()
    result = []
    for s in students:
        profile = (
            db.query(StudentProfile).filter(StudentProfile.user_id == s.id).first()
        )
        if profile is None:
            continue
        result.append(
            StudentSummary(
                id=s.id,
                name=s.name,
                email=s.email,
                student_id=profile.student_id,
                department=profile.department,
                level=profile.level,
                term=profile.term,
                section=profile.section,
                is_active=s.is_active,
                is_verified=s.is_verified,
            )
        )
    return result


@router.get("/supervisors", response_model=list[SupervisorSummary])
def list_all_supervisors_admin(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    supervisors = db.query(Supervisor).all()
    result = []
    for sup in supervisors:
        user = db.query(User).filter(User.id == sup.user_id).first()
        if user is None:
            continue
        load = db.query(Group).filter(Group.assigned_supervisor_id == sup.id).count()
        result.append(
            SupervisorSummary(
                id=sup.id,
                user_id=user.id,
                name=user.name,
                email=user.email,
                department=sup.department,
                research_areas=sup.research_areas,
                capacity=sup.capacity + sup.capacity_override,
                current_load=load,
                is_active=user.is_active,
            )
        )
    return result


@router.post("/users/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(
            status_code=400, detail="Cannot deactivate an admin account"
        )

    user.is_active = False
    db.commit()
    return MessageResponse(message=f"{user.name}'s account has been deactivated")


@router.post("/users/{user_id}/reactivate", response_model=MessageResponse)
def reactivate_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    return MessageResponse(message=f"{user.name}'s account has been reactivated")
