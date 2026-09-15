from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.deps import get_current_admin
from app.models.user import User
from app.models.semester import Semester
from app.schemas.semester import SemesterCreateRequest, SemesterInfo, MessageResponse

router = APIRouter(prefix="/admin/semesters", tags=["Semester"])


@router.post("", response_model=SemesterInfo)
def create_semester(
    payload: SemesterCreateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    semester = Semester(**payload.model_dump())
    db.add(semester)
    db.commit()
    db.refresh(semester)
    return semester


@router.get("", response_model=list[SemesterInfo])
def list_semesters(
    admin: User = Depends(get_current_admin), db: Session = Depends(get_db)
):
    return db.query(Semester).all()


@router.post("/{semester_id}/activate", response_model=MessageResponse)
def activate_semester(
    semester_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    semester = db.query(Semester).filter(Semester.id == semester_id).first()
    if semester is None:
        raise HTTPException(status_code=404, detail="Semester not found")

    # Only one semester can be active at a time
    db.query(Semester).filter(Semester.is_active == True).update(
        {"is_active": False}
    )  # noqa: E712
    semester.is_active = True
    db.commit()

    return MessageResponse(message=f"'{semester.name}' is now the active semester")
