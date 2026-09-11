from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.group import Group, GroupMember
from backend.app.models.supervisor import Supervisor
from backend.app.models.message import Message
from backend.app.services.file_service import save_upload_file
from backend.app.schemas.message import MessageInfo

router = APIRouter(prefix="/groups", tags=["Messages"])


def get_user_group_membership(db: Session, user_id: int) -> GroupMember | None:
    return db.query(GroupMember).filter(GroupMember.student_id == user_id).first()


def can_access_group_chat(db: Session, current_user: User, group_id: int) -> bool:
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        return False

    if current_user.role == "student":
        membership = get_user_group_membership(db, current_user.id)
        return membership is not None and membership.group_id == group_id

    if current_user.role == "supervisor":
        supervisor = (
            db.query(Supervisor).filter(Supervisor.user_id == current_user.id).first()
        )
        return supervisor is not None and group.assigned_supervisor_id == supervisor.id

    if current_user.role == "admin":
        return True

    return False


def to_message_info(db: Session, message: Message) -> MessageInfo:
    sender = db.query(User).filter(User.id == message.sender_id).first()
    return MessageInfo(
        id=message.id,
        group_id=message.group_id,
        sender_id=message.sender_id,
        sender_name=sender.name if sender else "Unknown",
        sender_role=sender.role if sender else "",
        content=message.content,
        file_url=message.file_url,
        created_at=message.created_at,
    )


@router.post("/{group_id}/messages", response_model=MessageInfo)
def send_message(
    group_id: int,
    content: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_access_group_chat(db, current_user, group_id):
        raise HTTPException(
            status_code=403, detail="You don't have access to this group's chat"
        )

    if not content and file is None:
        raise HTTPException(status_code=400, detail="Message must have text or a file")

    file_url = None
    if file is not None:
        file_url = save_upload_file(file, subfolder=f"messages/{group_id}")

    message = Message(
        group_id=group_id,
        sender_id=current_user.id,
        content=content,
        file_url=file_url,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return to_message_info(db, message)


@router.get("/{group_id}/messages", response_model=list[MessageInfo])
def list_messages(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_access_group_chat(db, current_user, group_id):
        raise HTTPException(
            status_code=403, detail="You don't have access to this group's chat"
        )

    messages = (
        db.query(Message)
        .filter(Message.group_id == group_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return [to_message_info(db, m) for m in messages]
