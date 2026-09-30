import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class AnomalySeverity(str, enum.Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"


class AlertStatus(str, enum.Enum):
    Pending_Triage = "Pending_Triage"
    Escalated = "Escalated"
    Under_Vet_Review = "Under_Vet_Review"
    Verified_Risk = "Verified_Risk"
    False_Positive = "False_Positive"
    Resolved = "Resolved"


class SLATier(str, enum.Enum):
    Tier_1_Farm_Owner = "Tier_1_Farm_Owner"
    Tier_2_Field_Vet = "Tier_2_Field_Vet"
    Tier_3_District_Officer = "Tier_3_District_Officer"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("acoustic_event_id", name="uq_alerts_acoustic_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acoustic_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("acoustic_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    shed_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anomaly_severity: Mapped[AnomalySeverity] = mapped_column(
        Enum(AnomalySeverity, name="anomaly_severity_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
        index=True,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
        default=AlertStatus.Pending_Triage,
        index=True,
    )
    current_sla_tier: Mapped[SLATier] = mapped_column(
        Enum(SLATier, name="sla_tier_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
        default=SLATier.Tier_1_Farm_Owner,
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    acoustic_event: Mapped["AcousticEvent"] = relationship(back_populates="alert")
    shed: Mapped["Shed"] = relationship(back_populates="alerts")
