import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class DeviceStatus(str, enum.Enum):
    Online = "Online"
    Offline = "Offline"
    Degraded = "Degraded"


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("device_uid", name="uq_devices_device_uid"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shed_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sheds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_uid: Mapped[str] = mapped_column(String(100), nullable=False)
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=False, default="0.1.0")
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status_enum", values_callable=lambda members: [item.value for item in members]),
        nullable=False,
        default=DeviceStatus.Online,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shed: Mapped["Shed"] = relationship(back_populates="devices")
    acoustic_events: Mapped[list["AcousticEvent"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
