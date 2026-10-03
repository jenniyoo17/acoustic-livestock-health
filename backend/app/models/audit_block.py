import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class AuditBlock(Base):
    __tablename__ = "audit_blocks"
    __table_args__ = (
        CheckConstraint("block_index >= 0", name="ck_audit_blocks_nonnegative_index"),
        CheckConstraint(
            "(block_index = 0 AND previous_hash IS NULL) OR "
            "(block_index > 0 AND previous_hash IS NOT NULL)",
            name="ck_audit_blocks_genesis_previous_hash",
        ),
        UniqueConstraint("block_index", name="uq_audit_blocks_block_index"),
        UniqueConstraint("block_hash", name="uq_audit_blocks_block_hash"),
        UniqueConstraint("transition_key", name="uq_audit_blocks_transition_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    transition_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
