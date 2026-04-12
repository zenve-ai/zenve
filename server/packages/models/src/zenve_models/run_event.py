from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RunEventType:
    OUTPUT = "output"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    USAGE = "usage"


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    event_type: str
    content: str | None
    meta: dict | None
    created_at: datetime
