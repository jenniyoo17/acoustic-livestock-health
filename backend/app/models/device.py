import enum
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.shed import Shed
    from app.models.acoustic_event import AcousticEvent


class DeviceStatus(str, enum.Enum):
    Online = "Online"
    Offline = "Offline"
    Degraded = "Degraded"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_uid: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=False, default="0.1.0")
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, name="device_status_enum"), nullable=False, default=DeviceStatus.Online
    )
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    public_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shed: Mapped["Shed"] = relationship("Shed", back_populates="devices")
    acoustic_events: Mapped[List["AcousticEvent"]] = relationship(
        "AcousticEvent", back_populates="device", cascade="all, delete-orphan"
    )
