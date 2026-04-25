import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from zenve_db.models import ApiKeyRecord
from zenve_models.api_key import ApiKeyCreate
from zenve_models.errors import NotFoundError
from zenve_utils.api_key import (
    extract_prefix,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project_id: str, data: ApiKeyCreate) -> tuple[ApiKeyRecord, str]:
        """Create a new API key. Returns (record, raw_key)."""
        raw_key = generate_api_key()
        record = ApiKeyRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            key_hash=hash_api_key(raw_key),
            key_prefix=extract_prefix(raw_key),
            name=data.name,
            scopes=",".join(data.scopes),
            expires_at=data.expires_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record, raw_key

    def verify(self, raw_key: str) -> ApiKeyRecord | None:
        """Look up by prefix, verify hash, check active + expiry."""
        prefix = extract_prefix(raw_key)
        record = self.db.query(ApiKeyRecord).filter(ApiKeyRecord.key_prefix == prefix).first()
        if not record:
            return None
        if not verify_api_key(raw_key, record.key_hash):
            return None
        if not record.is_active:
            return None
        if record.expires_at and record.expires_at < datetime.now(UTC):
            return None
        return record

    def list_by_org(self, project_id: str) -> list[ApiKeyRecord]:
        return self.db.query(ApiKeyRecord).filter(ApiKeyRecord.project_id == project_id).all()

    def revoke(self, key_id: str) -> ApiKeyRecord:
        record = self.db.query(ApiKeyRecord).filter(ApiKeyRecord.id == key_id).first()
        if not record:
            raise NotFoundError("API key not found")
        record.is_active = False
        self.db.commit()
        self.db.refresh(record)
        return record
