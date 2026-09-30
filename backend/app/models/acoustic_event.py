import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class EventType(str, enum.Enum):
    Cough = "Cough"
    Distress_Call = "Distress_Call"
    Abnormal_Rumination = "Abnormal_Rumination"
    Environmental_Noise = "Environmental_Noise"


class AcousticEvent(Base):
    __tablename__ = "acoustic_events"
    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_acoustic_events_confidence_range",
        ),
        CheckConstraint("audio_duration_sec > 0", name="ck_acoustic_events_duration_positive"),
        UniqueConstraint("idempotency_key", name="uq_acoustic_events_idempotency_key"),
        Index("ix_acoustic_events_shed_recorded", "shed_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shed_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
        index=True,
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    yamnet_embedding_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    audio_duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    audio_snippet_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_synced_offline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    device: Mapped["Device"] = relationship(back_populates="acoustic_events")
    shed: Mapped["Shed"] = relationship(back_populates="acoustic_events")
    alert: Mapped["Alert | None"] = relationship(
        back_populates="acoustic_event", uselist=False, cascade="all, delete-orphan"
    )
