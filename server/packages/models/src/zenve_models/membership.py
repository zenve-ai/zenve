from datetime import datetime

from pydantic import BaseModel


class MembershipResponse(BaseModel):
    id: str
    user_id: int
    org_id: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
