import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.shed import Shed
    from app.models.alert import Alert


class EventType(str, enum.Enum):
    Cough = "Cough"
    Distress_Call = "Distress_Call"
    Abnormal_Rumination = "Abnormal_Rumination"
    Environmental_Noise = "Environmental_Noise"


class AcousticEvent(Base):
    __tablename__ = "acoustic_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType, name="event_type_enum"), nullable=False, index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    yamnet_embedding_vector: Mapped[dict] = mapped_column(JSON, nullable=False)
    audio_duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    audio_snippet_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_synced_offline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="chk_confidence_range"),
        CheckConstraint("audio_duration_sec > 0.0", name="chk_duration_positive"),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="acoustic_events")
    shed: Mapped["Shed"] = relationship("Shed", back_populates="acoustic_events")
    alert: Mapped[Optional["Alert"]] = relationship(
        "Alert", back_populates="acoustic_event", uselist=False, cascade="all, delete-orphan"
    )
