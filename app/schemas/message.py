from datetime import datetime

from pydantic import BaseModel


class MessageInfo(BaseModel):
    id: int
    group_id: int
    sender_id: int
    sender_name: str
    sender_role: str
    content: str | None
    file_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True
