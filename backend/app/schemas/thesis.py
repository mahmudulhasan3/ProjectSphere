from pydantic import BaseModel


class ThesisInfo(BaseModel):
    id: int
    group_id: int
    category: str
    manuscript_url: str
    status: str
    feedback: str | None
    is_published: bool

    class Config:
        from_attributes = True


class ThesisReviewRequest(BaseModel):
    action: str  # "approve" / "revise" / "escalate"
    feedback: str | None = None  # required for "revise" and "escalate"


class AdminThesisActionRequest(BaseModel):
    action: str  # "reject_hold" / "publish" / "unpublish"


class MessageResponse(BaseModel):
    message: str
