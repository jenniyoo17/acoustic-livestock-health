import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.shed import Shed
    from app.models.acoustic_event import AcousticEvent


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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    acoustic_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("acoustic_events.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    shed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anomaly_severity: Mapped[AnomalySeverity] = mapped_column(
        SQLEnum(AnomalySeverity, name="anomaly_severity_enum"), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus, name="alert_status_enum"), nullable=False, default=AlertStatus.Pending_Triage, index=True
    )
    current_sla_tier: Mapped[SLATier] = mapped_column(
        SQLEnum(SLATier, name="sla_tier_enum"), nullable=False, default=SLATier.Tier_1_Farm_Owner
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    acoustic_event: Mapped["AcousticEvent"] = relationship("AcousticEvent", back_populates="alert")
    shed: Mapped["Shed"] = relationship("Shed", back_populates="alerts")
