import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.alert import SLATier


class EscalationRecord(Base):
    __tablename__ = "escalation_records"
    __table_args__ = (Index("ix_escalation_records_alert_created", "alert_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_tier: Mapped[SLATier | None] = mapped_column(
        Enum(SLATier, name="sla_tier_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=True,
    )
    to_tier: Mapped[SLATier] = mapped_column(
        Enum(SLATier, name="sla_tier_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    alert: Mapped["Alert"] = relationship(back_populates="escalation_records")