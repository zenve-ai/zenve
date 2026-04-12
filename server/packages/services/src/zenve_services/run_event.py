from sqlalchemy.orm import Session

from zenve_db.models import RunEvent


class RunEventService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        run_id: str,
        event_type: str,
        content: str | None = None,
        meta: dict | None = None,
    ) -> RunEvent:
        event = RunEvent(run_id=run_id, event_type=event_type, content=content, meta=meta)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_by_run(
        self,
        run_id: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[RunEvent]:
        query = self.db.query(RunEvent).filter(RunEvent.run_id == run_id)
        if after_id:
            cursor = self.db.get(RunEvent, after_id)
            if cursor:
                query = query.filter(RunEvent.created_at > cursor.created_at)
        return query.order_by(RunEvent.created_at).limit(limit).all()
