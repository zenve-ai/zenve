from pydantic import BaseModel


class SnapshotResponse(BaseModel):
    run_id: str
    fetched_at: str
    issues_count: int
    pull_requests_count: int
    branches_count: int
