from pydantic import BaseModel


class GroupCreateResponse(BaseModel):
    id: int
    join_code: str
    is_locked: bool

    class Config:
        from_attributes = True


class GroupJoinRequest(BaseModel):
    join_code: str


class GroupNameUpdate(BaseModel):
    name: str


class GroupMemberInfo(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class GroupDetailResponse(BaseModel):
    id: int
    name: str | None
    join_code: str
    leader_id: int
    is_locked: bool
    members: list[GroupMemberInfo]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
