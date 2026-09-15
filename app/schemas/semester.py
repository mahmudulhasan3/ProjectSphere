from datetime import datetime

from pydantic import BaseModel


class SemesterCreateRequest(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    group_formation_deadline: datetime
    final_submission_deadline: datetime
    auto_delete_days: int = 30


class SemesterInfo(BaseModel):
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    group_formation_deadline: datetime
    final_submission_deadline: datetime
    auto_delete_days: int
    is_active: bool

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
