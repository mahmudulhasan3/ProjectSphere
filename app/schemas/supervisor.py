from pydantic import BaseModel


class SupervisorCreateRequest(BaseModel):
    name: str
    email: str
    department: str
    research_areas: str


class SupervisorInfo(BaseModel):
    id: int
    name: str
    email: str
    department: str
    research_areas: str
    capacity: int
    current_load: int

    class Config:
        from_attributes = True


class InterestedAreaRequest(BaseModel):
    area: str


class PreferenceRequest(BaseModel):
    supervisor_ids: list[int]  # exactly 3, in preference order (1st, 2nd, 3rd)


class GroupPreferenceInfo(BaseModel):
    group_id: int
    group_name: str | None
    preferences: list[int]  # supervisor_ids in rank order


class AssignSupervisorRequest(BaseModel):
    group_id: int
    supervisor_id: int


class CapacityOverrideRequest(BaseModel):
    supervisor_id: int
    extra_slots: int


class MessageResponse(BaseModel):
    message: str


class SupervisorUpdateRequest(BaseModel):
    department: str | None = None
    research_areas: str | None = None

