import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class VetVerificationOutcome(str, enum.Enum):
    Verified_Risk = "Verified_Risk"
    False_Positive = "False_Positive"


class VetVerification(Base):
    __tablename__ = "vet_verifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    vet_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    verification_status: Mapped[VetVerificationOutcome] = mapped_column(
        Enum(
            VetVerificationOutcome,
            name="vet_verification_outcome_enum",
            values_callable=lambda members: [item.value for item in members],
        ),
        nullable=False,
    )
    assessment_notes: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    alert: Mapped["Alert"] = relationship(back_populates="vet_verification")
    lab_referral: Mapped["LabReferral | None"] = relationship(
        back_populates="verification", cascade="all, delete-orphan", uselist=False
    )