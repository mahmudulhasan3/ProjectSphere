from datetime import datetime

from pydantic import BaseModel


class ProposalTopicInfo(BaseModel):
    id: int
    title: str
    file_url: str | None
    assigned_by_supervisor: bool

    class Config:
        from_attributes = True


class ProposalRejectRequest(BaseModel):
    feedback: str
    resubmission_deadline: datetime  # required when rejecting round 1
    suggested_area: str | None = None


class ProposalApproveRequest(BaseModel):
    approved_topic_id: int


class AssignTopicRequest(BaseModel):
    title: str


class DuplicateWarning(BaseModel):
    similar_title: str
    other_group_id: int


class MessageResponse(BaseModel):
    message: str


class ProposalDetail(BaseModel):
    id: int
    group_id: int
    round_number: int
    status: str
    feedback: str | None
    resubmission_deadline: datetime | None
    suggested_area: str | None
    topics: list[ProposalTopicInfo]
    duplicate_warning: str | None = None

    class Config:
        from_attributes = True
