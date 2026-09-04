from pydantic import BaseModel, Field


class CreateClassRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ClassPublic(BaseModel):
    id: str
    name: str
    join_code: str
    member_count: int
    created_by: str


class ClassPublicWithRole(ClassPublic):
    role: str


class ClassPreview(BaseModel):
    """Shown before joining — name, rep, member count, no join_code (that's
    only revealed to members), per docs/Frontend Spec §4.3."""

    id: str
    name: str
    member_count: int


class JoinClassRequest(BaseModel):
    join_code: str = Field(min_length=1, max_length=32)


class MembershipPublic(BaseModel):
    class_id: str
    role: str
