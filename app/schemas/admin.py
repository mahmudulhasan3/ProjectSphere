from datetime import datetime

from pydantic import BaseModel


class BulkStudentCreate(BaseModel):
    name: str
    email: str
    student_id: str
    department: str
    level: str
    term: str
    section: str


class BulkImportResult(BaseModel):
    created: int
    skipped: int
    skipped_emails: list[str]


class ReassignGroupRequest(BaseModel):
    student_id: int
    new_group_id: int


class DeadlineExtensionRequest(BaseModel):
    new_deadline: datetime


class MessageResponse(BaseModel):
    message: str


class GroupSummary(BaseModel):
    id: int
    name: str | None
    leader_id: int
    is_locked: bool
    member_count: int
    assigned_supervisor_id: int | None
    member_risk: bool
    progress_risk: bool


class StudentSummary(BaseModel):
    id: int
    name: str
    email: str
    student_id: str
    department: str
    level: str
    term: str
    section: str
    is_active: bool
    is_verified: bool


class SupervisorSummary(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    department: str
    research_areas: str
    capacity: int
    current_load: int
    is_active: bool
