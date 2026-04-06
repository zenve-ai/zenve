import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zenve.db.database import Base


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    base_path: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    api_keys: Mapped[list["ApiKeyRecord"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class ApiKeyRecord(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    scopes: Mapped[str] = mapped_column(default="*")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="api_keys")


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("org_id", "name"),
        UniqueConstraint("org_id", "slug"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(nullable=False)
    dir_path: Mapped[str] = mapped_column(nullable=False)
    adapter_type: Mapped[str] = mapped_column(nullable=False)
    adapter_config: Mapped[dict] = mapped_column(JSON, default=dict)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(default="active")
    heartbeat_interval_seconds: Mapped[int] = mapped_column(default=0)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="agents")
