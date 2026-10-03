import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class LabReferralStatus(str, enum.Enum):
    Pending = "Pending"
    Sample_Collected = "Sample_Collected"
    In_Lab = "In_Lab"
    Result_Available = "Result_Available"
    Cancelled = "Cancelled"


class LabReferral(Base):
    __tablename__ = "lab_referrals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vet_verifications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    sample_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_tests: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[LabReferralStatus] = mapped_column(
        Enum(
            LabReferralStatus,
            name="lab_referral_status_enum",
            values_callable=lambda members: [item.value for item in members],
        ),
        nullable=False,
        default=LabReferralStatus.Pending,
    )
    referred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_demo_result: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    alert: Mapped["Alert"] = relationship(back_populates="lab_referral")
    verification: Mapped["VetVerification"] = relationship(back_populates="lab_referral")