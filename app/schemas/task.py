from datetime import datetime

from pydantic import BaseModel


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    deadline: datetime


class TaskInfo(BaseModel):
    id: int
    group_id: int
    title: str
    description: str
    deadline: datetime
    reference_file_url: str | None

    class Config:
        from_attributes = True


class SubmissionCreateRequest(BaseModel):
    github_url: str | None = None
    notes: str | None = None


class SubmissionInfo(BaseModel):
    id: int
    task_id: int
    submitted_by: int
    file_url: str | None
    github_url: str | None
    notes: str | None
    status: str

    class Config:
        from_attributes = True


class SubmissionReviewRequest(BaseModel):
    approve: bool  # true = verified, false = request changes


class ProgressResponse(BaseModel):
    total_tasks: int
    verified_tasks: int
    progress_percent: float


class MessageResponse(BaseModel):
    message: str
