from pydantic import BaseModel

from notify.models.group import Group


class GetGroupListResponse(BaseModel):
    status: int
    results: list[Group]
